try:
    from deepeval.tracing import observe
except ImportError:
    def observe(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

from devmate.config import config
from devmate.agent.tools import reset_search_history
from devmate.safety.guardrails import PIIDetectionError
from devmate.safety.hitl import handle_interrupts
from devmate.observability.logger import get_logger
from devmate.observability.metrics_tracker import metrics_tracker, MetricsCallbackHandler

logger = get_logger(__name__)


@observe(type="agent", name="codebase_agent")
async def handle_query(
    agent,
    question: str,
    thread_id: str,
    semantic_cache=None,
    cache_domain: str | None = None,
) -> str:
    """Entry point for all user queries - invokes agent with semantic caching, HITL interrupts, and guardrails."""
    logger.info(f"Handling query for session {thread_id}: {question}")
    model = config.get("llm", {}).get("model", "gpt-4o-mini")

    if semantic_cache is not None and cache_domain is not None:
        try:
            cached_response = await semantic_cache.get(question, domain=cache_domain, model=model)
        except Exception as e:
            logger.warning(f"Semantic cache lookup failed, falling back to agent: {e}")
            cached_response = None
        if cached_response is not None:
            logger.info("Semantic cache HIT - skipping agent/tool calls")
            metrics_tracker.record_cache_event(task_id=thread_id, hit=True, domain=cache_domain, key=question)
            return cached_response
        else:
            metrics_tracker.record_cache_event(task_id=thread_id, hit=False, domain=cache_domain, key=question)

    reset_search_history()
    agent_config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 100,
        "callbacks": [MetricsCallbackHandler()],
    }
    try:
        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]},
            agent_config,
        )

        # Resolve any Human-In-The-Loop approval prompts before returning reply
        response = await handle_interrupts(agent, response, agent_config)

        if hasattr(response, "value"):
            response = response.value

        answer = ""
        if isinstance(response, dict) and "messages" in response and response["messages"]:
            content = response["messages"][-1].content
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        parts.append(item["text"])
                    elif isinstance(item, str):
                        parts.append(item)
                answer = "\n".join(parts)
            else:
                answer = str(content)
        else:
            answer = str(response)

        if semantic_cache is not None and cache_domain is not None and answer:
            try:
                ttl = config.get("semantic_cache", {}).get("ttl", 86400)
                await semantic_cache.put(question, answer, domain=cache_domain, model=model, ttl=ttl)
            except Exception as e:
                logger.warning(f"Semantic cache store failed: {e}")

        return answer

    except PIIDetectionError as error:
        logger.warning(f"Guardrail blocked request: {error}")
        return f"Bot: Guardrail blocked your request because it contains sensitive or blocked credentials.\nDetails: {error}"
    except Exception as e:
        logger.error(f"Agent error: {e}")
        return f"Error: {e}"
