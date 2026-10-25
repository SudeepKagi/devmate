from pathlib import Path
from dataclasses import dataclass

try:
    from tree_sitter import Language, Parser
except ImportError:
    Language, Parser = None, None

from devmate.observability.logger import get_logger

logger = get_logger(__name__)

def get_parser(language_name: str):
    """Dynamically get tree-sitter parser, supporting tree_sitter_languages or individual packages."""
    if Parser is None:
        return None

    # Try tree_sitter_languages first if present
    try:
        from tree_sitter_languages import get_parser as tsl_get_parser
        return tsl_get_parser(language_name)
    except Exception:
        pass

    # Direct individual language packages
    try:
        if language_name == "python":
            import tree_sitter_python as tspython
            return Parser(Language(tspython.language()))
        elif language_name == "javascript":
            import tree_sitter_javascript as tsjs
            return Parser(Language(tsjs.language()))
        elif language_name == "typescript":
            import tree_sitter_typescript as tsts
            return Parser(Language(tsts.language_typescript()))
        elif language_name == "tsx":
            import tree_sitter_typescript as tsts
            return Parser(Language(tsts.language_tsx()))
    except Exception as e:
        logger.debug(f"Parser for {language_name} unavailable: {e}")

    return None

# Maps file extension -> tree-sitter language name.
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".cs": "c_sharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".sh": "bash",
}

# Text/config/markup files chunked by line count instead of AST.
TEXT_EXTENSIONS = {".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".css", ".scss", ".html"}
ALL_EXTENSIONS = set(EXTENSION_TO_LANGUAGE.keys()) | TEXT_EXTENSIONS

# Sliding window settings for text files and AST fallback.
CHUNK_SIZE = 50
CHUNK_OVERLAP = 10

# Tree-sitter node type names that correspond to a named, indexable block.
BLOCK_NODE_TYPES = {
    "function_definition",
    "function_declaration",
    "method_definition",
    "arrow_function",
    "class_definition",
    "class_declaration",
    "method_declaration",
    "constructor_declaration",
    "interface_declaration",
    "function_item",  # Rust
}

@dataclass
class ParsedChunk:
    name: str
    type: str          # "function" | "class" | "block"
    content: str
    source: str        # absolute path to the file
    start_line: int
    end_line: int

def parse_file(filepath: str) -> list[ParsedChunk]:
    """Entry point - routes to AST parsing or falls back safely to sliding window."""
    ext = Path(filepath).suffix.lower()

    if ext in TEXT_EXTENSIONS:
        lines = Path(filepath).read_text(encoding="utf-8", errors="ignore").splitlines()
        return _sliding_window(lines, filepath)

    language_name = EXTENSION_TO_LANGUAGE.get(ext)
    if language_name:
        try:
            parser = get_parser(language_name)
            if parser is not None:
                source = Path(filepath).read_text(encoding="utf-8", errors="ignore")
                chunks = _parse_with_treesitter(source, filepath, language_name, parser)
                if chunks:
                    return chunks
            else:
                logger.debug(f"No Tree-sitter parser installed for '{language_name}', falling back to sliding window")
        except Exception as e:
            logger.warning(f"AST parsing failed for {filepath} ({e}), falling back to sliding window")

    # Safe fallback: chunk file lines so no code is skipped
    lines = Path(filepath).read_text(encoding="utf-8", errors="ignore").splitlines()
    return _sliding_window(lines, filepath)

def _parse_with_treesitter(source: str, filepath: str, language_name: str, parser) -> list[ParsedChunk]:
    """Parse source with the appropriate tree-sitter grammar and extract named blocks."""
    logger.info(f"Parsing {language_name} file: {filepath}")
    tree = parser.parse(source.encode())
    lines = source.splitlines()

    chunks = []
    _walk(tree.root_node, source, filepath, chunks, depth=0)

    # If the AST yielded nothing (e.g. a file with only imports/variables), fall back to line chunks
    if not chunks:
        logger.debug(f"No AST blocks found in {filepath}, falling back to sliding window")
        return _sliding_window(lines, filepath)

    logger.info(f"Parsed {len(chunks)} chunks from {filepath}")
    return chunks

def _walk(node, source: str, filepath: str, chunks: list, depth: int):
    """
    Recursively walk the AST. When a named block node is found, record it and stop
    descending - this keeps chunks at the top level and avoids duplicating nested functions.
    """
    if node.type in BLOCK_NODE_TYPES:
        target = node
        # For arrow functions assigned to variables (e.g. const Hero = () => {}), include parent declaration
        if node.type == "arrow_function" and node.parent and node.parent.type == "variable_declarator":
            if node.parent.parent and node.parent.parent.type in ("lexical_declaration", "variable_declaration"):
                target = node.parent.parent

        name = _extract_name(node, source)
        content = source[target.start_byte:target.end_byte]
        chunk_type = "class" if "class" in node.type else "function"
        chunks.append(ParsedChunk(
            name=name,
            type=chunk_type,
            content=content,
            source=filepath,
            start_line=target.start_point[0] + 1,
            end_line=target.end_point[0] + 1,
        ))
        logger.debug(f"  Found {chunk_type} '{name}' (lines {target.start_point[0]+1}-{target.end_point[0]+1})")
        return  # stop here - don't index nested functions/classes as separate chunks

    for child in node.children:
        _walk(child, source, filepath, chunks, depth + 1)

def _extract_name(node, source: str) -> str:
    """Find the identifier child of a block node and return its text as the chunk name."""
    for child in node.children:
        if child.type in ("identifier", "name", "property_identifier"):
            return source[child.start_byte:child.end_byte]
    # Check parent if it's a variable declarator (e.g. const Hero = () => ...)
    if node.parent and node.parent.type == "variable_declarator":
        for child in node.parent.children:
            if child.type in ("identifier", "name"):
                return source[child.start_byte:child.end_byte]
    return node.type  # fallback to node type if no name found

def _sliding_window(lines: list[str], filepath: str) -> list[ParsedChunk]:
    """
    Split lines into overlapping fixed-size chunks.
    Used for text/markup files and as a fallback when AST parsing is unavailable or finds nothing.
    """
    if not lines:
        return []

    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    for i, start in enumerate(range(0, len(lines), step)):
        end = min(start + CHUNK_SIZE, len(lines))
        text = "\n".join(lines[start:end]).strip()
        if text:
            chunks.append(ParsedChunk(
                name=f"chunk_{i}",
                type="block",
                content=text,
                source=filepath,
                start_line=start + 1,
                end_line=end,
            ))
        if end == len(lines):
            break

    logger.info(f"Parsed {len(chunks)} chunks from {filepath}")
    return chunks

SKIP_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock"}

def get_source_files(repo_path: str, skip_dirs: list[str] = None) -> list[str]:
    """Recursively find all indexable source files under repo_path, skipping build/env dirs."""
    skip = set(skip_dirs or [".venv", "venv", "__pycache__", ".git", "node_modules", "dist", "build"])
    files = [
        str(path) for path in Path(repo_path).rglob("*")
        if path.is_file()
        and path.suffix.lower() in ALL_EXTENSIONS
        and path.name not in SKIP_FILES
        and not any(part in skip for part in path.parts)
    ]
    logger.info(f"Found {len(files)} source files in {repo_path}")
    return files
