from devmate.agent.tools import reset_search_history
from devmate.observability.logger import get_logger

logger = get_logger(__name__)


async def handle_query(agent, question: str, thread_id: str) -> str:
    """Entry point for all user queries - invokes the agent."""
    logger.info(f"Handling query for session {thread_id}: {question}")
    reset_search_history()
    agent_config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 25,
    }
    try:
        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]},
            agent_config,
        )

        if isinstance(response, dict) and "messages" in response and response["messages"]:
            content = response["messages"][-1].content
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        parts.append(item["text"])
                    elif isinstance(item, str):
                        parts.append(item)
                return "\n".join(parts)
            return str(content)

        return str(response)
    except Exception as e:
        logger.error(f"Agent error: {e}")
        return f"Error: {e}"
