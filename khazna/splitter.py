"""Minimal recursive character splitter, behaviour-compatible with LangChain's RecursiveCharacterTextSplitter
(keep_separator="start", strip_whitespace=True). Used when langchain-text-splitters is not installed, e.g. when
Khazna runs inside the browser (Pyodide). tests/test_khazna.py checks both give identical chunks for the library.
"""
from __future__ import annotations

import re


def _split_keep(text: str, sep: str) -> list[str]:
    if not sep:
        return list(text)
    parts = re.split(f"({re.escape(sep)})", text)
    out = [parts[i] + parts[i + 1] for i in range(1, len(parts), 2)]
    if len(parts) % 2 == 0:
        out += parts[-1:]
    return [s for s in [parts[0], *out] if s]


class RecursiveSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int, separators: list[str]):
        self.size, self.overlap, self.separators = chunk_size, chunk_overlap, separators

    def _merge(self, splits: list[str]) -> list[str]:
        docs, cur, total = [], [], 0
        for d in splits:
            n = len(d)
            if total + n > self.size:
                if cur:
                    joined = "".join(cur).strip()
                    if joined:
                        docs.append(joined)
                    while total > self.overlap or (total + n > self.size and total > 0):
                        total -= len(cur[0])
                        cur = cur[1:]
            cur.append(d)
            total += n
        joined = "".join(cur).strip()
        if joined:
            docs.append(joined)
        return docs

    def _split(self, text: str, separators: list[str]) -> list[str]:
        sep, rest = separators[-1], []
        for i, s in enumerate(separators):
            if not s:
                sep = s
                break
            if s in text:
                sep, rest = s, separators[i + 1:]
                break
        out, good = [], []
        for s in _split_keep(text, sep):
            if len(s) < self.size:
                good.append(s)
                continue
            if good:
                out.extend(self._merge(good))
                good = []
            out.extend(self._split(s, rest) if rest else [s])
        if good:
            out.extend(self._merge(good))
        return out

    def split_text(self, text: str) -> list[str]:
        return self._split(text, self.separators)
