import os
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from qdrant_client import QdrantClient

from devmate.config import config
from devmate.context.indexers.code_parser import parse_file, get_source_files
from devmate.llm.factory import get_embedder
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

def index_codebase(repo_path: str) -> QdrantVectorStore:
    """
    Parse all source files in repo_path, embed each chunk and store in Qdrant.
    Returns the QdrantVectorStore. Skips indexing if collection already has data.
    """
    embedder = get_embedder()
    collection_name = config["qdrant"]["collection_name"]
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")

    # Check if collection already has data
    client = QdrantClient(url=url, api_key=api_key)
    existing = [c.name for c in client.get_collections().collections]
    if collection_name in existing:
        info = client.get_collection(collection_name)
        if info.points_count and info.points_count > 0:
            logger.info(f"Loaded existing index with {info.points_count} chunks")
            return QdrantVectorStore.from_existing_collection(
                embedding=embedder,
                url=url,
                api_key=api_key,
                collection_name=collection_name,
            )

    logger.info(f"Starting semantic indexing of {repo_path}")
    files = get_source_files(repo_path)
    docs = []

    for filepath in files:
        try:
            chunks = parse_file(filepath)
        except (SyntaxError, ValueError) as e:
            logger.error(f"Skipping {filepath}: {e}")
            continue

        for chunk in chunks:
            docs.append(Document(
                page_content=chunk.content,
                metadata={
                    "source": chunk.source,
                    "name": chunk.name,
                    "type": chunk.type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                }
            ))
            logger.debug(f"  Indexed {chunk.type} '{chunk.name}' from {filepath}")

    vector_store = QdrantVectorStore.from_documents(
        docs,
        embedder,
        url=url,
        api_key=api_key,
        collection_name=collection_name,
        batch_size=50,
    )

    logger.info(f"Semantic indexing complete. Total chunks: {len(docs)}")
    return vector_store

def reindex_codebase(repo_path: str) -> QdrantVectorStore:
    """Delete existing Qdrant collection and re-index from scratch."""
    collection_name = config["qdrant"]["collection_name"]
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    client = QdrantClient(url=url, api_key=api_key)
    existing = [c.name for c in client.get_collections().collections]
    if collection_name in existing:
        client.delete_collection(collection_name)
        logger.info(f"Deleted existing Qdrant collection '{collection_name}'")
    return index_codebase(repo_path)

def show_index(vector_store: QdrantVectorStore = None) -> None:
    """Display all documents stored in the Qdrant collection."""
    from rich.console import Console
    console = Console()

    if vector_store is None:
        embedder = get_embedder()
        collection_name = config["qdrant"]["collection_name"]
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        client = QdrantClient(url=url, api_key=api_key)
        existing = [c.name for c in client.get_collections().collections]
        if collection_name not in existing:
            console.print(f"[yellow]Qdrant collection '{collection_name}' does not exist. Run /reindex to create it.[/yellow]\n")
            return
        vector_store = QdrantVectorStore.from_existing_collection(
            embedding=embedder,
            url=url,
            api_key=api_key,
            collection_name=collection_name,
        )

    client = vector_store.client
    collection_name = config["qdrant"]["collection_name"]
    results = client.scroll(collection_name=collection_name, with_payload=True, with_vectors=True, limit=1000)
    points = results[0]
    console.print(f"\n[bold]Semantic Index - {len(points)} chunks[/bold]\n")
    for i, point in enumerate(points):
        payload = point.payload or {}
        emb = point.vector or []
        console.print(f"[bold cyan]-- Chunk {i+1} --------------------------------------[/bold cyan]")
        console.print(f"  File     : {payload.get('source')}")
        console.print(f"  Name     : {payload.get('name')} ({payload.get('type')})")
        console.print(f"  Lines    : {payload.get('start_line')} - {payload.get('end_line')}")
        if emb:
            console.print(f"  Embedding: [{', '.join(f'{v:.4f}' for v in emb[:5])}...] ({len(emb)} dims)")
        console.print(f"  Code     :\n[dim]{payload.get('page_content', '')[:300]}[/dim]\n")
