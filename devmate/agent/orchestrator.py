from devmate.agent.factory import build_agent
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

def handle_query(question: str) -> str:
    """Entry point for all user queries - builds the agent and runs it."""
    logger.info(f"Handling query: {question}")
    agent = build_agent()
    response = agent.invoke({"messages": [{"role": "user", "content": question}]})
    if isinstance(response, dict) and "messages" in response and response["messages"]:
        return response["messages"][-1].content
    return response.get("output", str(response))
