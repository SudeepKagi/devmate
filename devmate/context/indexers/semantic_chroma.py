import time
import chromadb

from devmate.config import config
from devmate.context.indexers.code_parser import parse_file, get_source_files
from devmate.llm.factory import get_embedder
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

def index_codebase(repo_path: str) -> chromadb.Collection:
    """
    Parse all Python files in repo_path, embed each chunk and store in ChromaDB.
    Returns the ChromaDB collection for use by the retriever.
    """
    embedder = get_embedder()
    chroma_client = chromadb.PersistentClient(path=config["chromadb"]["persist_dir"])
    collection = chroma_client.get_or_create_collection(name=config["chromadb"]["collection_name"])

    logger.info(f"Starting semantic indexing of {repo_path}")

    files = get_source_files(repo_path)

    for filepath in files:
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
