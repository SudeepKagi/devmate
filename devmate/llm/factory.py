import os
from devmate.config import config
from devmate.observability.logger import get_logger
from devmate.observability.metrics_tracker import MetricsCallbackHandler

logger = get_logger(__name__)

def get_llm(
    model: str | None = None,
    temperature: float | None = None,
    callbacks: list | None = None,
):
    """Return the right LangChain LLM based on config with automated metrics tracking."""
    provider = config["llm"]["provider"].lower()
    selected_model = model or config["llm"]["model"]
    temp = temperature if temperature is not None else 0.2
    active_callbacks = list(callbacks) if callbacks is not None else [MetricsCallbackHandler()]
    logger.info(f"Using LLM provider: {provider}, model: {selected_model}")

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. Please add OPENAI_API_KEY=your_key in ~/.devmate/.env or .env file."
            )
        max_tokens = config["llm"].get("max_tokens", 1000)
        return ChatOpenAI(
            model=selected_model,
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temp,
            callbacks=active_callbacks,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(
            model=selected_model,
            google_api_key=api_key,
            max_retries=1,
            temperature=temp,
            callbacks=active_callbacks,
        )

    if provider == "groq":
        from langchain_groq import ChatGroq
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found. Please add GROQ_API_KEY=your_key in .env file."
            )
        return ChatGroq(
            model=selected_model,
            api_key=api_key,
            temperature=temp,
            callbacks=active_callbacks,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=selected_model,
            temperature=temp,
            callbacks=active_callbacks,
        )

    if provider == "grok":
        api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "XAI_API_KEY or GROK_API_KEY not found. Please add XAI_API_KEY=your_key in .env file."
            )
        if api_key.startswith("gsk_"):
            logger.info("Detected Groq API key (gsk_...). Using Groq provider.")
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=selected_model,
                api_key=api_key,
                temperature=temp,
                callbacks=active_callbacks,
            )

        from langchain_xai import ChatXAI
        return ChatXAI(
            model=selected_model,
            api_key=api_key,
            temperature=temp,
            callbacks=active_callbacks,
        )

    raise ValueError(f"Unsupported LLM provider: '{provider}'. Supported providers are: 'groq', 'anthropic', 'openai', 'gemini', 'grok'")

def get_embedder():
    """Return the right LangChain embedder based on config."""
    provider = config["embeddings"]["provider"].lower()
    model = config["embeddings"]["model"]
    logger.info(f"Using embeddings provider: {provider}, model: {model}")

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. Please add OPENAI_API_KEY=your_key in ~/.devmate/.env or .env file."
            )
        return OpenAIEmbeddings(model=model, api_key=api_key)

    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        return GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)

    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=model)

    raise ValueError(f"Unsupported embeddings provider: '{provider}'. Supported providers are: 'openai', 'gemini', 'huggingface'")
