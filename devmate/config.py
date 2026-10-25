import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

# Built-in fallback defaults
DEFAULT_CONFIG = {
    "llm": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "max_tokens": 1000,
    },
    "embeddings": {
        "provider": "openai",
        "model": "text-embedding-3-small",
    },
    "chromadb": {
        "persist_dir": ".chromadb/",
        "collection_name": "codebase",
    },
    "elasticsearch": {
        "url": "http://localhost:9200",
        "index_name": "codebase",
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

# Load .env: local project first, then global ~/.devmate/.env
load_dotenv(Path.cwd() / ".env")
load_dotenv(Path.home() / ".devmate" / ".env")

config = load_config()

__all__ = ["config", "load_config"]
