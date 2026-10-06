"""Build the in-browser version of Khazna (no server) into dist/static/.

The same Python engine runs in the visitor's browser with Pyodide; web/bridge.js answers the app's /api/* calls
locally. This is what the free Hugging Face static Space serves:  python -m scripts.build_static
"""
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "static"
SPACE_README = """---
title: Khazna — Private Document Assistant
emoji: 🗄️
colorFrom: blue
colorTo: yellow
sdk: static
app_file: index.html
pinned: true
short_description: Private Arabic-English RAG with PII masking, no egress
---

Live demo of [github.com/Ayshalubna/khazna](https://github.com/Ayshalubna/khazna). The whole engine runs inside
your browser (Pyodide): documents, questions and uploads never leave your device. All data is fictional.
"""


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for name in ("app.js", "i18n.js", "bridge.js"):
        shutil.copy(ROOT / "web" / name, OUT / name)
    for font in (ROOT / "web" / "fonts").glob("*.woff2"):          # flat layout: one folder to upload
        shutil.copy(font, OUT / font.name)
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8").replace("/fonts/", "")
    (OUT / "styles.css").write_text(css, encoding="utf-8")
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    html = (html.replace('href="/fonts/', 'href="').replace('href="/styles.css"', 'href="styles.css"')
                .replace('<script src="/i18n.js"></script>', '<script src="bridge.js"></script>\n<script src="i18n.js"></script>')
                .replace('<script src="/app.js"></script>', '<script src="app.js"></script>'))
    assert "bridge.js" in html
    (OUT / "index.html").write_text(html, encoding="utf-8")
    with zipfile.ZipFile(OUT / "khazna.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted((ROOT / "khazna").rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and f.name not in ("api.py", "hardening.py"):
                z.write(f, f.relative_to(ROOT).as_posix())
        for name in ("results.json", "results_llm.json"):
            f = ROOT / "eval" / name
            if f.exists():
                z.write(f, f"eval/{name}")
    (OUT / "README.md").write_text(SPACE_README, encoding="utf-8")
    print(f"built {OUT} ({sum(f.stat().st_size for f in OUT.iterdir()) // 1024} KB, {len(list(OUT.iterdir()))} files)")


if __name__ == "__main__":
    main()
