from langchain.agents import create_agent

from devmate.llm.factory import get_llm
from devmate.agent.tools import search_codebase
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are Devmate, a fast, helpful senior AI software engineer assistant.
Answer the user's question accurately using the codebase context.
1. Perform at most ONE search with the `search_codebase` tool to find relevant code chunks.
2. Immediately use the retrieved code chunks to provide a concise, direct answer referencing file names and line numbers.
3. Do NOT make repeated searches once results are returned. If the answer is not in the codebase, state so clearly."""

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
