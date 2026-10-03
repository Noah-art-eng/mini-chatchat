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
    """旧 `/chat` 接口的问答参数和模型生成选项。"""

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
    """创建知识库时由客户端提交的名称。"""

    kb_name: str


class SwitchKBRequest(BaseModel):
    """切换当前用户后端 KB 状态时提交的目标名称。"""

    kb_name: str


class SearchDocsRequest(BaseModel):
    """直接查看知识库检索结果时使用的查询参数。"""

    query: str
    top_k: int = Field(default=3, ge=1, le=MAX_TOP_K)
    file_name: str | None = None


class ReindexFileRequest(BaseModel):
    """重新索引文件时使用的文本块大小和重叠设置。"""

    chunk_size: int = Field(default=300, gt=0)
    chunk_overlap: int = Field(default=50, ge=0)


class FileChatRequest(BaseModel):
    """兼容旧临时文件问答接口的请求参数。"""

    query: str
    temp_kb_id: str
    top_k: int = Field(default=3, ge=1, le=MAX_TOP_K)
    score_threshold: float = Field(default=0.8, ge=0)
    prompt_name: str = "default"
    stream: bool = False


class KBChatRequest(BaseModel):
    """RAG 主入口参数，统一 local_kb、temp_kb 和 search_engine 三种模式。"""

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
    """OpenAI-compatible `/chat/completions` 接口接受的最小请求结构。"""

    model: str = get_default_chat_model()
    messages: list
    stream: bool = False
    temperature: float = get_default_temperature()
    max_tokens: int | None = get_default_max_tokens()
    extra_body: dict | None = None


class FeedbackRequest(BaseModel):
    """用户对一条助手消息提交的评分和可选原因。"""

    message_id: int
    score: int
    reason: str | None = None


class ConversationUpdateRequest(BaseModel):
    """重命名会话时提交的新标题。"""

    title: str


class ToolRunRequest(BaseModel):
    """直接调试一个已注册工具时传入的参数字典。"""

    arguments: dict = {}


class AgentToolCallRequest(BaseModel):
    """Agent 单步、多步和 Planner 路由共用的执行请求。"""

    query: str
    kb_name: str | None = "default"
    tools: list[str] | None = None
    conversation_id: int | None = None
    max_steps: int = 3


class AuthEmailPasswordRequest(BaseModel):
    """邮箱注册和登录共用的凭据结构。"""

    email: str
    password: str
    display_name: str | None = None


class AuthPreferencesUpdateRequest(BaseModel):
    """允许前端按字段更新当前用户偏好。"""

    language: str | None = None
    developer_mode: bool | None = None
    onboarding_completed: bool | None = None
    theme: str | None = None
    preferred_model: str | None = None


class AuthAccountUpdateRequest(BaseModel):
    """当前账号允许修改的公开资料；额外字段会被拒绝。"""

    display_name: str | None = None

    class Config:
        extra = "forbid"
