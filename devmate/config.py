import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

# Built-in fallback defaults
DEFAULT_CONFIG = {
    "llm": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "judge_model": "gpt-4o-mini",
    },
    "embeddings": {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "dims": 1536,
    },
    "vector_store": {
        "provider": "chroma",
        "retrieval_mode": "dense",
    },
    "chromadb": {
        "persist_dir": ".devmate/chromadb/",
        "collection_name": "codebase",
    },
    "qdrant": {
        "collection_name": "devmate",
    },
    "semantic_cache": {
        "enabled": True,
        "redis_url": "redis://localhost:6379",
        "threshold": 0.85,
        "ttl": 86400,
    },
    "tasks": {
        "db_path": ".devmate/tasks.db",
    },
    "memory": {
        "db_path": ".devmate/memory/memory.db",
        "summarize_at_tokens": 4000,
        "keep_last_messages": 20,
    },
    "skills": {
        "skills_dir": ".devmate/skills",
    },
    "rag": {
        "mode": "semantic",
    },
}

def load_config() -> dict:
    """
    Load settings from config.yaml:
    1. Checks current working directory (e.g. current project/config.yaml)
    2. Checks user global config (~/.devmate/config.yaml)
    3. Checks repository directory
    4. Falls back to built-in defaults
    """
    candidates = [
        Path.cwd() / "config.yaml",
        Path(__file__).parent / "config.yaml",
        Path.home() / ".devmate" / "config.yaml",
        Path(__file__).resolve().parent.parent / "config.yaml",
    ]

    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT_CONFIG.items()}
    for p in candidates:
        if p.exists():
            try:
                loaded = yaml.safe_load(p.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    for k, v in loaded.items():
                        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                            cfg[k].update(v)
                        else:
                            cfg[k] = v
                    break
            except Exception:
                pass

    return cfg

# Load .env: local project first, then repository root, then global ~/.devmate/.env
load_dotenv(Path.cwd() / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path.home() / ".devmate" / ".env")

config = load_config()

def get_project_collection_name(repo_path: str = None) -> str:
    """
    Return a project-scoped collection name for vector stores (e.g. Qdrant / Chroma).
    If the project has an explicit custom collection_name configured in its local config.yaml, use it.
    Otherwise, scope it using the folder name (e.g. codebase_claude_code, codebase_my_app)
    so different projects don't collide in shared vector databases.
    """
    import re
    provider = config.get("vector_store", {}).get("provider", "qdrant")
    store_cfg = config.get("qdrant" if provider == "qdrant" else "chromadb", {})
    configured = store_cfg.get("collection_name", "codebase")

    target = Path(repo_path or Path.cwd()).resolve()
    folder_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", target.name.lower()).strip("_")

    if configured == "codebase" and folder_slug:
        return f"codebase_{folder_slug}"
    return configured or (f"codebase_{folder_slug}" if folder_slug else "codebase")

def get_chroma_persist_dir(repo_path: str = None) -> str:
    """Return absolute path for Chroma persist_dir scoped to the target repo."""
    configured = config.get("chromadb", {}).get("persist_dir", ".devmate/chromadb/")
    p = Path(configured)
    if not p.is_absolute():
        p = Path(repo_path or Path.cwd()).resolve() / p
    return str(p)

__all__ = ["config", "load_config", "get_project_collection_name", "get_chroma_persist_dir"]
