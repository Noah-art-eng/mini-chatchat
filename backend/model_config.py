import os
import threading

from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_CHAT_MODEL = "gpt-4.1-mini"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = None
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_LLM_TIMEOUT_SECONDS = 30.0

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)


def get_llm_provider():
    """根据环境变量选择当前聊天与 Agent 共用的 LLM Provider。"""
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
    """返回当前 Provider 对应的 API Key。"""
    if get_llm_provider() == "deepseek":
        return get_deepseek_api_key()

    return get_openai_api_key()


def get_llm_base_url():
    """返回当前 Provider 的 OpenAI-compatible API 地址。"""
    if get_llm_provider() == "deepseek":
        return get_deepseek_base_url()

    return get_openai_base_url()


def get_default_chat_model():
    """返回当前 Provider 默认使用的聊天模型名。"""
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


def get_llm_timeout_seconds():
    try:
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", DEFAULT_LLM_TIMEOUT_SECONDS))
    except ValueError:
        return DEFAULT_LLM_TIMEOUT_SECONDS

    return timeout if timeout > 0 else DEFAULT_LLM_TIMEOUT_SECONDS


def get_openai_client():
    """按当前 Provider、超时和重试策略创建 OpenAI-compatible 客户端。"""
    client_kwargs = {
        "api_key": get_llm_api_key(),
        # OpenAI-compatible client applies this to Agent and chat model requests.
        "timeout": get_llm_timeout_seconds(),
        # Agent 的失败会走确定性 fallback；避免 SDK 重试把单次超时放大。
        "max_retries": 0,
    }

    base_url = get_llm_base_url()
    if base_url:
        client_kwargs["base_url"] = base_url

    return OpenAI(**client_kwargs)


class LazyOpenAIClient:
    """将共享 LLM client 延迟到第一次真正调用模型时再创建。

    这样没有 Provider Key 的干净环境仍能启动 Auth、KB 和前端；只有真正进入
    RAG 回答或 Agent 模型调用时，才要求完整的模型配置。
    """

    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    def _get_client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = get_openai_client()
        return self._client

    def __getattr__(self, name):
        return getattr(self._get_client(), name)


def get_lazy_openai_client():
    """供应用启动使用，使非 LLM 功能不依赖 provider key。"""
    return LazyOpenAIClient()
