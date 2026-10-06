"""Load documents (Markdown with a small header, or uploaded PDF/DOCX/TXT) and split them into passages."""
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import pii
from .config import CORPUS_DIR, ROLES
from .text import is_arabic

HEADER = re.compile(r"^---\n(.*?)\n---\n", re.S)
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=520, chunk_overlap=60,
                                          separators=["\n\n", "\n", "۔", ". ", "؟ ", "? ", "، ", ", ", " ", ""])


@dataclass
class Document:
    id: str
    title: str
    title_ar: str
    access: list[str]
    classification: str
    owner: str
    lang: str
    text: str
    uploaded: bool = False
    pii: dict = field(default_factory=dict)
    status: str = "current"          # current | superseded
    superseded_by: str = ""


@dataclass
class Chunk:
    id: str            # "<doc>#<n>"
    doc: str
    section: str
    text: str
    n: int


def _parse_header(raw: str) -> tuple[dict, str]:
    m = HEADER.match(raw)
    if not m:
        return {}, raw
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                v = [x.strip() for x in v[1:-1].split(",") if x.strip()]
            meta[k.strip()] = v
    return meta, raw[m.end():]


def load_corpus(path: Path = CORPUS_DIR) -> list[Document]:
    docs = []
    for f in sorted(path.glob("*.md")):
        meta, body = _parse_header(f.read_text(encoding="utf-8"))
        access = [r for r in meta.get("access", []) if r in ROLES]
        docs.append(Document(id=meta["id"], title=meta.get("title", f.stem), title_ar=meta.get("title_ar", ""),
                             access=access, classification=meta.get("classification", "Internal"),
                             owner=meta.get("owner", ""), lang=meta.get("lang", "en"), text=body.strip(),
                             pii=pii.summary(body), status=meta.get("status", "current"),
                             superseded_by=meta.get("superseded_by", "")))
    return docs


def chunk(doc: Document) -> list[Chunk]:
    """Split by section headings first (so passages keep their heading), then by size."""
    out: list[Chunk] = []
    section = doc.title
    blocks: list[tuple[str, str]] = []
    buf: list[str] = []
    for line in doc.text.splitlines():
        if line.startswith("#"):
            if buf:
                blocks.append((section, "\n".join(buf).strip()))
                buf = []
            section = line.lstrip("# ").strip()
        else:
            buf.append(line)
    if buf:
        blocks.append((section, "\n".join(buf).strip()))
    for sec, body in blocks:
        if not body:
            continue
        for piece in SPLITTER.split_text(body):
            out.append(Chunk(id=f"{doc.id}#{len(out)}", doc=doc.id, section=sec, text=piece.strip(), n=len(out)))
    return out


# ------------------------------------------------------------------------------------------- uploads
MAX_BYTES = 5 * 1024 * 1024
ALLOWED = {".pdf", ".docx", ".txt", ".md"}


class UploadError(ValueError):
    pass


def extract_text(name: str, data: bytes) -> str:
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED:
        raise UploadError("Only PDF, DOCX, TXT and MD files are supported.")
    if len(data) > MAX_BYTES:
        raise UploadError("Files must be 5 MB or smaller.")
    if ext in (".txt", ".md"):
        for enc in ("utf-8", "utf-16", "cp1256", "latin-1"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
    if ext == ".pdf":
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(data))
            if len(reader.pages) > 200:
                raise UploadError("PDFs are limited to 200 pages.")
            return "\n\n".join((p.extract_text() or "") for p in reader.pages)
        except UploadError:
            raise
        except Exception as e:  # malformed or encrypted PDFs
            raise UploadError("This PDF could not be read (it may be scanned, encrypted or damaged).") from e
    if ext == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                info = z.getinfo("word/document.xml")
                if info.file_size > 20 * MAX_BYTES:
                    raise UploadError("This document is too large once unpacked.")
                xml = z.read(info).decode("utf-8", "ignore")
        except UploadError:
            raise
        except Exception as e:
            raise UploadError("This Word file could not be read.") from e
        xml = re.sub(r"</w:p>", "\n", xml)
        return re.sub(r"<[^>]+>", "", xml)
    raise UploadError("Unsupported file.")


def from_upload(doc_id: str, name: str, data: bytes) -> Document:
    text = extract_text(name, data)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 20:
        raise UploadError("No readable text was found in this file.")
    text = text[:200_000]
    return Document(id=doc_id, title=Path(name).name[:120], title_ar="", access=list(ROLES), classification="Your upload",
                    owner="You", lang="ar" if is_arabic(text[:2000]) else "en", text=text, uploaded=True,
                    pii=pii.summary(text))
