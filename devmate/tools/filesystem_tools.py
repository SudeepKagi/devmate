import os
from pathlib import Path
from langchain_core.tools import tool


@tool
def read_file(path: str) -> str:
    """Read and return the text contents of a file at the given path."""
    p = Path(path)
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
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to '{path}'."
    except Exception as e:
        return f"Error writing to file '{path}': {str(e)}"


@tool
def append_file(path: str, content: str) -> str:
    """Append content to a file at the given path."""
    p = Path(path)
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
    p = Path(path)
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
    p = Path(path)
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
    return Path(path).exists()
