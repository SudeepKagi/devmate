from langchain.tools import tool
from rich.console import Console

from devmate.context.retrievers.factory import get_retriever
from devmate.observability.logger import get_logger

logger = get_logger(__name__)
console = Console()

_call_count = 0

def reset_search_history():
    global _call_count
    _call_count = 0

@tool
def search_codebase(query: str = "", path: str = None, **kwargs) -> str:
    """
    Search the codebase for relevant classes, functions or logic.
    Use this tool whenever you need to find code related to a question.
    """
    global _call_count
    _call_count += 1
    if _call_count > 2:
        return (
            "Search limit reached for this query. Do NOT call any more tools. "
            "Provide your final answer to the user now based on the code chunks already retrieved."
        )

    search_term = (query or path or " ".join(str(v) for v in kwargs.values() if v)).strip()
    if not search_term:
        return "No relevant code found."

    console.print(f"[dim] Searching codebase for:[/dim] [bold cyan]\"{search_term}\"[/bold cyan]")
    logger.info(f"Tool called: search_codebase with query: {search_term}")
    retrieve = get_retriever()
    chunks = retrieve(search_term, k=5)

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
