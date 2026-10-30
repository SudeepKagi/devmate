from devmate.config import config
from devmate.observability.logger import get_logger

logger = get_logger(__name__)


def _is_hybrid_qdrant() -> bool:
    vector_store = config.get("vector_store", {}).get("provider", "chroma")
    retrieval_mode = config.get("vector_store", {}).get("retrieval_mode", "dense")
    rag_mode = config.get("rag", {}).get("mode", "semantic")
    return vector_store == "qdrant" and (retrieval_mode in ("hybrid", "sparse") or rag_mode == "hybrid")


def get_indexer():
    """Return the right index_codebase function based on vector_store in config."""
    vector_store = config.get("vector_store", {}).get("provider", "chroma")
    logger.info(f"Using vector store: {vector_store}")

    if _is_hybrid_qdrant():
        from .hybrid_qdrant import index_codebase
    elif vector_store == "qdrant":
        from .semantic_qdrant import index_codebase
    else:
        from .semantic_chroma import index_codebase
    return index_codebase


def get_index_inspector():
    """Return the right show_index function based on vector_store in config."""
    vector_store = config.get("vector_store", {}).get("provider", "chroma")

    if _is_hybrid_qdrant():
        from .hybrid_qdrant import show_index
    elif vector_store == "qdrant":
        from .semantic_qdrant import show_index
    else:
        from .semantic_chroma import show_index
    return show_index


def get_reindexer():
    """Return the right reindex_codebase function based on vector_store in config."""
    vector_store = config.get("vector_store", {}).get("provider", "chroma")

    if _is_hybrid_qdrant():
        from .hybrid_qdrant import reindex_codebase
    elif vector_store == "qdrant":
        from .semantic_qdrant import reindex_codebase
    else:
        from .semantic_chroma import reindex_codebase
    return reindex_codebase
