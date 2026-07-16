import os

from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_CHAT_MODEL = "gpt-4.1-mini"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = None
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)


def get_llm_provider():
    if os.getenv("DEEPSEEK_API_KEY"):
        return "deepseek"

    return "openai"


def get_openai_api_key():
    return os.getenv("OPENAI_API_KEY")


def get_openai_base_url():
    return os.getenv("OPENAI_BASE_URL")


def get_deepseek_api_key():
    return os.getenv("DEEPSEEK_API_KEY")


def get_deepseek_base_url():
    return os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL)


def get_llm_api_key():
    if get_llm_provider() == "deepseek":
        return get_deepseek_api_key()

    return get_openai_api_key()


def get_llm_base_url():
    if get_llm_provider() == "deepseek":
        return get_deepseek_base_url()

    return get_openai_base_url()


def get_default_chat_model():
    if get_llm_provider() == "deepseek":
        return os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)

    return (
        os.getenv("OPENAI_MODEL")
        or os.getenv("DEFAULT_CHAT_MODEL")
        or DEFAULT_CHAT_MODEL
    )


def get_default_temperature():
    value = os.getenv("DEFAULT_TEMPERATURE")

    if value is None:
        return DEFAULT_TEMPERATURE

    try:
        return float(value)
    except ValueError:
        return DEFAULT_TEMPERATURE


def get_default_max_tokens():
    value = os.getenv("DEFAULT_MAX_TOKENS")

    if value in (None, ""):
        return DEFAULT_MAX_TOKENS

    try:
        return int(value)
    except ValueError:
        return DEFAULT_MAX_TOKENS


def get_embedding_model_name():
    return (
        os.getenv("EMBEDDING_MODEL_NAME")
        or os.getenv("EMBEDDING_MODEL")
        or DEFAULT_EMBEDDING_MODEL
    )


def get_openai_client():
    client_kwargs = {
        "api_key": get_llm_api_key()
    }

    base_url = get_llm_base_url()
    if base_url:
        client_kwargs["base_url"] = base_url

    return OpenAI(**client_kwargs)
