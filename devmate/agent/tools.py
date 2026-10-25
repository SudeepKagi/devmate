from langchain.tools import tool
from rich.console import Console

from devmate.context.retrievers.semantic_chroma import retrieve
from devmate.observability.logger import get_logger

logger = get_logger(__name__)
console = Console()

@tool
def search_codebase(query: str) -> str:
    """
    Search the codebase for relevant classes, functions or logic.
    Use this tool whenever you need to find code related to a question.
    """
    console.print(f"[dim] Searching codebase for:[/dim] [bold cyan]\"{query}\"[/bold cyan]")
    logger.info(f"Tool called: search_codebase with query: {query}")
    chunks = retrieve(query, k=4)

    if not chunks:
        console.print(f"[dim] No matches found for \"{query}\"[/dim]")
        return "No relevant code found."

    console.print(f"[dim] Found {len(chunks)} relevant code chunk(s)[/dim]")

    # Format chunks into a readable string for the LLM
    results = []
    for chunk in chunks:
        results.append(
            f"File: {chunk['source']} (lines {chunk['start_line']}-{chunk['end_line']})\n"
            f"Type: {chunk['type']} - {chunk['name']}\n"
            f"Code:\n{chunk['content']}\n"
        )
    return "\n---\n".join(results)
