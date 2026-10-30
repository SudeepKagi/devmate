import os
from pathlib import Path
from langchain_qdrant import QdrantVectorStore, RetrievalMode, FastEmbedSparse
from langchain_core.documents import Document
from qdrant_client import QdrantClient

from devmate.config import config, get_project_collection_name
from devmate.context.indexers.code_parser import parse_file, get_source_files
from devmate.llm.factory import get_embedder
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

RETRIEVAL_MODE_MAP = {
    "dense": RetrievalMode.DENSE,
    "sparse": RetrievalMode.SPARSE,
    "hybrid": RetrievalMode.HYBRID,
}


def _get_retrieval_mode() -> RetrievalMode:
    mode = config.get("vector_store", {}).get("retrieval_mode", "hybrid")
    return RETRIEVAL_MODE_MAP.get(mode.lower(), RetrievalMode.HYBRID)


def index_codebase(repo_path: str, force: bool = False) -> QdrantVectorStore:
    """
    Parse all source files in repo_path, embed with dense + sparse vectors (BM25)
    and store in Qdrant. Skips indexing if collection already has data.
    """
    embedder = get_embedder()
    collection_name = get_project_collection_name(repo_path, store="qdrant")
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    retrieval_mode = _get_retrieval_mode()

    # Check if collection already has data
    client = QdrantClient(url=url, api_key=api_key)
    existing = [c.name for c in client.get_collections().collections]
    if not force and collection_name in existing:
        info = client.get_collection(collection_name)
        if info.points_count and info.points_count > 0:
            # Verify existing points belong to this project's repo_path
            scroll_res = client.scroll(collection_name=collection_name, limit=1, with_payload=True)
            if scroll_res and scroll_res[0]:
                payload = scroll_res[0][0].payload or {}
                meta = payload.get("metadata", {}) or payload
                sample_source = meta.get("source", "")
                if sample_source:
                    target_resolved = str(Path(repo_path).resolve())
                    sample_resolved = str(Path(sample_source).resolve())
                    try:
                        Path(sample_resolved).relative_to(Path(target_resolved))
                    except ValueError:
                        logger.info(
                            f"Collection '{collection_name}' contains data from '{sample_resolved}', "
                            f"not '{target_resolved}'. Re-indexing for current repository."
                        )
                        return reindex_codebase(repo_path)

            logger.info(f"Loaded existing hybrid index with {info.points_count} chunks from collection '{collection_name}'")
            return QdrantVectorStore.from_existing_collection(
                embedding=embedder,
                sparse_embedding=FastEmbedSparse(model_name="Qdrant/bm25"),
                retrieval_mode=retrieval_mode,
                url=url,
                api_key=api_key,
                collection_name=collection_name,
            )

    logger.info(f"Starting hybrid (dense + BM25) indexing of {repo_path} into collection '{collection_name}'")
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
        sparse_embedding=FastEmbedSparse(model_name="Qdrant/bm25"),
        retrieval_mode=retrieval_mode,
        url=url,
        api_key=api_key,
        collection_name=collection_name,
        batch_size=50,
    )

    logger.info(f"Hybrid indexing complete for '{collection_name}'. Total chunks: {len(docs)}")
    return vector_store


def reindex_codebase(repo_path: str) -> QdrantVectorStore:
    """Delete existing Qdrant collection and re-index from scratch with hybrid vectors."""
    collection_name = get_project_collection_name(repo_path)
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    client = QdrantClient(url=url, api_key=api_key)
    existing = [c.name for c in client.get_collections().collections]
    if collection_name in existing:
        client.delete_collection(collection_name)
        logger.info(f"Deleted existing Qdrant collection '{collection_name}'")
    return index_codebase(repo_path, force=True)


def show_index(vector_store: QdrantVectorStore = None) -> None:
    """Display all documents stored in the Qdrant collection with hybrid metadata."""
    from rich.console import Console
    console = Console()
    collection_name = get_project_collection_name()

    if vector_store is None:
        embedder = get_embedder()
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        client = QdrantClient(url=url, api_key=api_key)
        existing = [c.name for c in client.get_collections().collections]
        if collection_name not in existing:
            console.print(f"[yellow]Qdrant collection '{collection_name}' does not exist. Run /reindex to create it.[/yellow]\n")
            return
        retrieval_mode = _get_retrieval_mode()
        vector_store = QdrantVectorStore.from_existing_collection(
            embedding=embedder,
            sparse_embedding=FastEmbedSparse(model_name="Qdrant/bm25"),
            retrieval_mode=retrieval_mode,
            url=url,
            api_key=api_key,
            collection_name=collection_name,
        )

    client = vector_store.client
    results = client.scroll(collection_name=collection_name, with_payload=True, with_vectors=True, limit=1000)
    points = results[0]
    console.print(f"\n[bold]Hybrid Index (Dense + BM25) — {len(points)} chunks[/bold]\n")
    for i, point in enumerate(points):
        payload = point.payload or {}
        meta = payload.get("metadata", {}) or payload
        emb = point.vector or []
        console.print(f"[bold cyan]── Chunk {i+1} ──────────────────────────────────────[/bold cyan]")
        console.print(f"  File     : {meta.get('source', payload.get('source', 'unknown'))}")
        console.print(f"  Name     : {meta.get('name', payload.get('name', 'unknown'))} ({meta.get('type', payload.get('type', 'unknown'))})")
        console.print(f"  Lines    : {meta.get('start_line', payload.get('start_line'))} - {meta.get('end_line', payload.get('end_line'))}")
        if emb:
            console.print(f"  Embedding: present")
        code_preview = payload.get("page_content") or meta.get("page_content") or ""
        console.print(f"  Code     :\n[dim]{code_preview[:300]}[/dim]\n")

