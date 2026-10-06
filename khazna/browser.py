"""Entry point for the in-browser build (Pyodide). The web app's /api/* calls are answered by `call()` instead of
FastAPI, so the same engine runs inside the visitor's browser: documents, questions and uploads never leave it.

    call("ask", '{"question": "...", "role": "employee", "sid": "..."}')  ->  JSON string
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from . import pii
from .config import EMBED, ROLE_LABELS, ROLES, UPLOAD_TTL_MIN
from .corpus import MAX_BYTES, UploadError
from .service import get

ROOT = Path(__file__).resolve().parent.parent
ROLE_RE = re.compile("^(" + "|".join(ROLES) + ")$")
SID_RE = re.compile(r"^[A-Za-z0-9]{8,40}$")
DOC_RE = re.compile(r"^[a-z_0-9]{2,40}$")


class BadRequest(ValueError):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


def _role(r) -> str:
    r = r or "employee"
    if not isinstance(r, str) or not ROLE_RE.match(r):
        raise BadRequest(422, "invalid role")
    return r


def _sid(s):
    if s in (None, ""):
        return None
    if not isinstance(s, str) or not SID_RE.match(s):
        raise BadRequest(422, "invalid session id")
    return s


def _eval() -> dict:
    out = {}
    for name in ("results", "results_llm"):
        f = ROOT / "eval" / f"{name}.json"
        if f.exists():
            out[name] = json.loads(f.read_text())
    return out


def meta() -> dict:
    k = get()
    ev = {}
    r = _eval().get("results")
    if r:
        ev = {"accuracy": r["answers"]["accuracy"], "cross": r["answers"]["cross_accuracy"],
              "refusal": r["refusal"]["unanswerable"], "checks": r["leaks"]["checks"], "questions": len(r["rows"]),
              "leaks": sum(v for kk, v in r["leaks"].items() if kk != "checks")}
    return {"roles": [{"id": r, "label": ROLE_LABELS[r][0], "label_ar": ROLE_LABELS[r][1], "documents": len(k.allowed(r))}
                      for r in ROLES],
            "documents": len(k.docs), "passages": len(k.chunks), "retrieval": f"BM25 + {k.index.mode.upper()} (NumPy), RRF",
            "embedding": EMBED, **k.model_info(), "where": "inside your browser", "runtime": "browser",
            "egress": {"enabled": True, "blocked_attempts": 0}, "upload_ttl_min": UPLOAD_TTL_MIN,
            "max_upload_mb": MAX_BYTES // (1024 * 1024), "eval": ev}


def _dispatch(name: str, a: dict):
    k = get()
    if name == "meta":
        return meta()
    if name == "health":
        return {"status": "ok", "documents": len(k.docs), "passages": len(k.chunks), "runtime": "browser"}
    if name == "library":
        return k.library(_role(a.get("role")), _sid(a.get("sid")))
    if name == "document":
        doc_id = a.get("id", "")
        if not DOC_RE.match(doc_id):
            raise BadRequest(422, "invalid document id")
        d = k.read(doc_id, _role(a.get("role")), _sid(a.get("sid")))
        if d is None:
            raise BadRequest(404, "document not found or not available to this role")
        return d
    if name == "ask":
        q = (a.get("question") or "").strip()
        if not 2 <= len(q) <= 400:
            raise BadRequest(422, "question must be 2-400 characters")
        return k.ask(q, _role(a.get("role")), _sid(a.get("sid")))
    if name == "scan":
        text = a.get("text") or ""
        if not 1 <= len(text) <= 5000:
            raise BadRequest(422, "text must be 1-5000 characters")
        masked, counts = pii.redact(text, _role(a.get("role")))
        return {"masked": masked, "found": counts}
    if name == "delete_upload":
        sid = _sid(a.get("sid"))
        if not sid or not re.fullmatch(r"up_[a-f0-9]{8}", a.get("id", "")) or not k.delete_upload(sid, a["id"]):
            raise BadRequest(404, "upload not found")
        return {"deleted": a["id"]}
    if name == "privacy":
        sid = _sid(a.get("sid"))
        return {"egress": {"enabled": True, "blocked_attempts": 0}, **k.model_info(), "totals": k.audit.totals(),
                "session_events": k.audit.events(sid, 20) if sid else []}
    if name == "eval":
        return _eval()
    raise BadRequest(404, "not found")


def call(name: str, args_json: str = "{}") -> str:
    """Returns {"status": int, "body": ...} as JSON."""
    try:
        return json.dumps({"status": 200, "body": _dispatch(name, json.loads(args_json or "{}"))}, ensure_ascii=False)
    except BadRequest as e:
        return json.dumps({"status": e.status, "body": {"detail": e.detail}})


def upload(sid: str, name: str, data) -> str:
    if hasattr(data, "to_bytes"):          # a JavaScript Uint8Array passed in from the page
        data = data.to_bytes()
    try:
        sid = _sid(sid)
        if not sid:
            raise BadRequest(400, "session id required")
        if len(data) > MAX_BYTES:
            raise UploadError("Files must be 5 MB or smaller.")
        return json.dumps({"status": 200, "body": get().upload(sid, name or "upload.txt", bytes(data))}, ensure_ascii=False)
    except BadRequest as e:
        return json.dumps({"status": e.status, "body": {"detail": e.detail}})
    except UploadError as e:
        return json.dumps({"status": 422, "body": {"detail": str(e)}})


def boot() -> str:
    os.environ.setdefault("KHAZNA_DB", "/tmp/khazna_audit.db")
    get()
    return json.dumps({"documents": len(get().docs)})
