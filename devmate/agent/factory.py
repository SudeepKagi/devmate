from langchain.agents import create_agent

from devmate.llm.factory import get_llm
from devmate.agent.tools import search_codebase
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a senior software engineer with deep knowledge of the codebase.
You have access to the search_codebase tool to find relevant code snippets.
Guidelines:
1. Use search_codebase with a targeted search query to locate relevant code.
2. The search results provide the file paths, line numbers, and code content. Do not repeatedly search for the same file.
3. Once the relevant code is retrieved, formulate and return your final answer directly.
4. Reference specific file names, function names and line numbers in your answer.
5. If you cannot find the answer in the codebase, say so explicitly."""

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
