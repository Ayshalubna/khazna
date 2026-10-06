# Khazna خزنة — private document assistant

[![CI](https://github.com/Ayshalubna/khazna/actions/workflows/ci.yml/badge.svg)](https://github.com/Ayshalubna/khazna/actions/workflows/ci.yml)
**[Live demo ↗](https://lubna777-khazna.hf.space)** · English and Arabic · MIT

Khazna answers questions about a company's confidential documents, in English or Arabic, with the exact source for
every answer, and nothing leaves the server. It is built for organisations in the UAE that cannot send internal
documents to an outside AI service (UAE PDPL, sector data-residency rules, plain caution).

![Ask page](docs/screenshots/ask.png)

## What it does

| | |
|---|---|
| **Role-based access** | Six roles (employee, HR, finance, legal, IT, executive). Locked documents are filtered *inside* the search, so they can never be quoted, cited or hinted at. A word that only appears in locked documents counts as unknown for that role, so the question is refused rather than answered from something unrelated. |
| **Cited, grounded answers** | Every answer cites its passage. If the documents don't contain the answer, Khazna says so. |
| **Local model, checked** | A small open model (Qwen2.5-1.5B-Instruct) runs inside the process, or a larger one via Ollama on the same machine. Its answer is checked: citations must exist and every number must appear in the cited text, otherwise the verified quote is shown instead. Without a model, Khazna quotes the best sentence. |
| **Personal data masking** | Emirates ID, IBAN, Luhn-valid card and passport numbers are always hidden. Personal phone numbers and e-mails are shown only to IT and executives, and only from operational runbooks. Shared team mailboxes stay visible. |
| **Prompt-injection guard** | Document text is data. Sentences that try to instruct an AI are removed before answering and flagged in the reader. |
| **No outbound network** | After start-up an egress guard refuses every connection outside the container and counts attempts; the count is on the page. |
| **Bilingual** | Arabic normalisation and light stemming, an Arabic↔English workplace glossary, Arabic answers to Arabic questions, full RTL interface. |
| **Version aware** | Superseded documents rank below the current version and are labelled. |
| **Your own files** | Upload a PDF, DOCX, TXT or MD (5 MB). It is indexed in memory for your session only and deleted after 30 minutes. |
| **Audit trail** | Every question is logged (SQLite) with the role, documents used, what was masked and blocked. |

| Personal data hidden from HR's answer | Planted instruction removed |
|---|---|
| ![Masked answer](docs/screenshots/answer-masked.png) | ![Injection](docs/screenshots/injection.png) |

## Results

127 questions with known answers (facts in both languages, cross-language, unanswerable, restricted, personal
data, injection, outdated versions), run on every push. Full report: [eval/RESULTS.md](eval/RESULTS.md).

| Built-in mode (no model) | |
|---|---|
| Correct answers | **91%** of 87 answerable (English 92%, Arabic 80%, Arabic↔English 100%) |
| "Not in the documents" refused | **85%** of 20 |
| Restricted questions refused | **91%** of 11 (the rest are answered from permitted documents only) |
| Right passage in the top 5 | **100%** (hybrid BM25 + FAISS) |
| Leaks: restricted text, personal identifiers, planted instruction, outdated values | **0** across 38 checks |
| Median latency | about 10 ms |

The CI build fails if any leak appears or if accuracy, cross-language accuracy, retrieval or refusal rates fall below
their thresholds. A separate on-demand CI job scores the local model on the same questions.

## How it works

```
question ─► role → allowed documents ─► hybrid search (BM25 + FAISS, RRF; Arabic↔English expansion)
          ─► remove planted instructions ─► answer (local model or verified quote, with citations)
          ─► check citations and numbers ─► mask personal data ─► audit log
```

| Part | Choice |
|---|---|
| Chunking | Split by heading, then LangChain `RecursiveCharacterTextSplitter` (520 / 60) |
| Keyword search | BM25 with Arabic normalisation and stemming |
| Meaning search | FAISS inner-product index with an ID selector for permissions. Default encoder: TF-IDF (words + character n-grams) → SVD, no download. Optional: `intfloat/multilingual-e5-small` (`KHAZNA_EMBED=e5`). |
| Fusion | Reciprocal rank fusion (k = 60); superseded documents × 0.35 |
| Answer | `KHAZNA_LLM=extractive` (default) · `transformers` (Qwen2.5-1.5B-Instruct, streamed) · `ollama` (e.g. qwen2.5:7b) |
| API | FastAPI, server-sent events for streaming, rate limiting, strict CSP and security headers |
| Front end | Plain HTML/CSS/JS, IBM Plex fonts served locally, no third-party requests |

## Run it

```bash
pip install -r requirements.txt
python -m scripts.serve            # http://localhost:8000   (API docs at /docs)
```

With the local model:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-llm.txt
KHAZNA_LLM=transformers python -m scripts.serve
```

On a company server with Docker, optionally with a larger model served by Ollama:

```bash
docker compose up -d                                   # built-in mode
KHAZNA_LLM=ollama docker compose --profile ollama up -d
docker compose exec ollama ollama pull qwen2.5:7b
```

Tests and evaluation:

```bash
pip install -r requirements-dev.txt
ruff check . && pytest -q && python -m eval.run_eval
```

## API

| Endpoint | |
|---|---|
| `POST /api/ask` · `POST /api/ask/stream` | `{question, role}` → answer, citations, sources, what was masked and blocked |
| `GET /api/library?role=` · `GET /api/documents/{id}?role=` | Library with access per role; a document as that role may see it |
| `POST /api/upload` · `DELETE /api/upload/{id}` | Session uploads (header `X-Khazna-Session`) |
| `POST /api/scan` | Preview personal-data masking on any text |
| `GET /api/privacy` · `GET /api/eval` · `GET /health` | Egress counter and audit totals; evaluation results; health |

## Limits

- The demo library is small (21 documents), so search is easy. Larger libraries need the multilingual embedding option and a proper evaluation set of their own.
- Built-in mode quotes sentences, so very differently worded questions can miss; the model mode handles those.
- The 1.5B model on a free CPU is slow (several seconds per answer) and weaker in Arabic than a 7B model.
- Scanned PDFs need OCR, which is not included.

## Data

Sadeem Freight LLC and every document, person, ID and number in `khazna/data/corpus` are fictional, written for
this demo. The personal identifiers are realistic in format so that masking can be tested.

---

Built by Ayesha Lubna.
