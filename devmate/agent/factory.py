from langchain.agents import create_agent

from devmate.llm.factory import get_llm
from devmate.agent.tools import search_codebase
from devmate.observability.logger import get_logger
from devmate.tools.terminal_tools import run_command, run_in_directory
from devmate.tools.filesystem_tools import (
    read_file,
    write_file,
    append_file,
    delete_file,
    list_directory,
    file_exists,
)
from devmate.mcp.devmate_mcp_client import get_devmate_mcp_tools

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a senior software engineer with deep knowledge of the codebase.
You have access to tools including search_codebase, terminal tools, filesystem tools, and GitHub MCP tools.
Guidelines:
1. Always use the search_codebase tool before answering questions about the codebase.
2. Use specific file names, function names, and line numbers in your answers.
3. Formulate your final answer directly once relevant code or tool output is obtained.
4. If you cannot find the answer in the codebase, say so explicitly."""


async def build_agent(checkpointer=None, mcp_tools=None):
    """Create and return a LangChain agent with persistent memory and tools."""
    llm = get_llm()
    if mcp_tools is None:
        mcp_tools = await get_devmate_mcp_tools()

    tools = [
        search_codebase,
        run_command,
        run_in_directory,
        read_file,
        write_file,
        append_file,
        delete_file,
        list_directory,
        file_exists,
        *mcp_tools,
    ]
    logger.info(f"Creating agent with {len(tools)} tools")

    return create_agent(
        llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )
