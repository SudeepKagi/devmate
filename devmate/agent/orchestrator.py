from devmate.agent.factory import build_agent
from devmate.agent.tools import reset_search_history
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

def handle_query(question: str) -> str:
    """Entry point for all user queries - builds the agent and runs it."""
    logger.info(f"Handling query: {question}")
    reset_search_history()
    agent = build_agent()
    response = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"recursion_limit": 25}
    )

    raw_content = ""
    if isinstance(response, dict) and "messages" in response and response["messages"]:
        content = response["messages"][-1].content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            raw_content = "\n".join(parts)
        else:
            raw_content = str(content)
    else:
        raw_content = response.get("output", str(response))

    return raw_content
