"""
Hybrid retriever for ChromaDB combining BM25 keyword scoring and dense vector embeddings
via Reciprocal Rank Fusion (RRF).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

import chromadb

from devmate.config import config, get_chroma_persist_dir, get_project_collection_name
from devmate.llm.factory import get_embedder
from devmate.observability.logger import get_logger

logger = get_logger(__name__)


def tokenize_code(text: str) -> List[str]:
    """
    Tokenize code and natural language text.
    Handles camelCase, PascalCase, snake_case, and standard word boundaries.
    """
    # Split camelCase / PascalCase
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    # Split punctuation and non-alphanumeric
    words = re.findall(r"[a-zA-Z0-9_]+", s1)
    tokens = []
    for w in words:
        # Also split snake_case
        subwords = w.split("_")
        for sub in subwords:
            t = sub.strip().lower()
            if len(t) > 1:  # ignore 1-char tokens
                tokens.append(t)
    return tokens


class BM25Index:
    """
    In-memory BM25Okapi index over collection chunks.
    Fast, lightweight, zero extra dependencies.
    """

    def __init__(self, documents: List[str], doc_ids: List[str], k1: float = 1.5, b: float = 0.75):
        self.doc_ids = doc_ids
        self.k1 = k1
        self.b = b
        self.corpus_size = len(documents)

        # Tokenize all documents
        self.doc_tokens: List[List[str]] = [tokenize_code(doc) for doc in documents]
        self.doc_len: List[int] = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl: float = sum(self.doc_len) / max(1, self.corpus_size)

        # Term document frequency
        self.df: Dict[str, int] = {}
        for tokens in self.doc_tokens:
            unique_terms = set(tokens)
            for term in unique_terms:
                self.df[term] = self.df.get(term, 0) + 1

        # Term frequency maps per document
        self.tf_list: List[Counter[str]] = [Counter(tokens) for tokens in self.doc_tokens]

    def idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        # Standard Lucene/BM25 Okapi IDF formulation
        return math.log(1.0 + (self.corpus_size - n + 0.5) / (n + 0.5))

    def score(self, query_tokens: List[str], doc_idx: int) -> float:
        score = 0.0
        doc_len = self.doc_len[doc_idx]
        tf_map = self.tf_list[doc_idx]

        for token in query_tokens:
            if token not in tf_map:
                continue
            freq = tf_map[token]
            idf = self.idf(token)
            numerator = freq * (self.k1 + 1.0)
            denominator = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / max(1.0, self.avgdl)))
            score += idf * (numerator / denominator)

        return score

    def search(self, query: str, top_n: int = 50) -> List[tuple[str, float, int]]:
        """Return list of (doc_id, bm25_score, rank_1_based)."""
        query_tokens = tokenize_code(query)
        if not query_tokens:
            return []

        scores = [
            (self.doc_ids[idx], self.score(query_tokens, idx))
            for idx in range(self.corpus_size)
        ]
        # Filter scores > 0 and sort descending
        scores = [(doc_id, s) for doc_id, s in scores if s > 0.0]
        scores.sort(key=lambda x: x[1], reverse=True)

        return [
            (doc_id, score, rank + 1)
            for rank, (doc_id, score) in enumerate(scores[:top_n])
        ]


def retrieve(query: str, k: int = 5, repo_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve top-k chunks using hybrid search:
    1. Dense cosine similarity from ChromaDB
    2. BM25Okapi keyword scoring over all chunks
    3. Reciprocal Rank Fusion (RRF) with constant k=60
    """
    persist_dir = get_chroma_persist_dir(repo_path)
    collection_name = get_project_collection_name(repo_path, store="chromadb")
    chroma_client = chromadb.PersistentClient(path=persist_dir)
    collection = chroma_client.get_or_create_collection(name=collection_name)

    total_count = collection.count()
    if total_count == 0:
        logger.warning("ChromaDB collection is empty. Nothing to retrieve.")
        return []

    # 1. Fetch all documents & metadatas to build BM25 index and doc lookup
    data = collection.get(include=["documents", "metadatas"])
    doc_ids = data["ids"]
    docs = data["documents"]
    metadatas = data["metadatas"]
    doc_map: Dict[str, Dict[str, Any]] = {
        doc_id: {"content": doc, "meta": meta}
        for doc_id, doc, meta in zip(doc_ids, docs, metadatas)
    }

    # 2. BM25 Search
    bm25 = BM25Index(docs, doc_ids)
    top_n_bm25 = min(50, total_count)
    bm25_results = bm25.search(query, top_n=top_n_bm25)
    bm25_ranks: Dict[str, int] = {doc_id: rank for doc_id, _, rank in bm25_results}

    # 3. Dense Vector Search
    embedder = get_embedder()
    query_embedding = embedder.embed_query(query)
    n_dense = min(50, total_count)
    dense_resp = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_dense,
        include=["documents", "metadatas", "distances"],
    )

    dense_ranks: Dict[str, int] = {}
    dense_distances: Dict[str, float] = {}
    if dense_resp.get("ids") and dense_resp["ids"][0]:
        for rank, (doc_id, dist) in enumerate(zip(dense_resp["ids"][0], dense_resp["distances"][0])):
            dense_ranks[doc_id] = rank + 1
            dense_distances[doc_id] = dist

    # 4. Reciprocal Rank Fusion (RRF)
    # RRF_Score(d) = sum_{m in {bm25, dense}} 1 / (60 + rank_m(d))
    RRF_K = 60.0
    all_candidate_ids = set(bm25_ranks.keys()) | set(dense_ranks.keys())

    fused_scores: List[tuple[str, float]] = []
    for doc_id in all_candidate_ids:
        score = 0.0
        if doc_id in dense_ranks:
            score += 1.0 / (RRF_K + dense_ranks[doc_id])
        if doc_id in bm25_ranks:
            score += 1.0 / (RRF_K + bm25_ranks[doc_id])
        fused_scores.append((doc_id, score))

    fused_scores.sort(key=lambda x: x[1], reverse=True)

    # 5. Format Top-K Results
    chunks = []
    for doc_id, rrf_score in fused_scores[:k]:
        item = doc_map.get(doc_id)
        if not item:
            continue
        meta = item["meta"] or {}
        chunks.append({
            "content": item["content"],
            "source": meta.get("source", ""),
            "name": meta.get("name", ""),
            "type": meta.get("type", "block"),
            "start_line": meta.get("start_line", 1),
            "end_line": meta.get("end_line", 1),
            "distance": round(1.0 - rrf_score, 4),  # Lower is better convention
            "rrf_score": round(rrf_score, 6),
            "dense_rank": dense_ranks.get(doc_id),
            "bm25_rank": bm25_ranks.get(doc_id),
        })

    logger.info(f"Hybrid retrieved {len(chunks)} chunks for query: '{query}'")
    return chunks
