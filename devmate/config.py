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
    "prompt_caching": {
        "enabled": False,
    },
    "router": {
        "enabled": False,
        "fast_model": "gpt-4o-mini",
        "strong_model": "gpt-4o",
    },
    "retrieval": {
        "mode": "dense",  # "dense" | "hybrid"
    },
    "chunking": {
        "mode": "ast",  # "file" | "ast"
    },
    "sandbox": {
        "enabled": False,
        "timeout_seconds": 30,
        "network": False,
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
    "pricing": {
        "source_url": "https://openai.com/api/pricing/ and https://ai.google.dev/pricing and https://www.anthropic.com/pricing",
        "effective_date": "2024-10-01",
        "models": {
            "gpt-4o-mini": {
                "input_per_million": 0.15,
                "cached_input_per_million": 0.075,
                "output_per_million": 0.60,
            },
            "gpt-4o": {
                "input_per_million": 2.50,
                "cached_input_per_million": 1.25,
                "output_per_million": 10.00,
            },
            "claude-3-5-sonnet": {
                "input_per_million": 3.00,
                "cached_input_per_million": 0.30,
                "output_per_million": 15.00,
            },
            "claude-3-5-haiku": {
                "input_per_million": 0.80,
                "cached_input_per_million": 0.08,
                "output_per_million": 4.00,
            },
            "gemini-1.5-flash": {
                "input_per_million": 0.075,
                "cached_input_per_million": 0.01875,
                "output_per_million": 0.30,
            },
            "gemini-1.5-pro": {
                "input_per_million": 1.25,
                "cached_input_per_million": 0.3125,
                "output_per_million": 5.00,
            },
            "text-embedding-3-small": {
                "input_per_million": 0.02,
                "cached_input_per_million": 0.02,
                "output_per_million": 0.0,
            },
        },
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

def get_project_collection_name(repo_path: str = None, store: str = None) -> str:
    """
    Return a project-scoped collection name for vector stores (e.g. Qdrant / Chroma).
    If the project has an explicit custom collection_name configured in its local config.yaml, use it.
    Otherwise, scope it using the folder name (e.g. codebase_claude_code, codebase_my_app)
    so different projects don't collide in shared vector databases.
    """
    import re
    if store:
        store_cfg = config.get(store, {})
    else:
        provider = config.get("vector_store", {}).get("provider", "chroma")
        store_cfg = config.get("chromadb" if provider == "chroma" else "qdrant", {})
    configured = store_cfg.get("collection_name", "codebase")

    target = Path(repo_path or Path.cwd()).resolve()
    folder_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", target.name.lower()).strip("_")

    if configured in ("codebase", "devmate") and folder_slug:
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
