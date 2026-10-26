import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_CONFIG_PATH = Path(__file__).parent.parent / "educosys_mcp_servers.json"


def load_educosys_mcp_configs() -> dict:
    """Return mcp_servers dict from educosys_mcp_servers.json with env vars resolved.

    CWD is injected at load time so ${CWD} in the config always resolves to the
    directory where educosys claude was launched — not the package install location.
    """
    os.environ.setdefault("CWD", str(Path.cwd().as_posix()))
    raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))

    def _replace_env(match):
        var_name = match.group(1)
        val = os.getenv(var_name, "")
        return val.replace("\\", "\\\\")

    resolved = re.sub(r"\$\{(\w+)\}", _replace_env, json.dumps(raw))
    return json.loads(resolved).get("mcp_servers", {})
