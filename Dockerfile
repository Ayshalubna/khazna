# Production image. The index (21 documents) builds at start-up in under a second; no model download is needed
# in the default mode. For a local model, build with --build-arg EXTRAS=llm and set KHAZNA_LLM=transformers,
# or run Ollama next to it (see docker-compose.yml).
FROM python:3.10-slim

ARG EXTRAS=""
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    KHAZNA_DB=/data/khazna_audit.db PORT=8000 HF_HOME=/models

RUN useradd -m -u 1000 app && mkdir -p /data /models && chown app:app /data /models

WORKDIR /app
COPY requirements*.txt ./
RUN pip install -r requirements.txt \
    && if [ "$EXTRAS" = "llm" ]; then pip install torch --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements-llm.txt; fi
COPY --chown=app:app . .
USER app

EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health')"
# one worker: visitors' temporary uploads live in this process's memory
CMD ["sh", "-c", "uvicorn khazna.api:api --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*' --timeout-keep-alive 30"]
