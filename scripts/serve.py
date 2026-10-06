"""Run the web app locally:  python -m scripts.serve  ->  http://localhost:8000

Environment options (all optional):
  KHAZNA_LLM=extractive|transformers|ollama   answer mode (default: extractive, no model)
  KHAZNA_EMBED=lsa|e5                         dense retriever (default: lsa, no download)
  KHAZNA_EGRESS_GUARD=1|0                     block outbound network after start-up (default: 1)
"""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("khazna.api:api", host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")),
                proxy_headers=True, timeout_keep_alive=30)
