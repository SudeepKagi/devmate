import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from rich.markdown import Markdown
import chromadb

# Ensure Windows terminal handles UTF-8 characters cleanly
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from devmate.config import config
from devmate.context.indexers.semantic_chroma import index_codebase, reindex_codebase
from devmate.llm.factory import get_llm, get_embedder
from devmate.observability.logger import get_logger
from devmate.agent.orchestrator import handle_query

# Load .env before anything else
load_dotenv()
console = Console()
logger = get_logger(__name__)

def get_or_create_index() -> chromadb.Collection:
    """Load existing index or create a new one by indexing current directory."""
    chroma_client = chromadb.PersistentClient(path=config["chromadb"]["persist_dir"])
    collection = chroma_client.get_or_create_collection(name=config["chromadb"]["collection_name"])

    if collection.count() > 0:
        logger.info(f"Loaded existing index with {collection.count()} chunks")
        console.print(f"[dim]Loaded existing index - {collection.count()} chunks[/dim]")
        return collection

    # Auto-index the current working directory
    repo_path = str(Path.cwd())
    logger.info(f"Indexing repo: {repo_path}")
    console.print(f"[dim]Indexing {repo_path}...[/dim]")
    return index_codebase(repo_path)

def show_semantic_index(collection: chromadb.Collection) -> None:
    """Display all documents stored in the ChromaDB collection."""
    results = collection.get(include=["documents", "metadatas", "embeddings"])
    total = collection.count()
    console.print(f"\n[bold]Semantic Index - {total} chunks[/bold]\n")

    if total == 0:
        console.print("[yellow]Index is empty. Use '/reindex' to index the codebase.[/yellow]\n")
        return

    # Show first 10 chunks to avoid flooding terminal
    display_count = min(10, total)
    for i in range(display_count):
        doc = results["documents"][i]
        meta = results["metadatas"][i]
        emb = results["embeddings"][i] if results.get("embeddings") else []

        console.print(f"[bold cyan]-- Chunk {i+1} of {total} --------------------------------------[/bold cyan]")
        console.print(f"  File     : {meta['source']}")
        console.print(f"  Name     : {meta['name']} ({meta['type']})")
        console.print(f"  Lines    : {meta['start_line']} - {meta['end_line']}")
        if emb:
            console.print(f"  Embedding: [{', '.join(f'{v:.4f}' for v in emb[:5])}...] ({len(emb)} dims)")
        console.print(f"  Code     :\n[dim]{doc[:300]}[/dim]\n")

    if total > display_count:
        console.print(f"[dim]... and {total - display_count} more chunk(s).[/dim]\n")

def initialize():
    """Bootstrap LLM, embedder, and index before the REPL starts."""
    llm = get_llm()
    embedder = get_embedder()
    console.print(f"[dim]LLM: {config['llm']['provider']} / {config['llm']['model']}[/dim]")
    console.print(f"[dim]Embedder: {config['embeddings']['provider']} / {config['embeddings']['model']}[/dim]")

    collection = get_or_create_index()
    console.print(f"[green]Ready - {collection.count()} chunks indexed[/green]\n")
    return llm, embedder, collection

def run():
    logger.info("Starting Devmate")
    console.print("\n[bold blue]Devmate[/bold blue] - RAG-powered code assistant")
    llm, embedder, collection = initialize()
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
            with console.status("[bold cyan]Reindexing codebase...[/bold cyan]", spinner="dots"):
                collection = reindex_codebase(repo_path)
            console.print(f"[bold green]Reindexing complete! {collection.count()} chunks indexed.[/bold green]\n")
        elif cmd in ("/show_semantic_index", "show_semantic_index"):
            logger.info("Showing semantic index")
            show_semantic_index(collection)
        elif cmd in ("/help", "help"):
            console.print("\n[bold]Available Commands:[/bold]")
            console.print("  [bold cyan]/ask <question>[/bold cyan]           - Ask questions about the codebase")
            console.print("  [bold cyan]/reindex[/bold cyan]                   - Re-index all files in the current repository")
            console.print("  [bold cyan]/show_semantic_index[/bold cyan]       - View indexed chunks in ChromaDB")
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
