"""ChromaDB vector store over the policy clauses.

Embeddings come from ChromaDB's built-in local model (all-MiniLM-L6-v2 via
ONNX), so retrieval needs no API key. The index rebuilds itself whenever the
policy text changes.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from ..config import load_config, path
from ..schemas import RetrievedClause
from .chunker import Clause, clauses_by_id, load_clauses
from .lexical import BM25

# Reciprocal rank fusion constant; 60 is the value from the original RRF paper.
RRF_K = 60


def _fingerprint(clauses: tuple[Clause, ...]) -> str:
    h = hashlib.sha256()
    for c in clauses:
        h.update(c.clause_id.encode())
        h.update(c.embedding_text().encode())
    return h.hexdigest()[:16]


class PolicyStore:
    def __init__(self, persist_dir: str | None = None, collection: str | None = None):
        cfg = load_config()["rag"]
        self.top_k = cfg["top_k"]
        self.mode = cfg.get("mode", "hybrid")
        self.bm25 = BM25(load_clauses())
        self.client = chromadb.PersistentClient(
            path=str(persist_dir or path("rag.persist_dir")),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection_name = collection or cfg["collection"]
        self.embedder = DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            self.collection_name, embedding_function=self.embedder, metadata={"hnsw:space": "cosine"}
        )

    def build(self, force: bool = False) -> int:
        """Index all clauses. Skips work when the stored fingerprint matches."""
        clauses = load_clauses()
        fp = _fingerprint(clauses)
        meta = self.collection.metadata or {}
        if not force and meta.get("fingerprint") == fp and self.collection.count() == len(clauses):
            return 0
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            self.collection_name, embedding_function=self.embedder, metadata={"fingerprint": fp, "hnsw:space": "cosine"}
        )
        self.collection.add(
            ids=[c.clause_id for c in clauses],
            documents=[c.embedding_text() for c in clauses],
            metadatas=[{"doc_title": c.doc_title, "section": c.section, "url": c.url} for c in clauses],
        )
        return len(clauses)

    def dense_rank(self, query: str, k: int) -> list[tuple[str, float]]:
        res = self.collection.query(query_texts=[query], n_results=min(k, self.collection.count()))
        return list(zip(res["ids"][0], (float(d) for d in res["distances"][0])))

    def retrieve(self, query: str, k: int | None = None, mode: str | None = None) -> list[RetrievedClause]:
        """Top-k clauses for a query. mode: dense, lexical or hybrid (rank fusion of both)."""
        k = k or self.top_k
        mode = mode or self.mode
        pool = max(k * 4, 12)
        dense = self.dense_rank(query, pool) if mode in ("dense", "hybrid") else []
        distances = dict(dense)
        if mode == "dense":
            ranked = [cid for cid, _ in dense]
        elif mode == "lexical":
            ranked = self.bm25.rank(query, pool)
        else:
            fused: dict[str, float] = {}
            for ranking in ([cid for cid, _ in dense], self.bm25.rank(query, pool)):
                for pos, cid in enumerate(ranking):
                    fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + pos + 1)
            ranked = sorted(fused, key=fused.get, reverse=True)

        by_id = clauses_by_id()
        out = []
        for cid in ranked[:k]:
            clause = by_id.get(cid)
            if clause is None:
                continue
            rc = clause.as_retrieved()
            rc.distance = round(distances[cid], 4) if cid in distances else None
            rc.query = query
            out.append(rc)
        return out


@lru_cache(maxsize=1)
def get_store() -> PolicyStore:
    store = PolicyStore()
    store.build()
    return store
