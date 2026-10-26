import json
import os
from pathlib import Path
import re
from dotenv import load_dotenv

load_dotenv()

_CONFIG_PATH = Path(__file__).parent.parent / "devmate_mcp_servers.json"


def load_devmate_mcp_configs() -> dict:
    """Return mcp_servers dict from devmate_mcp_servers.json with env vars resolved.
    CWD is injected at load time so ${CWD} in the config always resolves to the
    directory where devmate was launched.
    """
    os.environ.setdefault("CWD", str(Path.cwd().as_posix()))

    config_path = _CONFIG_PATH
    if not config_path.exists():
        repo_root_path = Path(__file__).parent.parent.parent / "devmate_mcp_servers.json"
        if repo_root_path.exists():
            config_path = repo_root_path
        else:
            fallback_path = Path.cwd() / "devmate_mcp_servers.json"
            if fallback_path.exists():
                config_path = fallback_path
            else:
                return {}

    raw = json.loads(config_path.read_text(encoding="utf-8"))

    def _replace_env(match):
        var_name = match.group(1)
        val = os.getenv(var_name, "")
        # Normalize Windows backslashes so JSON parsing does not fail on \P, \U, etc.
        return val.replace("\\", "\\\\")

    # Replace ${VAR} placeholders in the config with actual env var values
    resolved = re.sub(
        r"\$\{(\w+)\}",
        _replace_env,
        json.dumps(raw),
    )

    data = json.loads(resolved)
    return data.get("mcp_servers", {})
