import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from rich.markdown import Markdown
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

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
from devmate.agent.factory import build_agent
from devmate.memory.short_term import get_checkpointer_db_path
from devmate.agent.orchestrator import handle_query
from devmate.memory.session import get_current_session, new_session, switch_session
from devmate.observability.logger import get_logger

console = Console()
logger = get_logger(__name__)


def get_or_create_index():
    repo_path = str(Path.cwd())
    logger.info(f"Checking index for: {repo_path}")
    console.print(f"[dim]Checking index for {repo_path}...[/dim]")
    return get_indexer()(repo_path)


async def initialize(checkpointer):
    """Bootstrap LLM, embedder, index, MCP tools, and session before the REPL starts."""
    llm = get_llm()
    embedder = get_embedder()
    console.print(f"[dim]LLM: {config['llm']['provider']} / {config['llm']['model']}[/dim]")
    console.print(f"[dim]Embedder: {config['embeddings']['provider']} / {config['embeddings']['model']}[/dim]")

    index = get_or_create_index()
    agent = await build_agent(checkpointer)
    session_id = get_current_session()
    console.print(f"[dim]Session: {session_id}[/dim]")
    console.print("[green]Ready[/green]\n")
    return llm, embedder, index, agent, session_id


async def _run_async():
    logger.info("Starting Devmate")
    console.print("\n[bold blue]Devmate[/bold blue] - RAG-powered code assistant")

    db_path = get_checkpointer_db_path()
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        llm, embedder, index, agent, session_id = await initialize(checkpointer)
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

            cmd_lower = cleaned.lower()
            if cmd_lower in ("/exit", "/quit", "exit", "quit"):
                logger.info("Shutting down")
                console.print("[dim]Goodbye![/dim]")
                break
            elif cleaned.startswith("/ask "):
                question = cleaned.removeprefix("/ask ").strip()
                if not question:
                    console.print("[yellow]Please provide a question: /ask <your question>[/yellow]")
                    continue
                logger.info(f"Ask command received: {question}")
                console.print(f"[dim]Searching for: {question}...[/dim]")
                with console.status("[bold cyan]Devmate is reasoning and answering...[/bold cyan]", spinner="dots"):
                    response = await handle_query(agent, question, session_id)
                console.print()
                console.print(Markdown(response))
                console.print()
            elif cmd_lower == "/new_session":
                session_id = new_session()
                console.print(f"[green]New session started: {session_id}[/green]")
            elif cleaned.startswith("/switch "):
                target = cleaned.removeprefix("/switch ").strip()
                if target:
                    session_id = switch_session(target)
                    console.print(f"[green]Switched to session: {session_id}[/green]")
                else:
                    console.print("[yellow]Usage: /switch <session_id>[/yellow]")
            elif cmd_lower == "/session":
                console.print(f"[dim]Current session: {session_id}[/dim]")
            elif cmd_lower in ("/show_index", "/show_semantic_index"):
                logger.info("Showing index")
                get_index_inspector()(index)
            elif cmd_lower in ("/reindex", "reindex"):
                logger.info("Reindexing repository")
                repo_path = str(Path.cwd())
                console.print(f"[dim]Reindexing {repo_path}...[/dim]")
                with console.status("[bold cyan]Reindexing codebase into vector store...[/bold cyan]", spinner="dots"):
                    index = get_reindexer()(repo_path)
                console.print("[bold green]Reindexing complete![/bold green]\n")
            elif cmd_lower in ("/help", "help"):
                console.print("\n[bold]Available Commands:[/bold]")
                console.print("  [bold cyan]/ask <question>[/bold cyan]           - Ask a question about the codebase")
                console.print("  [bold cyan]/show_index[/bold cyan]                - Show all chunks in the index")
                console.print("  [bold cyan]/new_session[/bold cyan]               - Start a fresh conversation")
                console.print("  [bold cyan]/switch <session_id>[/bold cyan]       - Resume a past session")
                console.print("  [bold cyan]/session[/bold cyan]                   - Show current session ID")
                console.print("  [bold cyan]/reindex[/bold cyan]                   - Re-index all files into vector store")
                console.print("  [bold cyan]/exit[/bold cyan]                      - Quit Devmate\n")
            elif not cleaned.startswith("/"):
                # Non-command input treated as question
                logger.info(f"Direct question received: {cleaned}")
                console.print(f"[dim]Searching for: {cleaned}...[/dim]")
                with console.status("[bold cyan]Devmate is reasoning and answering...[/bold cyan]", spinner="dots"):
                    response = await handle_query(agent, cleaned, session_id)
                console.print()
                console.print(Markdown(response))
                console.print()
            else:
                logger.warning(f"Unknown command received: {cleaned}")
                console.print("[yellow]Unknown command. Try:[/yellow]")
                console.print("  [bold]/ask <question>[/bold]           — ask a question about the codebase")
                console.print("  [bold]/show_index[/bold]               — show all chunks in the index")
                console.print("  [bold]/new_session[/bold]              — start a fresh conversation")
                console.print("  [bold]/switch <session_id>[/bold]      — resume a past session")
                console.print("  [bold]/session[/bold]                  — show current session id")
                console.print("  [bold]/exit[/bold]                     — quit")


def run():
    asyncio.run(_run_async())


if __name__ == "__main__":
    run()
