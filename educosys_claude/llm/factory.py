from educosys_claude.config import config
from educosys_claude.observability.logger import get_logger

logger = get_logger(__name__)


def get_llm():
    """Return the right LangChain LLM based on config."""
    provider = config.get("llm", {}).get("provider", "openai")
    model = config.get("llm", {}).get("model", "gpt-4o-mini")
    logger.info(f"Using LLM provider: {provider}, model: {model}")

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model)
    elif provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model_name=model)

    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=model)


def get_embedder():
    """Return the right LangChain embedder based on config."""
    provider = config.get("embeddings", {}).get("provider", "openai")
    model = config.get("embeddings", {}).get("model", "text-embedding-3-small")
    logger.info(f"Using embeddings provider: {provider}, model: {model}")

    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=model)

    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=model)
