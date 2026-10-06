"""Hybrid retrieval: BM25 keyword search + dense vector search in FAISS, fused with Reciprocal Rank Fusion.

Permission filtering happens inside the search itself: passages from documents the user's role may not read are
never scored, so they cannot leak into an answer, a citation or a "did you mean" hint.

Dense vectors come from either
* "lsa": TF-IDF over words and character n-grams reduced with truncated SVD (built here, no download), or
* "e5":  intfloat/multilingual-e5-small sentence embeddings (true cross-lingual meaning; downloaded once).
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

import faiss
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from .config import E5_MODEL, RRF_K
from .corpus import Chunk
from .glossary import expand
from .text import normalise_ar, tokens


@dataclass
class Hit:
    chunk: Chunk
    score: float          # fused RRF score
    bm25: float
    dense: float
    rank_bm25: int | None
    rank_dense: int | None


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.4, b: float = 0.72):
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in docs]
        self.len = np.array([len(d) for d in docs], dtype=float)
        self.avg = float(self.len.mean()) if len(docs) else 1.0
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def scores(self, q: list[str], weights: dict[str, float] | None = None) -> np.ndarray:
        out = np.zeros(len(self.tf))
        for t in set(q):
            idf = self.idf.get(t)
            if idf is None:
                continue
            w = (weights or {}).get(t, 1.0)
            for i, tf in enumerate(self.tf):
                f = tf.get(t)
                if f:
                    out[i] += w * idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
        return out


class LSAEncoder:
    name = "lsa"

    def fit(self, texts: list[str]) -> np.ndarray:
        n_comp = max(2, min(192, len(texts) - 1))
        self.word = TfidfVectorizer(analyzer=lambda s: tokens(s) + expand_only(s), sublinear_tf=True, min_df=1)
        self.char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=1,
                                    preprocessor=lambda s: normalise_ar(s).lower())
        from scipy.sparse import hstack
        X = hstack([self.word.fit_transform(texts), 0.6 * self.char.fit_transform(texts)]).tocsr()
        self.svd = TruncatedSVD(n_components=n_comp, random_state=0)
        return normalize(self.svd.fit_transform(X)).astype("float32")

    def query(self, q: str) -> np.ndarray:
        from scipy.sparse import hstack
        X = hstack([self.word.transform([q]), 0.6 * self.char.transform([q])]).tocsr()
        return normalize(self.svd.transform(X)).astype("float32")


def expand_only(s: str) -> list[str]:
    base = set(tokens(s))
    return [t for t in expand(s) if t not in base]


class E5Encoder:
    name = "e5"

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.m = SentenceTransformer(E5_MODEL, device="cpu")

    def fit(self, texts: list[str]) -> np.ndarray:
        return self.m.encode([f"passage: {t}" for t in texts], normalize_embeddings=True, batch_size=32).astype("float32")

    def query(self, q: str) -> np.ndarray:
        return self.m.encode([f"query: {q}"], normalize_embeddings=True).astype("float32")


def make_encoder(kind: str):
    if kind == "e5":
        try:
            return E5Encoder()
        except Exception:      # model unavailable offline: fall back to the built-in encoder
            return LSAEncoder()
    return LSAEncoder()


class Index:
    def __init__(self, chunks: list[Chunk], embed: str = "lsa", encoder=None, superseded: set[str] | None = None):
        self.chunks = chunks
        self.superseded = np.array([c.doc in (superseded or set()) for c in chunks])
        self.ids = {c.id: i for i, c in enumerate(chunks)}
        self.doc_of = np.array([c.doc for c in chunks])
        texts = [f"{c.section}. {c.text}" for c in chunks]
        self.bm25 = BM25([tokens(t) for t in texts])
        self.encoder = encoder or make_encoder(embed)
        vecs = self.encoder.fit(texts) if encoder is None else encoder.fit(texts)
        self.faiss = faiss.IndexIDMap(faiss.IndexFlatIP(vecs.shape[1]))
        self.faiss.add_with_ids(vecs, np.arange(len(chunks), dtype="int64"))
        self.mode = self.encoder.name

    def _allowed(self, docs: set[str] | None) -> np.ndarray:
        if docs is None:
            return np.arange(len(self.chunks))
        return np.where(np.isin(self.doc_of, list(docs)))[0]

    def search(self, query: str, docs: set[str] | None = None, k: int = 5, method: str = "hybrid") -> list[Hit]:
        allowed = self._allowed(docs)
        if len(allowed) == 0:
            return []
        q_base = tokens(query)
        q_exp = expand(query)
        weights = {t: (1.0 if t in q_base else 0.6) for t in q_exp}
        # --- BM25 over allowed passages only
        bm = self.bm25.scores(q_exp, weights)
        mask = np.zeros(len(self.chunks), bool)
        mask[allowed] = True
        bm_masked = np.where(mask, bm, -1.0)
        order_bm = [i for i in np.argsort(-bm_masked) if mask[i] and bm[i] > 0][: max(k * 4, 20)]
        # --- dense search inside FAISS, restricted to allowed ids
        qv = self.encoder.query(query)
        sel = faiss.IDSelectorBatch(allowed.astype("int64"))
        params = faiss.SearchParameters(sel=sel)
        dists, ids = self.faiss.search(qv, min(max(k * 4, 20), len(allowed)), params=params)
        order_dn = [int(i) for i in ids[0] if i >= 0]
        dense = {int(i): float(d) for d, i in zip(dists[0], ids[0]) if i >= 0}
        rb = {i: r for r, i in enumerate(order_bm)}
        rd = {i: r for r, i in enumerate(order_dn)}
        if method == "bm25":
            cand = order_bm
            fused = {i: 1 / (RRF_K + rb[i]) for i in cand}
        elif method == "dense":
            cand = order_dn
            fused = {i: 1 / (RRF_K + rd[i]) for i in cand}
        else:
            cand = set(order_bm) | set(order_dn)
            fused = {i: (1 / (RRF_K + rb[i]) if i in rb else 0) + (1 / (RRF_K + rd[i]) if i in rd else 0) for i in cand}
        for i in fused:                      # outdated versions rank below current ones
            if self.superseded[i]:
                fused[i] *= 0.35
        top = sorted(fused, key=lambda i: -fused[i])[:k]
        return [Hit(self.chunks[i], fused[i], float(bm[i]), dense.get(i, 0.0), rb.get(i), rd.get(i)) for i in top]
