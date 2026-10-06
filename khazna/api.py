"""REST API + web app.

Run:  python -m scripts.serve            (or: uvicorn khazna.api:api)
Docs: http://localhost:8000/docs

Visitors are identified by an anonymous random session id (header X-Khazna-Session); their uploads live only in
that session's memory and are deleted after 30 minutes.
"""
from __future__ import annotations

import json
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi import Path as P
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import pii, service
from .config import EMBED, ROLE_LABELS, ROLES, UPLOAD_TTL_MIN
from .corpus import MAX_BYTES, UploadError
from .guard import EGRESS
from .hardening import AccessLog, RateLimit, SecurityHeaders, warm_up

SESSION_ID = r"^[A-Za-z0-9]{8,40}$"
ROLE = "^(" + "|".join(ROLES) + ")$"
DOC_ID = r"^[a-z_0-9]{2,40}$"
EVAL = Path(__file__).resolve().parent.parent / "eval"


@asynccontextmanager
async def lifespan(_app):
    if os.getenv("KHAZNA_WARMUP", "1") == "1":
        warm_up()
    yield


api = FastAPI(title="Khazna — private document assistant", version="1.0.0", lifespan=lifespan,
              description="Answers questions about confidential documents with citations. Runs entirely inside "
                          "this server: role-based access, personal data masking, prompt-injection guard, no outbound network.")
api.add_middleware(GZipMiddleware, minimum_size=1000)
api.add_middleware(SecurityHeaders)
api.add_middleware(RateLimit, reads_per_min=int(os.getenv("KHAZNA_READS_PER_MIN", "240")),
                   writes_per_min=int(os.getenv("KHAZNA_WRITES_PER_MIN", "30")))
api.add_middleware(AccessLog)


def K():
    return service.get()


def _sid(x: str | None) -> str | None:
    if x is None:
        return None
    if not re.fullmatch(SESSION_ID, x):
        raise HTTPException(422, "invalid session id")
    return x


class AskBody(BaseModel):
    question: str = Field(min_length=2, max_length=400)
    role: str = Field("employee", pattern=ROLE)


class ScanBody(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    role: str = Field("employee", pattern=ROLE)


@api.get("/health")
def health():
    k = K()
    return {"status": "ok", "documents": len(k.docs), "passages": len(k.chunks), "boot_seconds": k.boot_seconds,
            **k.model_info(), "egress_guard": EGRESS.enabled}


@api.get("/api/meta")
def meta():
    k = K()
    ev = {}
    try:
        r = json.loads((EVAL / "results.json").read_text())
        ev = {"accuracy": r["answers"]["accuracy"], "cross": r["answers"]["cross_accuracy"],
              "refusal": r["refusal"]["unanswerable"], "leaks": sum(v for kk, v in r["leaks"].items() if kk != "checks"),
              "checks": r["leaks"]["checks"], "questions": len(r["rows"])}
    except (OSError, ValueError, KeyError):
        pass
    return {"roles": [{"id": r, "label": ROLE_LABELS[r][0], "label_ar": ROLE_LABELS[r][1],
                       "documents": len(k.allowed(r))} for r in ROLES],
            "documents": len(k.docs), "passages": len(k.chunks), "retrieval": f"BM25 + {k.index.mode.upper()} (FAISS), RRF",
            "embedding": EMBED, **k.model_info(), "egress": EGRESS.status(), "upload_ttl_min": UPLOAD_TTL_MIN,
            "max_upload_mb": MAX_BYTES // (1024 * 1024), "eval": ev}


@api.get("/api/library")
def library(role: str = Query("employee", pattern=ROLE), x_khazna_session: str | None = Header(None)):
    return K().library(role, _sid(x_khazna_session))


@api.get("/api/documents/{doc_id}")
def document(doc_id: str = P(..., pattern=DOC_ID), role: str = Query("employee", pattern=ROLE),
             x_khazna_session: str | None = Header(None)):
    d = K().read(doc_id, role, _sid(x_khazna_session))
    if d is None:
        raise HTTPException(404, "document not found or not available to this role")
    return d


@api.post("/api/ask")
def ask(body: AskBody, x_khazna_session: str | None = Header(None)):
    return K().ask(body.question.strip(), body.role, _sid(x_khazna_session))


@api.post("/api/ask/stream")
def ask_stream(body: AskBody, x_khazna_session: str | None = Header(None)):
    sid = _sid(x_khazna_session)
    q = body.question.strip()

    def events():
        for ev in K().ask_stream(q, body.role, sid):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store",
                                                                                 "X-Accel-Buffering": "no"})


@api.post("/api/upload")
async def upload(file: UploadFile = File(...), x_khazna_session: str | None = Header(None)):
    sid = _sid(x_khazna_session)
    if not sid:
        raise HTTPException(400, "X-Khazna-Session header required")
    data = await file.read(MAX_BYTES + 1)
    try:
        return K().upload(sid, file.filename or "upload.txt", data)
    except UploadError as e:
        raise HTTPException(422, str(e)) from None


@api.delete("/api/upload/{doc_id}")
def delete_upload(doc_id: str = P(..., pattern=r"^up_[a-f0-9]{8}$"), x_khazna_session: str | None = Header(None)):
    sid = _sid(x_khazna_session)
    if not sid or not K().delete_upload(sid, doc_id):
        raise HTTPException(404, "upload not found")
    return {"deleted": doc_id}


@api.post("/api/scan")
def scan(body: ScanBody):
    """Preview personal-data masking on any text (nothing is stored)."""
    masked, counts = pii.redact(body.text, body.role)
    return {"masked": masked, "found": counts}


@api.get("/api/privacy")
def privacy(x_khazna_session: str | None = Header(None)):
    k = K()
    sid = _sid(x_khazna_session)
    return {"egress": EGRESS.status(), **k.model_info(), "totals": k.audit.totals(),
            "session_events": k.audit.events(sid, 20) if sid else []}


@api.get("/api/eval")
def evaluation():
    out = {}
    for name in ("results", "results_llm"):
        f = EVAL / f"{name}.json"
        if f.exists():
            out[name] = json.loads(f.read_text())
    return out


WEB = Path(__file__).resolve().parent.parent / "web"
if WEB.exists():
    api.mount("/", StaticFiles(directory=WEB, html=True), name="web")
