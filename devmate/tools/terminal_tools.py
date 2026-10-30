import subprocess
from pathlib import Path
from langchain_core.tools import tool

from devmate.safety.sandbox import is_sandbox_enabled, execute_sandboxed_command

_BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf ~",
    "rmdir /s /q c:\\",
    ":(){ :|:& };:",
    "mkfs",
    "dd if=",
    "format c:",
]


def _is_safe(command: str) -> bool:
    cmd_lower = command.lower().strip()
    return not any(blocked in cmd_lower for blocked in _BLOCKED_COMMANDS)


@tool
def run_command(command: str) -> str:
    """Execute a shell command safely in the current working directory.
    Returns stdout and stderr from the command. Destructive system-level commands are blocked."""
    if not _is_safe(command):
        return f"Error: Command blocked for security reasons: {command}"

    if is_sandbox_enabled():
        code, stdout, stderr, meta = execute_sandboxed_command(command)
        output = stdout
        if stderr:
            output += f"\nSTDERR:\n{stderr}"
        if code != 0:
            output += f"\n(Command exited with code {code})"
        return output.strip() or "(Command completed with no output)"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n(Command exited with code {result.returncode})"
        return output.strip() or "(Command completed with no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"


@tool
def run_in_directory(command: str, directory: str) -> str:
    """Execute a shell command in a specific directory.
    Returns stdout and stderr from the command."""
    target_dir = Path(directory)
    if not target_dir.exists() or not target_dir.is_dir():
        return f"Error: Directory '{directory}' does not exist or is not a directory."

    if not _is_safe(command):
        return f"Error: Command blocked for security reasons: {command}"

    if is_sandbox_enabled():
        code, stdout, stderr, meta = execute_sandboxed_command(command)
        output = stdout
        if stderr:
            output += f"\nSTDERR:\n{stderr}"
        if code != 0:
            output += f"\n(Command exited with code {code})"
        return output.strip() or "(Command completed with no output)"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(target_dir.resolve()),
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n(Command exited with code {result.returncode})"
        return output.strip() or "(Command completed with no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error executing command in directory: {str(e)}"
