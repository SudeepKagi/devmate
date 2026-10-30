import os
from langchain_qdrant import QdrantVectorStore, RetrievalMode, FastEmbedSparse

from devmate.config import config, get_project_collection_name
from devmate.llm.factory import get_embedder
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

RETRIEVAL_MODE_MAP = {
    "dense": RetrievalMode.DENSE,
    "sparse": RetrievalMode.SPARSE,
    "hybrid": RetrievalMode.HYBRID,
}


def retrieve(query: str, k: int = 5, repo_path: str = None) -> list[dict]:
    """
    Retrieve top-k chunks using dense + BM25 sparse vectors (hybrid search) from Qdrant.
    """
    embedder = get_embedder()
    collection_name = get_project_collection_name(repo_path, store="qdrant")
    mode = config.get("vector_store", {}).get("retrieval_mode", "hybrid")
    retrieval_mode = RETRIEVAL_MODE_MAP.get(mode.lower(), RetrievalMode.HYBRID)

    vector_store = QdrantVectorStore.from_existing_collection(
        embedding=embedder,
        sparse_embedding=FastEmbedSparse(model_name="Qdrant/bm25"),
        retrieval_mode=retrieval_mode,
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
        collection_name=collection_name,
    )

    logger.info(f"Retrieving top {k} chunks — mode: {mode} — query: {query}")
    results = vector_store.similarity_search_with_score(query, k=k)

    chunks = []
    for doc, score in results:
        meta = doc.metadata
        chunks.append({
            "content": doc.page_content,
            "source": meta["source"],
            "name": meta["name"],
            "type": meta["type"],
            "start_line": meta["start_line"],
            "end_line": meta["end_line"],
            "distance": score,
        })
        logger.debug(f"  Retrieved {meta['type']} '{meta['name']}' from {meta['source']} (score: {score:.4f})")

    logger.info(f"Retrieved {len(chunks)} chunks")
    return chunks

