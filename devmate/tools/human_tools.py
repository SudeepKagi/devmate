from langchain_core.tools import tool


@tool
def ask_user(question: str) -> str:
    """Ask the human user for clarification or approval-related input."""
    # The real answer comes back through the HITL interrupt/resume flow;
    # this return value is just a placeholder for the initial tool call.
    return f"User input placeholder for question: {question}"
