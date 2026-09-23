import json
import os
import uuid

from fastapi.responses import StreamingResponse

from model_config import (
    get_default_chat_model,
    get_default_temperature,
    get_default_max_tokens
)
from rag import build_context, generate_answer, stream_answer
from services.document_loader import load_file
from services.kb_service import MiniKBService
from services.reranker_service import rerank_docs
from services.search_service import search_web
from db import (
    create_conversation,
    save_message,
    get_conversation_messages,
    user_owns_kb,
    get_conversation
)
from user_scope import get_user_temp_root, migrate_legacy_demo_files


temp_kb_services = {}


def get_metadata_filter(request):
    """负责 get_metadata_filter 的函数职责。"""
    metadata_filter = request.metadata_filter or {}
    source = request.source or request.file_name

    if source:
        metadata_filter = {
            **metadata_filter,
            "source": source
        }

    return metadata_filter or None


def is_safe_temp_kb_id(temp_kb_id: str) -> bool:
    """负责 is_safe_temp_kb_id 的函数职责。"""
    return (
        bool(temp_kb_id)
        and ".." not in temp_kb_id
        and "/" not in temp_kb_id
        and "\\" not in temp_kb_id
    )


def get_temp_root_path(user_id=None):
    """负责 get_temp_root_path 的函数职责。"""
    return get_user_temp_root(user_id)


def get_temp_kb_service(temp_kb_id: str, user_id=None):
    """负责 get_temp_kb_service 的函数职责。"""
    migrate_legacy_demo_files()

    if not is_safe_temp_kb_id(temp_kb_id):
        return None

    cache_key = (user_id, temp_kb_id)
    temp_root_path = get_temp_root_path(user_id)

    if cache_key not in temp_kb_services:
        temp_kb_path = os.path.join(temp_root_path, temp_kb_id)

        if not os.path.exists(temp_kb_path):
            return None

        temp_kb_services[cache_key] = MiniKBService(
            temp_kb_id,
            root_path=temp_root_path,
            user_id=user_id,
        )

    return temp_kb_services[cache_key]


def build_streaming_response(
    query,
    results,
    client,
    history,
    prompt_name,
    model=None,
    temperature=None,
    max_tokens=None,
    response_meta=None,
    save_assistant=None,
    source_type="local_kb",
):
    """负责 build_streaming_response 的函数职责。"""
    def event_stream():
        # SSE Sources 与真正进入 Prompt 的 Context chunk 保持一致。
        """负责 event_stream 的函数职责。"""
        answer_parts = []
        context, context_results = build_context(results, return_results=True)
        sources_event = {
            "type": "sources",
            "sources": context_results
        }

        if response_meta:
            sources_event.update(response_meta)

        yield f"data: {json.dumps(sources_event)}\n\n"

        try:
            for delta in stream_answer(
                query,
                results,
                client,
                history,
                model=model or get_default_chat_model(),
                temperature=(
                    temperature
                    if temperature is not None
                    else get_default_temperature()
                ),
                max_tokens=(
                    max_tokens
                    if max_tokens is not None
                    else get_default_max_tokens()
                ),
                prompt_name=prompt_name,
                source_type=source_type,
                context=context,
            ):
                answer_parts.append(delta)
                token_event = {
                    "type": "token",
                    "content": delta
                }
                yield f"data: {json.dumps(token_event)}\n\n"
        except Exception as exc:
            error_event = {
                "type": "error",
                "message": str(exc)
            }
            yield f"data: {json.dumps(error_event)}\n\n"

        assistant_message_id = None

        if save_assistant:
            assistant_message_id = save_assistant(
                "".join(answer_parts),
                context_results,
            )

        done_event = {
            "type": "done"
        }
        if assistant_message_id is not None:
            done_event["assistant_message_id"] = assistant_message_id

        yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


def get_fallback_answer(results):
    """模型调用失败时保留既有的检索首段回退行为。"""
    return results[0]["chunk"] if results else "No relevant information found."


def get_context_and_sources(results):
    """回答与持久化来源只使用真正进入 LLM Prompt 的 chunk。"""
    return build_context(results, return_results=True)


def run_local_kb_chat(request, kb_service, client, user_id=None):
    """负责 run_local_kb_chat 的函数职责。"""
    conversation_id = request.conversation_id

    if conversation_id is None:
        conversation_id = create_conversation(request.question, user_id=user_id)
    elif get_conversation(conversation_id, user_id=user_id) is None:
        return {
            "error": "conversation not found"
        }

    results = kb_service.search_docs(
        request.question,
        top_k=request.top_k,
        score_threshold=request.score_threshold
    )

    save_message(conversation_id, "user", request.question, user_id=user_id)
    history = get_conversation_messages(conversation_id, user_id=user_id)

    if request.return_direct:
        return {
            "conversation_id": conversation_id,
            "question": request.question,
            "answer": "",
            "sources": results,
            "return_direct": True
        }

    if request.stream:
        return build_streaming_response(
            request.question,
            results,
            client,
            history,
            request.prompt_name,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            response_meta={
                "conversation_id": conversation_id
            },
            save_assistant=lambda answer, sources: save_message(
                conversation_id,
                "assistant",
                answer,
                metadata={
                    "sources": sources
                },
                user_id=user_id,
            ),
            source_type="local_kb",
        )

    context, context_results = get_context_and_sources(results)

    try:
        answer = generate_answer(
            request.question,
            results,
            client,
            history,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            prompt_name=request.prompt_name,
            source_type="local_kb",
            context=context,
        )
    except Exception:
        answer = get_fallback_answer(context_results)

    assistant_message_id = save_message(
        conversation_id,
        "assistant",
        answer,
        metadata={
            "sources": context_results
        },
        user_id=user_id,
    )
    history = get_conversation_messages(conversation_id, user_id=user_id)

    return {
        "conversation_id": conversation_id,
        "assistant_message_id": assistant_message_id,
        "question": request.question,
        "answer": answer,
        "sources": context_results,
        "chat_history": history,
    }


def run_temp_kb_chat(request, client, user_id=None):
    """负责 run_temp_kb_chat 的函数职责。"""
    temp_service = get_temp_kb_service(request.temp_kb_id, user_id=user_id)

    if temp_service is None:
        return {
            "error": "temp knowledge base not found"
        }

    results = temp_service.search_docs(
        request.query,
        top_k=request.top_k,
        score_threshold=request.score_threshold
    )

    conversation_id = create_conversation(request.query, user_id=user_id)
    save_message(conversation_id, "user", request.query, user_id=user_id)
    history = get_conversation_messages(conversation_id, user_id=user_id)

    if request.stream:
        return build_streaming_response(
            request.query,
            results,
            client,
            history,
            request.prompt_name,
            response_meta={
                "conversation_id": conversation_id,
                "temp_kb_id": request.temp_kb_id
            },
            save_assistant=lambda answer, sources: save_message(
                conversation_id,
                "assistant",
                answer,
                metadata={
                    "sources": sources
                },
                user_id=user_id,
            ),
            source_type="temp_kb",
        )

    context, context_results = get_context_and_sources(results)

    try:
        answer = generate_answer(
            request.query,
            results,
            client,
            history,
            prompt_name=request.prompt_name,
            source_type="temp_kb",
            context=context,
        )
    except Exception:
        answer = get_fallback_answer(context_results)

    assistant_message_id = save_message(
        conversation_id,
        "assistant",
        answer,
        metadata={
            "sources": context_results
        },
        user_id=user_id,
    )

    return {
        "conversation_id": conversation_id,
        "assistant_message_id": assistant_message_id,
        "temp_kb_id": request.temp_kb_id,
        "question": request.query,
        "answer": answer,
        "sources": context_results
    }


def get_local_kb_service(kb_name: str, user_id=None):
    """负责 get_local_kb_service 的函数职责。"""
    if not user_owns_kb(kb_name, user_id=user_id):
        return None

    return MiniKBService(kb_name, user_id=user_id)


def get_rerank_model(service):
    """负责 get_rerank_model 的函数职责。"""
    if service is not None:
        return getattr(service, "model", None)

    try:
        default_service = get_local_kb_service("default")
        return default_service.model if default_service is not None else None
    except Exception:
        return None


def get_rerank_candidate_count(top_k, rerank_top_n):
    """Reranker 先看更大的初检索池，关闭 rerank 时不调用此规则。"""
    return max(int(top_k), int(rerank_top_n)) * 4


def run_kb_chat(request, client, user_id=None):
    """负责 run_kb_chat 的函数职责。"""
    if request.mode == "local_kb":
        service = get_local_kb_service(request.kb_name, user_id=user_id)

        if service is None:
            return {
                "error": "knowledge base not found"
            }

        conversation_id = request.conversation_id

        if conversation_id is None:
            conversation_id = create_conversation(request.query, user_id=user_id)
        elif get_conversation(conversation_id, user_id=user_id) is None:
            return {
                "error": "conversation not found"
            }

        save_message(conversation_id, "user", request.query, user_id=user_id)
        history = get_conversation_messages(conversation_id, user_id=user_id)
        response_meta = {
            "conversation_id": conversation_id,
            "mode": request.mode,
            "kb_name": request.kb_name
        }
    elif request.mode == "temp_kb":
        if not request.temp_kb_id:
            return {
                "error": "temp_kb_id is required for temp_kb mode"
            }

        service = get_temp_kb_service(request.temp_kb_id, user_id=user_id)

        if service is None:
            return {
                "error": "temp knowledge base not found"
            }

        conversation_id = request.conversation_id

        if conversation_id is None:
            conversation_id = create_conversation(request.query, user_id=user_id)
        elif get_conversation(conversation_id, user_id=user_id) is None:
            return {
                "error": "conversation not found"
            }

        save_message(conversation_id, "user", request.query, user_id=user_id)
        history = get_conversation_messages(conversation_id, user_id=user_id)
        response_meta = {
            "conversation_id": conversation_id,
            "mode": request.mode,
            "temp_kb_id": request.temp_kb_id
        }
    elif request.mode == "search_engine":
        service = None
        conversation_id = request.conversation_id

        if conversation_id is None:
            conversation_id = create_conversation(request.query, user_id=user_id)
        elif get_conversation(conversation_id, user_id=user_id) is None:
            return {
                "error": "conversation not found"
            }

        save_message(conversation_id, "user", request.query, user_id=user_id)
        history = get_conversation_messages(conversation_id, user_id=user_id)
        response_meta = {
            "conversation_id": conversation_id,
            "mode": request.mode
        }
    else:
        return {
            "error": "invalid mode"
        }

    retrieval_top_k = (
        get_rerank_candidate_count(request.top_k, request.rerank_top_n)
        if request.rerank
        else request.top_k
    )

    if request.mode == "search_engine":
        results = search_web(
            request.query,
            top_k=retrieval_top_k
        )
    else:
        results = service.search_docs(
            request.query,
            top_k=retrieval_top_k,
            score_threshold=request.score_threshold,
            metadata_filter=get_metadata_filter(request),
        )

    if request.rerank:
        rerank_model = get_rerank_model(service)

        if rerank_model is not None:
            results = rerank_docs(
                request.query,
                results,
                rerank_model,
                top_n=request.rerank_top_n
            )

    if request.return_direct:
        response = {
            "question": request.query,
            "answer": "",
            "sources": results,
            "return_direct": True,
            "mode": request.mode
        }

        if conversation_id is not None:
            response["conversation_id"] = conversation_id

        if request.mode == "local_kb":
            response["kb_name"] = request.kb_name
        elif request.mode == "temp_kb":
            response["temp_kb_id"] = request.temp_kb_id

        return response

    if request.stream:
        save_assistant = None

        if conversation_id is not None:
            save_assistant = lambda answer, sources: save_message(
                conversation_id,
                "assistant",
                answer,
                metadata={
                    "sources": sources
                },
                user_id=user_id,
            )

        return build_streaming_response(
            request.query,
            results,
            client,
            history,
            request.prompt_name,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            response_meta=response_meta,
            save_assistant=save_assistant,
            source_type=request.mode,
        )

    context, context_results = get_context_and_sources(results)

    try:
        answer = generate_answer(
            request.query,
            results,
            client,
            history,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            prompt_name=request.prompt_name,
            source_type=request.mode,
            context=context,
        )
    except Exception:
        answer = get_fallback_answer(context_results)

    response = {
        "question": request.query,
        "answer": answer,
        "sources": context_results,
        "mode": request.mode
    }

    if conversation_id is not None:
        assistant_message_id = save_message(
            conversation_id,
            "assistant",
            answer,
            metadata={
                "sources": context_results
            },
            user_id=user_id,
        )
        response["conversation_id"] = conversation_id
        response["assistant_message_id"] = assistant_message_id
        response["chat_history"] = get_conversation_messages(
            conversation_id,
            user_id=user_id,
        )

    if request.mode == "local_kb":
        response["kb_name"] = request.kb_name
    elif request.mode == "temp_kb":
        response["temp_kb_id"] = request.temp_kb_id

    return response


def create_temp_kb_from_upload(
    content,
    filename,
    chunk_size=300,
    chunk_overlap=50,
    user_id=None,
):
    """负责 create_temp_kb_from_upload 的函数职责。"""
    migrate_legacy_demo_files()

    filename = filename or "uploaded.txt"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in [".txt", ".pdf", ".docx", ".md", ".csv"]:
        return {
            "message": "Only .txt, .pdf, .docx, .md and .csv files are supported."
        }

    temp_kb_id = str(uuid.uuid4())
    temp_root_path = get_temp_root_path(user_id)
    temp_kb_path = os.path.join(temp_root_path, temp_kb_id)
    upload_path = os.path.join(temp_kb_path, "uploads")
    content_path = os.path.join(temp_kb_path, "content")
    vector_store_path = os.path.join(temp_kb_path, "vector_store")

    for path in (
        upload_path,
        content_path,
        vector_store_path,
    ):
        os.makedirs(path, exist_ok=True)

    original_path = os.path.join(upload_path, filename)
    with open(original_path, "wb") as f:
        f.write(content)

    text = load_file(original_path)
    txt_filename = f"{os.path.splitext(filename)[0]}.txt"
    txt_path = os.path.join(content_path, txt_filename)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    temp_kb_services[(user_id, temp_kb_id)] = MiniKBService(
        temp_kb_id,
        root_path=temp_root_path,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        user_id=user_id,
    )

    return {
        "temp_kb_id": temp_kb_id,
        "message": f"{filename} uploaded to temp knowledge base"
    }
