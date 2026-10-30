import os
from pathlib import Path
from langchain_core.tools import tool

from devmate.safety.sandbox import is_sandbox_enabled, validate_workspace_path, SecurityError


def _safe_path(path: str) -> tuple[Path, str | None]:
    """Helper to check path against sandbox jail if enabled."""
    if is_sandbox_enabled():
        try:
            return validate_workspace_path(path), None
        except SecurityError as e:
            return Path(path), f"SecurityError: {e}"
    return Path(path), None


@tool
def read_file(path: str) -> str:
    """Read and return the text contents of a file at the given path."""
    p, err = _safe_path(path)
    if err:
        return err
    if not p.exists():
        return f"Error: File '{path}' does not exist."
    if not p.is_file():
        return f"Error: Path '{path}' is not a file."
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return p.read_text(encoding="latin-1")
        except Exception as e:
            return f"Error reading file with fallback encoding: {str(e)}"
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file at the given path, creating parent directories if needed."""
    p, err = _safe_path(path)
    if err:
        return err
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to '{path}'."
    except Exception as e:
        return f"Error writing to file '{path}': {str(e)}"


@tool
def append_file(path: str, content: str) -> str:
    """Append content to a file at the given path."""
    p, err = _safe_path(path)
    if err:
        return err
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully appended {len(content)} characters to '{path}'."
    except Exception as e:
        return f"Error appending to file '{path}': {str(e)}"


@tool
def delete_file(path: str) -> str:
    """Delete a file at the given path safely (will not delete directories)."""
    p, err = _safe_path(path)
    if err:
        return err
    if not p.exists():
        return f"Error: File '{path}' does not exist."
    if not p.is_file():
        return f"Error: Path '{path}' is not a file. For safety, this tool cannot delete directories."
    try:
        p.unlink()
        return f"Successfully deleted file '{path}'."
    except Exception as e:
        return f"Error deleting file '{path}': {str(e)}"


@tool
def list_directory(path: str = ".") -> str:
    """List contents of a directory, showing files, directories, and file sizes."""
    p, err = _safe_path(path)
    if err:
        return err
    if not p.exists():
        return f"Error: Directory '{path}' does not exist."
    if not p.is_dir():
        return f"Error: Path '{path}' is not a directory."
    try:
        entries = sorted(list(p.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = []
        for entry in entries:
            if entry.is_dir():
                lines.append(f"[DIR]  {entry.name}/")
            else:
                size_kb = entry.stat().st_size / 1024
                lines.append(f"[FILE] {entry.name} ({size_kb:.1f} KB)")
        return "\n".join(lines) if lines else "(Directory is empty)"
    except Exception as e:
        return f"Error listing directory '{path}': {str(e)}"


@tool
def file_exists(path: str) -> bool:
    """Check if a file or directory exists at the given path."""
    p, err = _safe_path(path)
    if err:
        return False
    return p.exists()


@tool
def update_file(path: str, old_text: str, new_text: str, replace_all: bool = False) -> str:
    """Update text in a file by replacing old_text with new_text."""
    p, err = _safe_path(path)
    if err:
        return err
    if not p.exists():
        return f"Error: File '{path}' does not exist."
    if not p.is_file():
        return f"Error: Path '{path}' is not a file."
    try:
        content = p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"

    if old_text not in content:
        return "Error: old_text was not found in file."

    if replace_all:
        count = content.count(old_text)
        updated = content.replace(old_text, new_text)
    else:
        count = 1
        updated = content.replace(old_text, new_text, 1)

    try:
        p.write_text(updated, encoding="utf-8")
        return f"Updated file '{path}' (replacements: {count})"
    except Exception as e:
        return f"Error writing updated file '{path}': {str(e)}"


