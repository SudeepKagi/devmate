import uuid
from pathlib import Path
from devmate.config import config
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

def _session_file() -> Path:
    db_path = config.get("memory", {}).get("db_path", ".memory/memory.db")
    p = Path(db_path)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.parent / "current_session"

def get_current_session() -> str:
    session_file = _session_file()
    if session_file.exists():
        session_id = session_file.read_text(encoding="utf-8").strip()
        if session_id:
            logger.info(f"Resuming session: {session_id}")
            return session_id
    return new_session()

def new_session() -> str:
    session_id = str(uuid.uuid4())
    session_file = _session_file()
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(session_id, encoding="utf-8")
    logger.info(f"Started new session: {session_id}")
    return session_id

def switch_session(session_id: str) -> str:
    session_file = _session_file()
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(session_id, encoding="utf-8")
    logger.info(f"Switched to session: {session_id}")
    return session_id
