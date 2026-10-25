import time
import chromadb
from rich.console import Console

from devmate.config import config, get_project_collection_name, get_chroma_persist_dir
from devmate.context.indexers.code_parser import parse_file, get_source_files
from devmate.llm.factory import get_embedder
from devmate.observability.logger import get_logger
from pathlib import Path

logger = get_logger(__name__)
console = Console()

def index_codebase(repo_path: str, force: bool = False) -> chromadb.Collection:
    """
    Parse all source files in repo_path, embed each chunk and store in ChromaDB.
    Returns the ChromaDB collection for use by the retriever.
    """
    embedder = get_embedder()
    persist_dir = get_chroma_persist_dir(repo_path)
    collection_name = get_project_collection_name(repo_path)
    chroma_client = chromadb.PersistentClient(path=persist_dir)
    collection = chroma_client.get_or_create_collection(name=collection_name)

    if not force and collection.count() > 0:
        # Check if collection data belongs to current repo_path
        results = collection.get(limit=1, include=["metadatas"])
        if results and results.get("metadatas"):
            sample_source = results["metadatas"][0].get("source", "")
            if sample_source:
                target_resolved = str(Path(repo_path).resolve())
                sample_resolved = str(Path(sample_source).resolve())
                try:
                    Path(sample_resolved).relative_to(Path(target_resolved))
                except ValueError:
                    logger.info(
                        f"Chroma index has chunks from '{sample_resolved}', not '{target_resolved}'. Reindexing."
                    )
                    return reindex_codebase(repo_path)

        logger.info(f"Loaded existing index with {collection.count()} chunks from collection '{collection_name}'")
        return collection

    logger.info(f"Starting semantic indexing of {repo_path}")

    files = get_source_files(repo_path)

    for i, filepath in enumerate(files):
        try:
            chunks = parse_file(filepath)
        except (SyntaxError, ValueError) as e:
            logger.error(f"Skipping {filepath}: {e}")
            continue

        for chunk in chunks:
            embedding = None
            for attempt in range(5):
                try:
                    embedding = embedder.embed_query(chunk.content)
                    break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        logger.warning(f"Rate limited by API. Backing off 3s (attempt {attempt+1}/5)...")
                        time.sleep(3)
                    else:
                        logger.error(f"Failed to embed chunk '{chunk.name}': {e}")
                        break

            if embedding is None:
                continue

            # Unique ID for each chunk - source + name + line prevents duplicates on re-index
            doc_id = f"{chunk.source}::{chunk.name}::{chunk.start_line}"

            collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk.content],
                metadatas=[{
                    "source": chunk.source,
                    "name": chunk.name,
                    "type": chunk.type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                }]
            )
            logger.debug(f"  Indexed {chunk.type} '{chunk.name}' from {filepath}")

    logger.info(f"Semantic indexing complete. Total chunks: {collection.count()}")
    return collection

def reindex_codebase(repo_path: str) -> chromadb.Collection:
    """Reset the ChromaDB collection and perform a fresh indexing of repo_path."""
    persist_dir = get_chroma_persist_dir(repo_path)
    collection_name = get_project_collection_name(repo_path)
    chroma_client = chromadb.PersistentClient(path=persist_dir)
    try:
        chroma_client.delete_collection(name=collection_name)
        logger.info(f"Deleted existing collection '{collection_name}'")
    except Exception:
        pass
    return index_codebase(repo_path, force=True)

def show_index(collection: chromadb.Collection = None) -> None:
    """Display documents stored in the ChromaDB collection."""
    if collection is None:
        persist_dir = get_chroma_persist_dir()
        collection_name = get_project_collection_name()
        chroma_client = chromadb.PersistentClient(path=persist_dir)
        collection = chroma_client.get_or_create_collection(name=collection_name)

    results = collection.get(include=["documents", "metadatas", "embeddings"])
    total = collection.count()
    console.print(f"\n[bold]Semantic Index (ChromaDB) - {total} chunks[/bold]\n")

    if total == 0:
        console.print("[yellow]Index is empty. Use '/reindex' to index the codebase.[/yellow]\n")
        return

    display_count = min(10, total)
    for i in range(display_count):
        doc = results["documents"][i]
        meta = results["metadatas"][i]
        emb = results["embeddings"][i] if results.get("embeddings") else []

        console.print(f"[bold cyan]-- Chunk {i+1} of {total} --------------------------------------[/bold cyan]")
        console.print(f"  File     : {meta['source']}")
        console.print(f"  Name     : {meta['name']} ({meta['type']})")
        console.print(f"  Lines    : {meta['start_line']} - {meta['end_line']}")
        if emb:
            console.print(f"  Embedding: [{', '.join(f'{v:.4f}' for v in emb[:5])}...] ({len(emb)} dims)")
        console.print(f"  Code     :\n[dim]{doc[:300]}[/dim]\n")

    if total > display_count:
        console.print(f"[dim]... and {total - display_count} more chunk(s).[/dim]\n")

