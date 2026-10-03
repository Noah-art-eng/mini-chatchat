"""OpenAI-compatible Chat Completions HTTP 适配层。"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from api.schemas import KBChatRequest, OpenAIChatCompletionRequest
from auth.dependencies import get_current_user_optional, get_request_user_id
from auth.models import CurrentUser
from chat_service import RAG_STREAM_ERROR_MESSAGE, run_kb_chat


def get_last_user_message(messages):
    """从 OpenAI messages 中取得最后一条用户输入，作为内部 RAG query。"""
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")

    return ""


def build_kb_chat_request_from_openai(request: OpenAIChatCompletionRequest):
    """把 OpenAI Chat Completions 请求转换为项目内部的 KBChatRequest。"""
    extra_body = request.extra_body or {}
    query = get_last_user_message(request.messages)

    try:
        return KBChatRequest(
            query=query,
            mode=extra_body.get("mode", "local_kb"),
            kb_name=extra_body.get("kb_name", "default"),
            temp_kb_id=extra_body.get("temp_kb_id"),
            top_k=extra_body.get("top_k", 3),
            score_threshold=extra_body.get("score_threshold", 0.8),
            prompt_name=extra_body.get("prompt_name", "default"),
            stream=request.stream,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            return_direct=extra_body.get("return_direct", False),
            conversation_id=extra_body.get("conversation_id"),
            rerank=extra_body.get("rerank", False),
            rerank_top_n=extra_body.get("rerank_top_n", 3),
            file_name=extra_body.get("file_name"),
            source=extra_body.get("source"),
            metadata_filter=extra_body.get("metadata_filter"),
        )
    except ValidationError as exc:
        # OpenAI 兼容入口手工构造请求模型，需显式保留 422 语义。
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


def build_openai_completion_response(completion_id, model, result):
    """把 run_kb_chat() 的非流式结果包装成 OpenAI-compatible JSON。"""
    return {
        "id": completion_id,
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.get("answer", "")
                },
                "finish_reason": "stop"
            }
        ],
        "sources": result.get("sources", []),
        "assistant_message_id": result.get("assistant_message_id")
    }


def build_openai_streaming_response(completion_id, model, internal_response):
    """把内部 RAG SSE 事件转换成 OpenAI Chat Completions 的流式格式。"""
    async def event_stream():
        """逐个转译 token/error/done，同时保留内部流式错误约定。"""
        buffer = ""
        stream_failed = False

        async for chunk in internal_response.body_iterator:
            if isinstance(chunk, bytes):
                buffer += chunk.decode("utf-8")
            else:
                buffer += str(chunk)

            events = buffer.split("\n\n")
            buffer = events.pop()

            for event_text in events:
                lines = [
                    line
                    for line in event_text.split("\n")
                    if line.startswith("data:")
                ]

                for line in lines:
                    payload = line.replace("data:", "", 1).strip()

                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                    if event.get("type") == "token":
                        chunk_data = {
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "model": model,
                            "choices": [
                                {
                                    "delta": {
                                        "content": event.get("content", "")
                                    },
                                    "index": 0,
                                    "finish_reason": None
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk_data)}\n\n"

                    if event.get("type") == "error":
                        stream_failed = True
                        error_data = {
                            "error": {
                                "message": RAG_STREAM_ERROR_MESSAGE,
                                "type": "server_error",
                                "code": "rag_stream_error",
                            }
                        }
                        yield f"data: {json.dumps(error_data)}\n\n"

                    if event.get("type") == "done":
                        if not stream_failed:
                            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


def build_openai_static_streaming_response(completion_id, model, result):
    """把已完成的非流式结果包装成一条 chunk 和最终 [DONE]。"""
    async def event_stream():
        """输出兼容客户端期望的最小 SSE 序列。"""
        content = result.get("answer", "")

        if content:
            chunk_data = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [
                    {
                        "delta": {
                            "content": content
                        },
                        "index": 0,
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


def create_openai_compat_router(client):
    """绑定应用共享的 LLM client，并创建 OpenAI-compatible Router。"""
    router = APIRouter()

    @router.post("/chat/completions")
    def chat_completions(
        request: OpenAIChatCompletionRequest,
        current_user: CurrentUser = Depends(get_current_user_optional),
    ):
        """接收 OpenAI-compatible 请求，复用 run_kb_chat() 完成实际 RAG 问答。"""
        query = get_last_user_message(request.messages)

        if not query:
            return {
                "error": "messages must contain at least one user message"
            }

        completion_id = f"chatcmpl-{uuid.uuid4()}"
        kb_request = build_kb_chat_request_from_openai(request)
        result = run_kb_chat(
            kb_request,
            client,
            user_id=get_request_user_id(current_user),
        )

        if request.stream and isinstance(result, StreamingResponse):
            return build_openai_streaming_response(
                completion_id,
                request.model,
                result
            )

        if request.stream:
            return build_openai_static_streaming_response(
                completion_id,
                request.model,
                result
            )

        return build_openai_completion_response(
            completion_id,
            request.model,
            result
        )

    return router
