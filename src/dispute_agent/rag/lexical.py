"""Small BM25 keyword index over the policy clauses.

The corpus is only a few dozen clauses, so a pure-Python BM25 is enough. It
complements the embedding search on exact policy words such as "untracked",
"bank transfer" or "8/10" that a small embedding model tends to blur.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .chunker import Clause

STOPWORDS = set(
    "a an and are as at be by can for from has have how i if in is it its my of on or so that the their them "
    "they this to was were what when which who will with you your".split()
)
TOKEN = re.compile(r"[a-z0-9/]+")


def tokenize(text: str) -> list[str]:
    tokens = []
    for tok in TOKEN.findall(text.lower()):
        if tok in STOPWORDS:
            continue
        # Light stemming so "parts"/"part", "returned"/"return" match.
        for suffix in ("ing", "ed", "es", "s"):
            if len(tok) > 4 and tok.endswith(suffix):
                tok = tok[: -len(suffix)]
                break
        tokens.append(tok)
    return tokens


class BM25:
    def __init__(self, clauses: tuple[Clause, ...] | list[Clause], k1: float = 1.4, b: float = 0.75):
        self.ids = [c.clause_id for c in clauses]
        self.docs = [Counter(tokenize(c.embedding_text())) for c in clauses]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / max(len(self.lengths), 1)
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query: str) -> dict[str, float]:
        q = tokenize(query)
        out = {}
        for cid, doc, length in zip(self.ids, self.docs, self.lengths):
            s = 0.0
            for t in q:
                tf = doc.get(t, 0)
                if tf:
                    s += self.idf[t] * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / self.avg_len))
            out[cid] = s
        return out

    def rank(self, query: str, k: int) -> list[str]:
        scored = sorted(self.scores(query).items(), key=lambda kv: kv[1], reverse=True)
        return [cid for cid, s in scored[:k] if s > 0]
