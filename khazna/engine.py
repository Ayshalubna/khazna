"""The question-answering pipeline: permissions -> hybrid retrieval -> injection guard -> answer -> checks -> masking."""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
import threading
import time
from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import guard, pii
from .config import DB_PATH, EMBED, LLM, MAX_UPLOADS_PER_SESSION, ROLES, TOP_K, UPLOAD_TTL_MIN
from .corpus import Document, UploadError, chunk, from_upload, load_corpus
from .generate import REFUSAL, Answer, ExtractiveGenerator, LLMGenerator, Source, make_generator
from .index import Index
from .text import is_arabic, tokens

MAX_SESSIONS = 500


@dataclass
class Session:
    sid: str
    docs: dict[str, Document] = field(default_factory=dict)
    index: Index | None = None
    created: dict[str, float] = field(default_factory=dict)
    touched: float = field(default_factory=time.time)


class Audit:
    """Append-only log of who asked what with which role, which documents were used, and what was masked."""

    def __init__(self, path=DB_PATH):
        self.path = path
        self.lock = threading.Lock()
        with self._con() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS events (ts TEXT, session TEXT, role TEXT, kind TEXT,
                         question TEXT, docs TEXT, refused INTEGER, masked INTEGER, injections INTEGER, ms INTEGER)""")

    def _con(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def log(self, session, role, kind, question, docs, refused, masked, injections, ms):
        with self.lock, self._con() as c:
            c.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (datetime.now(timezone.utc).isoformat(timespec="seconds"), session, role, kind, question[:500],
                       ",".join(docs), int(refused), masked, injections, ms))

    def events(self, session, limit=50):
        with self._con() as c:
            rows = c.execute("SELECT ts, role, kind, question, docs, refused, masked, injections, ms FROM events "
                             "WHERE session=? ORDER BY rowid DESC LIMIT ?", (session, limit)).fetchall()
        keys = ("ts", "role", "kind", "question", "docs", "refused", "masked", "injections", "ms")
        return [dict(zip(keys, r)) for r in rows]

    def totals(self):
        with self._con() as c:
            r = c.execute("SELECT COUNT(*), COALESCE(SUM(refused),0), COALESCE(SUM(masked),0), "
                          "COALESCE(SUM(injections),0) FROM events WHERE kind='ask'").fetchone()
        return {"questions": r[0], "refused": r[1], "masked": r[2], "injections_blocked": r[3]}


class Khazna:
    def __init__(self, embed: str = EMBED, llm: str = LLM, audit: Audit | None = None):
        tic = time.time()
        self.docs = {d.id: d for d in load_corpus()}
        self.chunks = [c for d in self.docs.values() for c in chunk(d)]
        self.superseded = {d.id for d in self.docs.values() if d.status == "superseded"}
        self.index = Index(self.chunks, embed=embed, superseded=self.superseded)
        self.idf = self.index.bm25.idf
        self._role_idf: dict[str, dict[str, float]] = {}
        self.generator = make_generator(llm)
        self.extractive = self.generator if isinstance(self.generator, ExtractiveGenerator) else self.generator.fallback
        self.sessions: OrderedDict[str, Session] = OrderedDict()
        self.lock = threading.Lock()
        self.audit = audit or Audit()
        self.boot_seconds = round(time.time() - tic, 2)

    # --------------------------------------------------------------------------------- access
    def model_info(self) -> dict:
        g = self.generator
        if isinstance(g, LLMGenerator):
            return {"generator": "llm", "model": g.backend.model_id, "where": "inside this server"}
        return {"generator": "extractive", "model": None, "where": "inside this server"}

    def allowed(self, role: str) -> set[str]:
        return {d.id for d in self.docs.values() if role in d.access}

    def library(self, role: str, sid: str | None = None) -> list[dict]:
        out = []
        for d in self.docs.values():
            out.append({"id": d.id, "title": d.title, "title_ar": d.title_ar, "classification": d.classification,
                        "owner": d.owner, "lang": d.lang, "access": d.access, "can_read": role in d.access,
                        "status": d.status, "pii": d.pii, "uploaded": False,
                        "words": len(d.text.split())})
        s = self._session(sid, create=False)
        if s:
            self._expire(s)
            for d in s.docs.values():
                out.append({"id": d.id, "title": d.title, "title_ar": "", "classification": d.classification,
                            "owner": "You", "lang": d.lang, "access": ROLES, "can_read": True, "status": "current",
                            "pii": d.pii, "uploaded": True, "words": len(d.text.split()),
                            "expires_in_min": max(0, round(UPLOAD_TTL_MIN - (time.time() - s.created[d.id]) / 60))})
        return out

    def read(self, doc_id: str, role: str, sid: str | None = None) -> dict | None:
        """A whole document as the role may see it: masked, and only if the role has access."""
        d = self.docs.get(doc_id)
        if d is None:
            s = self._session(sid, create=False)
            d = s.docs.get(doc_id) if s else None
        if d is None or (not d.uploaded and role not in d.access):
            return None
        text, masked = pii.redact(d.text, role, contacts_ok=d.id in pii.CONTACT_DOCS)
        flagged = [x.strip() for x in text.split("\n") if x.strip() and guard.is_injection(x)]
        return {"id": d.id, "title": d.title, "title_ar": d.title_ar, "classification": d.classification,
                "owner": d.owner, "lang": d.lang, "status": d.status, "superseded_by": d.superseded_by,
                "text": text, "masked": masked, "injection_lines": flagged}

    # --------------------------------------------------------------------------------- sessions/uploads
    def _session(self, sid: str | None, create: bool = True) -> Session | None:
        if not sid:
            return None
        with self.lock:
            s = self.sessions.get(sid)
            if s is None and create:
                s = Session(sid)
                self.sessions[sid] = s
                while len(self.sessions) > MAX_SESSIONS:
                    self.sessions.popitem(last=False)
            if s:
                self.sessions.move_to_end(sid)
                s.touched = time.time()
            return s

    def _expire(self, s: Session) -> None:
        now = time.time()
        old = [k for k, t in s.created.items() if now - t > UPLOAD_TTL_MIN * 60]
        if old:
            for k in old:
                s.docs.pop(k, None)
                s.created.pop(k, None)
            self._reindex(s)

    def _reindex(self, s: Session) -> None:
        ch = [c for d in s.docs.values() for c in chunk(d)]
        s.index = Index(ch, embed="lsa") if len(ch) >= 2 else (Index(ch * 2, embed="lsa") if ch else None)

    def upload(self, sid: str, name: str, data: bytes) -> dict:
        s = self._session(sid)
        self._expire(s)
        if len(s.docs) >= MAX_UPLOADS_PER_SESSION:
            raise UploadError(f"You can keep up to {MAX_UPLOADS_PER_SESSION} files at a time. Delete one first.")
        doc_id = "up_" + secrets.token_hex(4)
        d = from_upload(doc_id, name, data)
        s.docs[doc_id] = d
        s.created[doc_id] = time.time()
        self._reindex(s)
        self.audit.log(sid, "-", "upload", name, [doc_id], False, sum(d.pii.values()), 0, 0)
        return {"id": doc_id, "title": d.title, "lang": d.lang, "words": len(d.text.split()), "pii": d.pii,
                "chunks": len(chunk(d)), "expires_in_min": UPLOAD_TTL_MIN}

    def delete_upload(self, sid: str, doc_id: str) -> bool:
        s = self._session(sid, create=False)
        if not s or doc_id not in s.docs:
            return False
        s.docs.pop(doc_id)
        s.created.pop(doc_id, None)
        self._reindex(s)
        return True

    # --------------------------------------------------------------------------------- retrieval
    def retrieve(self, q: str, role: str, sid: str | None = None, k: int = TOP_K) -> list[Source]:
        hits = self.index.search(q, self.allowed(role), k)
        s = self._session(sid, create=False)
        if s:
            self._expire(s)
            if s.index is not None:
                hits += s.index.search(q, None, k)
                hits = sorted(hits, key=lambda h: -h.score)[:k]
        sources = []
        seen = set()
        for h in hits:
            if h.chunk.id in seen:
                continue
            seen.add(h.chunk.id)
            d = self.docs.get(h.chunk.doc) or (s.docs.get(h.chunk.doc) if s else None)
            text, removed = guard.sanitise(h.chunk.text)
            sources.append(Source(n=len(sources) + 1, doc=h.chunk.doc, title=d.title if d else h.chunk.doc,
                                  section=h.chunk.section, text=text, superseded=h.chunk.doc in self.superseded,
                                  injection_removed=removed))
        return sources

    def role_idf(self, role: str) -> dict[str, float]:
        """Word rarity limited to the vocabulary of documents this role may read.

        A word that only occurs in locked documents counts as unknown for the role, so the answer step refuses
        instead of answering a nearby, unrelated passage (and without revealing that the word exists elsewhere)."""
        if role not in self._role_idf:
            ok = self.allowed(role)
            vocab = {t for c in self.chunks if c.doc in ok for t in tokens(f"{c.section} {c.text}")}
            vocab |= {t for d in self.docs.values() if d.id in ok for t in tokens(d.title)}
            self._role_idf[role] = {t: v for t, v in self.idf.items() if t in vocab}
        return self._role_idf[role]

    def _idf(self, sid, role: str = "employee"):
        base = self.role_idf(role)
        s = self._session(sid, create=False)
        if s and s.index is not None:
            return {**s.index.bm25.idf, **base}
        return base

    def _package(self, q, role, sid, sources: list[Source], ans: Answer, t0: float) -> dict:
        cited_docs = {src.doc for src in sources if src.n in ans.citations}
        text, masked = pii.redact(ans.text, role, contacts_ok=bool(cited_docs) and cited_docs <= pii.CONTACT_DOCS)
        out_sources = []
        total_masked = sum(masked.values())
        for src in sources:
            st, m = pii.redact(src.text, role, contacts_ok=src.doc in pii.CONTACT_DOCS)
            total_masked += sum(m.values()) if src.n in ans.citations else 0
            d = self.docs.get(src.doc)
            out_sources.append({"n": src.n, "doc": src.doc, "title": src.title, "section": src.section, "text": st,
                                "cited": src.n in ans.citations, "superseded": src.superseded,
                                "classification": d.classification if d else "Your upload",
                                "uploaded": d is None, "injection_removed": src.injection_removed, "masked": m})
        inj = sum(s.injection_removed for s in sources)
        ms = int((time.time() - t0) * 1000)
        self.audit.log(sid or "-", role, "ask", q, sorted({s.doc for s in sources if s.n in ans.citations}),
                       ans.refused, total_masked, inj, ms)
        return {"question": q, "role": role, "lang": "ar" if is_arabic(q) else "en", "answer": text,
                "refused": ans.refused, "citations": ans.citations, "method": ans.method, "support": round(ans.support, 3),
                "notes": ans.notes, "masked": masked, "injections_blocked": inj, "sources": out_sources, "ms": ms}

    # --------------------------------------------------------------------------------- answering
    def ask(self, q: str, role: str = "employee", sid: str | None = None) -> dict:
        t0 = time.time()
        sources = self.retrieve(q, role, sid)
        idf = self._idf(sid, role)
        if isinstance(self.generator, LLMGenerator):
            safe = self.extractive.answer(q, sources, idf)
            if safe.refused:
                ans = safe
            else:
                raw = "".join(self.generator.stream(q, sources, idf))
                ans = self.generator.finalise(q, raw, sources, idf)
        else:
            ans = self.generator.answer(q, sources, idf)
        return self._package(q, role, sid, sources, ans, t0)

    def ask_stream(self, q: str, role: str = "employee", sid: str | None = None) -> Iterator[dict]:
        """Events: sources (immediately), token* (model output, masked as it streams), final."""
        t0 = time.time()
        sources = self.retrieve(q, role, sid)
        idf = self._idf(sid, role)
        preview = [{"n": s.n, "title": s.title, "section": s.section} for s in sources]
        yield {"type": "sources", "sources": preview}
        if not isinstance(self.generator, LLMGenerator):
            yield {"type": "final", **self._package(q, role, sid, sources, self.generator.answer(q, sources, idf), t0)}
            return
        safe = self.extractive.answer(q, sources, idf)
        if safe.refused:
            yield {"type": "final", **self._package(q, role, sid, sources, safe, t0)}
            return
        raw = ""
        for tok in self.generator.stream(q, sources, idf):
            raw += tok
            yield {"type": "token", "text": pii.redact(tok, role)[0]}   # strictest masking while streaming
        ans = self.generator.finalise(q, raw, sources, idf)
        yield {"type": "final", **self._package(q, role, sid, sources, ans, t0)}


def refusal(lang: str) -> str:
    return REFUSAL[lang]


def question_id(q: str) -> str:
    return hashlib.sha256(q.encode()).hexdigest()[:12]
