from devmate.config import config
from devmate.observability.logger import get_logger

logger = get_logger(__name__)


def _is_hybrid_qdrant() -> bool:
    vector_store = config.get("vector_store", {}).get("provider", "chroma")
    retrieval_mode = config.get("vector_store", {}).get("retrieval_mode", "dense")
    rag_mode = config.get("rag", {}).get("mode", "semantic")
    return vector_store == "qdrant" and (retrieval_mode in ("hybrid", "sparse") or rag_mode == "hybrid")


def get_retriever():
    """Return the right retrieve function based on vector_store and rag mode in config."""
    vector_store = config.get("vector_store", {}).get("provider", "chroma")
    logger.info(f"Using vector store for retrieval: {vector_store}")

    if _is_hybrid_qdrant():
        from .hybrid_qdrant import retrieve
    elif vector_store == "qdrant":
        from .semantic_qdrant import retrieve
    else:
        from .semantic_chroma import retrieve

    return retrieve
