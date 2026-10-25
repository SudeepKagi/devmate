from pathlib import Path
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain.agents.middleware import SummarizationMiddleware
from devmate.config import config
from devmate.llm.factory import get_llm
from devmate.observability.logger import get_logger

logger = get_logger(__name__)


def get_checkpointer_db_path() -> str:
    db_path = config.get("memory", {}).get("db_path", ".memory/memory.db")
    p = Path(db_path)
    if not p.is_absolute():
        p = Path.cwd() / p
    p.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using SQLite checkpointer at {p}")
    return str(p)


def get_checkpointer() -> AsyncSqliteSaver:
    db_path = get_checkpointer_db_path()
    return AsyncSqliteSaver.from_conn_string(db_path)


def get_summarization_middleware() -> SummarizationMiddleware:
    memory_cfg = config.get("memory", {})
    return SummarizationMiddleware(
        model=get_llm(),
        trigger=("tokens", memory_cfg.get("summarize_at_tokens", 4000)),
        keep=("messages", memory_cfg.get("keep_last_messages", 20)),
    )
