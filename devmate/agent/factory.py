from langchain.agents import create_agent

from devmate.llm.factory import get_llm
from devmate.agent.tools import search_codebase
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are Devmate, a helpful senior AI software engineer assistant.
Answer the user's question accurately using the codebase context.
Use the `search_codebase` tool to find relevant files, classes, and functions.
Be focused and decisive: retrieve the necessary code context (usually 1-2 searches are sufficient), then provide a well-structured, direct answer referencing file names and line numbers.
If the answer is not present in the codebase, state so clearly."""

def build_agent():
    """Create and return a LangChain agent."""
    llm = get_llm()
    tools = [search_codebase]
    logger.info("Creating agent")
    return create_agent(
        llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )
