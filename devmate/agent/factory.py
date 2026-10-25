import os
from langchain.agents import create_agent

from devmate.llm.factory import get_llm
from devmate.agent.tools import search_codebase
from devmate.observability.logger import get_logger
from devmate.tools.terminal_tools import run_command, run_in_directory
from devmate.tools.filesystem_tools import (
    read_file,
    write_file,
    append_file,
    update_file,
    delete_file,
    list_directory,
    file_exists,
)
from devmate.tools.human_tools import ask_user
from devmate.skills.skill_tools import load_skill, build_skills_prompt
from devmate.mcp.devmate_mcp_client import get_devmate_mcp_tools
from devmate.safety.hitl import build_hitl_middleware
from devmate.safety.guardrails import build_guardrails, env_bool

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a senior software engineer with deep knowledge of the codebase.
You have access to tools including search_codebase, terminal tools, filesystem tools, skills, and MCP tools.
Guidelines:
1. Always use the search_codebase tool before answering questions about the codebase.
2. When the user's request matches a skill, call load_skill(name) to get full instructions before proceeding.
3. Use specific file names, function names, and line numbers in your answers.
4. Formulate your final answer directly once relevant code or tool output is obtained.
5. If you cannot find the answer in the codebase, say so explicitly."""


async def build_agent(checkpointer=None, mcp_tools=None, enable_safety: bool = True):
    """Create and return a LangChain agent with persistent memory, tools, skills, and safety guardrails."""
    llm = get_llm()
    if mcp_tools is None:
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
        write_file,
        append_file,
        update_file,
        delete_file,
        list_directory,
        file_exists,
        ask_user,
        *mcp_tools,
    ]
    logger.info(f"Creating agent with {len(tools)} tools")

    middleware = []
    if enable_safety:
        show_redacted = env_bool("GUARDRAIL_SHOW_REDACTED_INPUT", default=False)
        # 1. Guardrails (ContentFilter, PII redact/mask/block, RedactionDebug, SafetyJudge)
        middleware.extend(build_guardrails(safety_model=llm, show_redacted_input=show_redacted))
        # 2. Human In The Loop approval
        middleware.append(build_hitl_middleware())

    return create_agent(
        llm,
        tools=tools,
        system_prompt=full_prompt,
        checkpointer=checkpointer,
        middleware=middleware,
    )
