import chromadb

from devmate.config import config
from devmate.llm.factory import get_embedder
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

def retrieve(query: str, k: int = 5) -> list[dict]:
    """
    Embed the query and find the k most similar chunks in ChromaDB.
    Returns a list of results with content and metadata.
    """
    chroma_client = chromadb.PersistentClient(path=config["chromadb"]["persist_dir"])
    collection = chroma_client.get_or_create_collection(name=config["chromadb"]["collection_name"])

    logger.info(f"Retrieving top {k} chunks for query: {query}")

    if collection.count() == 0:
        logger.warning("ChromaDB collection is empty. Nothing to retrieve.")
        return []

    # Use the same embedder as the indexer - model must match or results will be wrong
    embedder = get_embedder()
    query_embedding = embedder.embed_query(query)

    # Make sure k doesn't exceed collection count
    n_results = min(k, collection.count())

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    if results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            chunks.append({
                "content": doc,
                "source": meta["source"],
                "name": meta["name"],
                "type": meta["type"],
                "start_line": meta["start_line"],
                "end_line": meta["end_line"],
                "distance": dist,  # lower = more similar
            })
            logger.debug(f"  Retrieved {meta['type']} '{meta['name']}' from {meta['source']} (distance: {dist:.4f})")

    logger.info(f"Retrieved {len(chunks)} chunks")
    return chunks
