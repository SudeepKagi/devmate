import os
from langchain.agents import create_agent

from devmate.llm.factory import get_llm
from devmate.agent.tools import search_codebase
from devmate.observability.logger import get_logger
from devmate.tools.terminal_tools import run_command, run_in_directory
from devmate.tools.filesystem_tools import (
    read_file,
    list_directory,
    file_exists,
)
from devmate.skills.skill_tools import load_skill, build_skills_prompt
from devmate.mcp.devmate_mcp_client import get_devmate_mcp_tools
from devmate.safety.hitl import build_hitl_middleware
from devmate.safety.guardrails import build_guardrails, env_bool

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a senior software engineer with deep knowledge of the codebase.
Always use the search_codebase tool before answering questions about the codebase.
Reference specific file names, function names, and line numbers in your answers.
Directly formulate and return your final answer once you have retrieved the relevant code chunks.
If you cannot find the answer in the codebase, say so explicitly."""


async def build_agent(
    checkpointer=None,
    mcp_tools=None,
    enable_safety: bool = False,
    include_mcp_tools: bool = True,
):
    """Create and return a LangChain agent with persistent memory and tools."""
    llm = get_llm()
    if not include_mcp_tools:
        mcp_tools = []
    elif mcp_tools is None:
        mcp_tools = await get_devmate_mcp_tools()

    # Build dynamic skills prompt
    skills_prompt = build_skills_prompt()
    full_prompt = SYSTEM_PROMPT
    if skills_prompt:
        full_prompt = SYSTEM_PROMPT + "\n\n" + skills_prompt

    tools = [
        search_codebase,
        load_skill,
        run_command,
        run_in_directory,
        read_file,
        list_directory,
        file_exists,
        *mcp_tools,
    ]
    logger.info(f"Creating agent with {len(tools)} tools")

    middleware = []
    if enable_safety:
        show_redacted = env_bool("GUARDRAIL_SHOW_REDACTED_INPUT", default=False)
        middleware.extend(build_guardrails(safety_model=llm, show_redacted_input=show_redacted))
        middleware.append(build_hitl_middleware())

    agent_kwargs = {}
    if middleware:
        agent_kwargs["middleware"] = middleware

    return create_agent(
        llm,
        tools=tools,
        system_prompt=full_prompt,
        checkpointer=checkpointer,
        **agent_kwargs,
    )
