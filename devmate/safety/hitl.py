from __future__ import annotations

import json
from langchain.agents.middleware import HumanInTheLoopMiddleware, ToolCallRequest
from langgraph.types import Command
from rich.console import Console
from devmate.observability.logger import get_logger

logger = get_logger(__name__)
console = Console()

DANGEROUS_TOKENS = [
    "rm ",
    "del ",
    "rmdir ",
    "format ",
    "shutdown",
    "reboot",
    "mkfs",
    "diskpart",
    "reg delete",
    "powershell -encodedcommand",
    "drop table",
    "truncate table",
]


def is_dangerous_command(request: ToolCallRequest) -> bool:
    """Predicate for terminal commands: only pause for approval if the command looks destructive."""
    cmd = str(request.tool_call.get("args", {}).get("command", "")).lower()
    return any(token in cmd for token in DANGEROUS_TOKENS)


def build_hitl_middleware() -> HumanInTheLoopMiddleware:
    """Gate specific tool calls behind human approval before they execute."""
    return HumanInTheLoopMiddleware(
        interrupt_on={
            "delete_file": {"allowed_decisions": ["approve", "reject"]},
            "write_file": {"allowed_decisions": ["approve", "edit", "reject"]},
            "append_file": {"allowed_decisions": ["approve", "edit", "reject"]},
            "update_file": {"allowed_decisions": ["approve", "edit", "reject"]},
            "run_command": {
                "allowed_decisions": ["approve", "edit", "reject"],
                "when": is_dangerous_command,
            },
            "run_in_directory": {
                "allowed_decisions": ["approve", "edit", "reject"],
                "when": is_dangerous_command,
            },
            "ask_user": {"allowed_decisions": ["respond"]},
        },
        description_prefix="Tool execution pending approval",
    )


async def handle_interrupts(agent, result, config: dict):
    """Pause resolution loop: keeps resolving HITL interrupts and resuming the agent."""
    while getattr(result, "interrupts", None):
        interrupt = result.interrupts[0]
        payload = interrupt.value
        action_requests = payload.get("action_requests", [])
        review_configs = payload.get("review_configs", [])

        if not action_requests:
            break

        decisions = []
        for index, action in enumerate(action_requests):
            tool_name = action.get("name", "unknown_tool")
            arguments = action.get("args", {})
            allowed = review_configs[index].get(
                "allowed_decisions",
                ["approve", "edit", "reject", "respond"],
            )

            console.print(f"\n[bold yellow]Approval needed for tool:[/bold yellow] [bold cyan]{tool_name}[/bold cyan]")
            console.print(f"[dim]Arguments: {arguments}[/dim]")
            console.print(f"[dim]Allowed decisions: {', '.join(allowed)}[/dim]")

            # ask_user calls expect a free-text response
            if "respond" in allowed and tool_name == "ask_user":
                prompt_q = arguments.get("question", "Agent asks for clarification:")
                console.print(f"[bold]{prompt_q}[/bold]")
                user_reply = input("Your response: ").strip()
                decisions.append({"type": "respond", "message": user_reply})
                continue

            choice = input("Decision [approve/edit/reject]: ").strip().lower()
            while choice not in allowed:
                choice = input(f"Choose one of {allowed}: ").strip().lower()

            if choice == "approve":
                decisions.append({"type": "approve"})
            elif choice == "reject":
                feedback = input("Rejection feedback (optional): ").strip()
                decision = {"type": "reject"}
                if feedback:
                    decision["message"] = feedback
                decisions.append(decision)
            elif choice == "edit":
                console.print("Provide edited args as JSON object. Example: {\"path\":\"notes.txt\"}")
                edited_args_raw = input("Edited args JSON: ").strip()
                edited_args = json.loads(edited_args_raw) if edited_args_raw else arguments
                decisions.append({
                    "type": "edit",
                    "edited_action": {"name": tool_name, "args": edited_args},
                })

        # Resume the graph supplying human decisions
        if hasattr(agent, "ainvoke"):
            result = await agent.ainvoke(
                Command(resume={"decisions": decisions}),
                config=config,
            )
        else:
            result = agent.invoke(
                Command(resume={"decisions": decisions}),
                config=config,
            )

    return result
