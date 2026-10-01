"""API 请求模型；字段和默认值保持现有接口契约。"""

from pydantic import BaseModel, Field

from model_config import (
    get_default_chat_model,
    get_default_max_tokens,
    get_default_temperature,
)


MAX_TOP_K = 20
MAX_RERANK_TOP_N = 20


class ChatRequest(BaseModel):
    """负责 ChatRequest 的类职责。"""

    question: str
    conversation_id: int | None = None
    top_k: int = Field(default=3, ge=1, le=MAX_TOP_K)
    score_threshold: float = Field(default=0.8, ge=0)
    prompt_name: str = "default"
    return_direct: bool = False
    model: str = get_default_chat_model()
    temperature: float = get_default_temperature()
    max_tokens: int | None = get_default_max_tokens()
    stream: bool = False


class CreateKBRequest(BaseModel):
    """负责 CreateKBRequest 的类职责。"""

    kb_name: str


class SwitchKBRequest(BaseModel):
    """负责 SwitchKBRequest 的类职责。"""

    kb_name: str


class SearchDocsRequest(BaseModel):
    """负责 SearchDocsRequest 的类职责。"""

    query: str
    top_k: int = Field(default=3, ge=1, le=MAX_TOP_K)
    file_name: str | None = None


class ReindexFileRequest(BaseModel):
    """负责 ReindexFileRequest 的类职责。"""

    chunk_size: int = Field(default=300, gt=0)
    chunk_overlap: int = Field(default=50, ge=0)


class FileChatRequest(BaseModel):
    """负责 FileChatRequest 的类职责。"""

    query: str
    temp_kb_id: str
    top_k: int = Field(default=3, ge=1, le=MAX_TOP_K)
    score_threshold: float = Field(default=0.8, ge=0)
    prompt_name: str = "default"
    stream: bool = False


class KBChatRequest(BaseModel):
    """负责 KBChatRequest 的类职责。"""

    query: str
    mode: str = "local_kb"
    kb_name: str = "default"
    temp_kb_id: str | None = None
    top_k: int = Field(default=3, ge=1, le=MAX_TOP_K)
    score_threshold: float = Field(default=0.8, ge=0)
    prompt_name: str = "default"
    stream: bool = False
    model: str = get_default_chat_model()
    temperature: float = get_default_temperature()
    max_tokens: int | None = get_default_max_tokens()
    return_direct: bool = False
    conversation_id: int | None = None
    rerank: bool = False
    rerank_top_n: int = Field(default=3, ge=1, le=MAX_RERANK_TOP_N)
    file_name: str | None = None
    source: str | None = None
    metadata_filter: dict | None = None


class OpenAIChatCompletionRequest(BaseModel):
    """负责 OpenAIChatCompletionRequest 的类职责。"""

    model: str = get_default_chat_model()
    messages: list
    stream: bool = False
    temperature: float = get_default_temperature()
    max_tokens: int | None = get_default_max_tokens()
    extra_body: dict | None = None


class FeedbackRequest(BaseModel):
    """负责 FeedbackRequest 的类职责。"""

    message_id: int
    score: int
    reason: str | None = None


class ConversationUpdateRequest(BaseModel):
    """负责 ConversationUpdateRequest 的类职责。"""

    title: str


class ToolRunRequest(BaseModel):
    """负责 ToolRunRequest 的类职责。"""

    arguments: dict = {}


class AgentToolCallRequest(BaseModel):
    """负责 AgentToolCallRequest 的类职责。"""

    query: str
    kb_name: str | None = "default"
    tools: list[str] | None = None
    conversation_id: int | None = None
    max_steps: int = 3


class AuthEmailPasswordRequest(BaseModel):
    """负责 AuthEmailPasswordRequest 的类职责。"""

    email: str
    password: str
    display_name: str | None = None


class AuthPreferencesUpdateRequest(BaseModel):
    """负责 AuthPreferencesUpdateRequest 的类职责。"""

    language: str | None = None
    developer_mode: bool | None = None
    onboarding_completed: bool | None = None
    theme: str | None = None
    preferred_model: str | None = None


class AuthAccountUpdateRequest(BaseModel):
    """负责 AuthAccountUpdateRequest 的类职责。"""

    display_name: str | None = None

    class Config:
        """负责 Config 的类职责。"""

        extra = "forbid"
