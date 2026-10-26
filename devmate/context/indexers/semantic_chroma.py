import os
import time
from pathlib import Path
import chromadb
from rich.console import Console

from devmate.config import config, get_project_collection_name, get_chroma_persist_dir
from devmate.context.indexers.code_parser import parse_file, get_source_files
from devmate.llm.factory import get_embedder
from devmate.observability.logger import get_logger

logger = get_logger(__name__)
console = Console()


def _get_collection(repo_path: str = None) -> chromadb.Collection:
    """Open or create the ChromaDB collection scoped to the repo path."""
    persist_dir = get_chroma_persist_dir(repo_path)
    collection_name = get_project_collection_name(repo_path)
    chroma_client = chromadb.PersistentClient(path=persist_dir)
    return chroma_client.get_or_create_collection(name=collection_name)


def _get_indexed_mtimes(collection: chromadb.Collection) -> dict[str, float]:
    """Read all chunk metadata from ChromaDB and return {filepath: mtime}."""
    results = collection.get(include=["metadatas"])
    mtimes: dict[str, float] = {}
    for meta in results.get("metadatas", []):
        if not meta:
            continue
        source = meta.get("source", "")
        mtime = meta.get("mtime", 0.0)
        if source and mtime > mtimes.get(source, 0.0):
            mtimes[source] = mtime
    return mtimes


def _delete_file_chunks(collection: chromadb.Collection, filepath: str) -> None:
    """Remove every chunk belonging to filepath from the collection."""
    results = collection.get(where={"source": filepath}, include=[])
    if results and results.get("ids"):
        collection.delete(ids=results["ids"])
        logger.debug(f"Deleted {len(results['ids'])} chunks for {filepath}")


def _embed_file(collection: chromadb.Collection, filepath: str, mtime: float) -> int:
    """Parse, embed, and upsert all chunks of a single file with mtime tracking."""
    embedder = get_embedder()
    try:
        chunks = parse_file(filepath)
    except (SyntaxError, ValueError) as e:
        logger.error(f"Skipping {filepath}: {e}")
        return 0

    indexed_count = 0
    for chunk in chunks:
        doc_id = f"{chunk.source}::{chunk.name}::{chunk.start_line}"
        embedding = None
        for attempt in range(5):
            try:
                embedding = embedder.embed_query(chunk.content)
                break
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    logger.warning(f"Rate limited by API. Backing off 2s (attempt {attempt+1}/5)...")
                    time.sleep(2)
                else:
                    logger.error(f"Failed to embed chunk '{chunk.name}': {e}")
                    break

        if embedding is None:
            continue

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
                "mtime": mtime,
            }]
        )
        indexed_count += 1

    return indexed_count


def index_single_file(filepath: str, repo_path: str = None) -> None:
    """Reindex one file immediately — called by the watchdog handler on modify/create."""
    if not os.path.exists(filepath):
        return
    collection = _get_collection(repo_path)
    mtime = os.path.getmtime(filepath)
    _delete_file_chunks(collection, filepath)
    count = _embed_file(collection, filepath, mtime)
    logger.info(f"Watchdog indexed {filepath} -> {count} chunks")


def remove_file_from_index(filepath: str, repo_path: str = None) -> None:
    """Remove all chunks for a deleted file — called by the watchdog handler."""
    collection = _get_collection(repo_path)
    _delete_file_chunks(collection, filepath)
    logger.info(f"Watchdog removed {filepath} from index")


def index_codebase(repo_path: str, force: bool = False) -> chromadb.Collection:
    """Incrementally index all source files in repo_path into ChromaDB.
    Skips unchanged files based on mtime to minimize embedding cost.
    """
    collection = _get_collection(repo_path)
    if force:
        try:
            persist_dir = get_chroma_persist_dir(repo_path)
            collection_name = get_project_collection_name(repo_path)
            client = chromadb.PersistentClient(path=persist_dir)
            client.delete_collection(name=collection_name)
            collection = client.get_or_create_collection(name=collection_name)
        except Exception:
            pass

    current_files = {f: os.path.getmtime(f) for f in get_source_files(repo_path)}
    indexed_mtimes = _get_indexed_mtimes(collection) if not force else {}

    # 1. Remove chunks for files that no longer exist
    deleted = set(indexed_mtimes) - set(current_files)
    for filepath in deleted:
        logger.info(f"Removing deleted file from index: {filepath}")
        _delete_file_chunks(collection, filepath)

    # 2. Index new or changed files, skip unchanged
    added = 0
    changed = 0
    skipped = 0

    for filepath, mtime in current_files.items():
        if indexed_mtimes.get(filepath) == mtime:
            skipped += 1
            continue

        if filepath in indexed_mtimes:
            _delete_file_chunks(collection, filepath)
            changed += 1
        else:
            added += 1

        _embed_file(collection, filepath, mtime)

    logger.info(
        f"Index updated — added: {added}, changed: {changed}, deleted: {len(deleted)}, skipped: {skipped} | total: {collection.count()}"
    )
    return collection


def reindex_codebase(repo_path: str) -> chromadb.Collection:
    """Reset the ChromaDB collection and perform a fresh indexing of repo_path."""
    return index_codebase(repo_path, force=True)


def show_index(collection: chromadb.Collection = None) -> None:
    """Display documents stored in the ChromaDB collection."""
    if collection is None:
        collection = _get_collection()

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
        console.print(f"  File     : {meta.get('source', '')}")
        console.print(f"  Name     : {meta.get('name', '')} ({meta.get('type', '')})")
        console.print(f"  Lines    : {meta.get('start_line', '')} - {meta.get('end_line', '')}")
        if emb:
            console.print(f"  Embedding: [{', '.join(f'{v:.4f}' for v in emb[:5])}...] ({len(emb)} dims)")
        console.print(f"  Code     :\n[dim]{doc[:300]}[/dim]\n")

    if total > display_count:
        console.print(f"[dim]... and {total - display_count} more chunk(s).[/dim]\n")
