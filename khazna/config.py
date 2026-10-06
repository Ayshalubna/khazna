"""Settings. Everything runs inside this process: no cloud APIs are ever called."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = Path(__file__).resolve().parent / "data" / "corpus"
DB_PATH = Path(os.getenv("KHAZNA_DB", "/tmp/khazna_audit.db"))

ROLES = ["employee", "hr", "finance", "legal", "it", "executive"]
ROLE_LABELS = {
    "employee": ("Employee", "موظف"), "hr": ("HR", "الموارد البشرية"), "finance": ("Finance", "المالية"),
    "legal": ("Legal", "الشؤون القانونية"), "it": ("IT & Security", "تقنية المعلومات"),
    "executive": ("Executive", "الإدارة التنفيذية"),
}

# retrieval
TOP_K = 5
RRF_K = 60
EMBED = os.getenv("KHAZNA_EMBED", "lsa")                 # lsa (built-in, no download) | e5 (multilingual model)
E5_MODEL = os.getenv("KHAZNA_E5_MODEL", "intfloat/multilingual-e5-small")

# generation
LLM = os.getenv("KHAZNA_LLM", "extractive")              # extractive | transformers | ollama
HF_MODEL = os.getenv("KHAZNA_HF_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
OLLAMA_URL = os.getenv("KHAZNA_OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("KHAZNA_OLLAMA_MODEL", "qwen2.5:7b")
MAX_NEW_TOKENS = int(os.getenv("KHAZNA_MAX_NEW_TOKENS", "220"))

# privacy
EGRESS_GUARD = os.getenv("KHAZNA_EGRESS_GUARD", "1") == "1"
UPLOAD_TTL_MIN = 30
MAX_UPLOADS_PER_SESSION = 3
