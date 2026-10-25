import os
from devmate.config import config
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

def get_llm():
    """Return the right LangChain LLM based on config."""
    provider = config["llm"]["provider"].lower()
    model = config["llm"]["model"]
    logger.info(f"Using LLM provider: {provider}, model: {model}")

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        # max_retries=1 prevents tenacity from freezing the terminal for minutes on 429s
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            max_retries=1,
            temperature=0.2,
        )

    if provider == "grok":
        from langchain_xai import ChatXAI
        api_key = os.getenv("XAI_API_KEY")
        return ChatXAI(model=model, api_key=api_key)

    raise ValueError(f"Unsupported LLM provider: '{provider}'. Supported providers are: 'gemini', 'grok'")

def get_embedder():
    """Return the right LangChain embedder based on config."""
    provider = config["embeddings"]["provider"].lower()
    model = config["embeddings"]["model"]
    logger.info(f"Using embeddings provider: {provider}, model: {model}")

    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        return GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)

    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=model)

    raise ValueError(f"Unsupported embeddings provider: '{provider}'. Supported providers are: 'gemini', 'huggingface'")
