import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from rich.markdown import Markdown

# Ensure Windows terminal handles UTF-8 characters cleanly
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Load .env from multiple standard locations
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path.home() / ".devmate" / ".env")
load_dotenv()

from devmate.config import config
from devmate.context.indexers.factory import get_indexer, get_index_inspector, get_reindexer
from devmate.llm.factory import get_llm, get_embedder
from devmate.agent.orchestrator import handle_query
from devmate.observability.logger import get_logger

console = Console()
logger = get_logger(__name__)

def get_or_create_index():
    repo_path = str(Path.cwd())
    logger.info(f"Checking index for: {repo_path}")
    console.print(f"[dim]Checking index for {repo_path}...[/dim]")
    return get_indexer()(repo_path)

def initialize():
    """Bootstrap LLM, embedder, and index before the REPL starts."""
    llm = get_llm()
    embedder = get_embedder()
    console.print(f"[dim]LLM: {config['llm']['provider']} / {config['llm']['model']}[/dim]")
    console.print(f"[dim]Embedder: {config['embeddings']['provider']} / {config['embeddings']['model']}[/dim]")

    index = get_or_create_index()
    console.print(f"[green]Ready[/green]\n")
    return llm, embedder, index

def run():
    logger.info("Starting Devmate")
    console.print("\n[bold blue]Devmate[/bold blue] - RAG-powered code assistant")
    llm, embedder, index = initialize()
    console.print("Type [bold]'/exit'[/bold] to quit, or [bold]'/help'[/bold] for commands\n")

    while True:
        try:
            user_input = Prompt.ask("[bold green]>[/bold green]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        cleaned = user_input.strip()
        if not cleaned:
            continue

        cmd = cleaned.lower()
        if cmd in ("/exit", "/quit", "exit", "quit"):
            logger.info("Shutting down")
            console.print("[dim]Goodbye![/dim]")
            break
        elif cleaned.startswith("/ask ") or cleaned.startswith("ask "):
            question = cleaned.split(" ", 1)[1].strip()
            if not question:
                console.print("[yellow]Please provide a question: /ask <your question>[/yellow]")
                continue
            logger.info(f"Ask command received: {question}")
            console.print(f"[dim]Searching codebase for: {question}...[/dim]")
            try:
                with console.status("[bold cyan]Devmate is reasoning and answering...[/bold cyan]", spinner="dots"):
                    response = handle_query(question)
                console.print()
                console.print(Markdown(response))
                console.print()
            except Exception as e:
                console.print(f"[bold red]Error querying agent:[/bold red] {e}")
        elif cmd in ("/reindex", "reindex"):
            logger.info("Reindexing repository")
            repo_path = str(Path.cwd())
            console.print(f"[dim]Reindexing {repo_path}...[/dim]")
            with console.status("[bold cyan]Reindexing codebase into vector store...[/bold cyan]", spinner="dots"):
                index = get_reindexer()(repo_path)
            console.print(f"[bold green]Reindexing complete![/bold green]\n")
        elif cmd in ("/show_semantic_index", "show_semantic_index"):
            logger.info("Showing semantic index")
            get_index_inspector()(index)
        elif cmd in ("/help", "help"):
            console.print("\n[bold]Available Commands:[/bold]")
            console.print("  [bold cyan]/ask <question>[/bold cyan]           - Ask questions about the codebase")
            console.print("  [bold cyan]/reindex[/bold cyan]                   - Re-index all files into the vector store")
            console.print("  [bold cyan]/show_semantic_index[/bold cyan]       - View indexed chunks in vector store")
            console.print("  [bold cyan]/exit[/bold cyan]                      - Quit Devmate\n")
        else:
            logger.warning(f"Unknown command received: {cleaned}")
            console.print("[yellow]Unknown command. Try:[/yellow]")
            console.print("  [bold cyan]/ask <question>[/bold cyan]           - Ask questions about the codebase")
            console.print("  [bold cyan]/reindex[/bold cyan]                   - Re-index current repository")
            console.print("  [bold cyan]/show_semantic_index[/bold cyan]       - Show chunks in semantic index")
            console.print("  [bold cyan]/exit[/bold cyan]                      - Exit\n")

if __name__ == "__main__":
    run()
