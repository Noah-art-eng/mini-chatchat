import json
import logging
import os
import shutil
import uuid

from fastapi.responses import StreamingResponse

from model_config import (
    get_default_chat_model,
    get_default_temperature,
    get_default_max_tokens
)
from rag import build_context, generate_answer, stream_answer
from services.document_loader import parse_file_to_text_file
from services.kb_service import MiniKBService
from services.reranker_service import rerank_docs
from services.search_service import search_web
from path_security import safe_join, validate_filename
from resource_limits import install_staged_file
from db import (
    create_conversation,
    save_message,
    get_conversation_messages,
    user_owns_kb,
    get_conversation
)
from user_scope import get_user_temp_root, migrate_legacy_demo_files


temp_kb_services = {}
logger = logging.getLogger(__name__)
RAG_STREAM_ERROR_MESSAGE = "Streaming response failed. Please try again."


def get_metadata_filter(request):
    """整理传给检索层的 metadata_filter，即对候选文本块的字段过滤条件。

    request 中的通用元数据条件会与 source/file_name 指定的文件范围合并。
    条件直接进入候选检索，而不是先从全库取 top-k 再过滤；后者可能让目标文件
    的有效文本块在过滤前就被截掉。整理后的条件随后交给 `search_docs()` 使用。
    """
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
        stream_failed = False
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
            # 客户端只需要稳定错误语义；具体 SDK/网络异常保留在服务端日志中。
            logger.exception("RAG LLM streaming failed", exc_info=exc)
            stream_failed = True

        assistant_message_id = None
        answer = "".join(answer_parts)
        if stream_failed and not answer:
            # 首个 token 前失败时，UI 会展示这条通用提示，历史记录保存同一内容。
            answer = RAG_STREAM_ERROR_MESSAGE

        if save_assistant:
            assistant_message_id = save_assistant(
                answer,
                context_results,
            )

        if stream_failed:
            error_event = {
                "type": "error",
                "message": RAG_STREAM_ERROR_MESSAGE,
                "partial_response": bool(answer_parts),
            }
            yield f"data: {json.dumps(error_event)}\n\n"

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
    """取得正式知识库对应的 MiniKBService，用于后续检索其中的文档文本块。

    MiniKBService 是封装知识库索引、检索和持久化操作的服务对象。创建它之前
    必须同时用 kb_name 和 user_id 检查用户归属，避免打开其他用户的同名知识库。
    校验通过后，返回的服务对象会继续交给 `search_docs()` 执行检索。
    """
    if not user_owns_kb(kb_name, user_id=user_id):
        return None

    return MiniKBService(kb_name, user_id=user_id)


def get_rerank_model(service):
    """取得 Rerank 所需的 embedding 模型，用于重新排列初检索候选结果。

    该模型会把用户问题和每个候选文本块转换成向量，再按余弦相似度排序。
    `local_kb` 和 `temp_kb` 复用当前 MiniKBService 已加载的模型；`search_engine`
    没有对应的知识库服务对象，因此尝试复用 default 知识库的模型。模型不可用时
    返回 None，让调用方保留初检索顺序。
    """
    if service is not None:
        return getattr(service, "model", None)

    try:
        default_service = get_local_kb_service("default")
        return default_service.model if default_service is not None else None
    except Exception:
        return None


def get_rerank_candidate_count(top_k, rerank_top_n):
    """计算送入 Rerank 的初检索候选数量。

    top_k 是不开启 Rerank 时希望检索返回的数量，rerank_top_n 是精排后最终
    保留的数量。开启 Rerank 时先召回两者较大值的 4 倍，让精排能从更多文本块
    中挑选。返回的 retrieval_top_k 只是粗检索候选数量，不是最终回答使用的数量，
    也不参与 FAISS/BM25 的相关性分数计算。
    """
    return max(int(top_k), int(rerank_top_n)) * 4

def run_kb_chat(request, client, user_id=None):
    """编排 RAG 问答：选择数据源、维护对话记录、检索并生成回答。

    conversation_id 指向数据库中保存连续消息的对话记录；service 是当前知识库的
    MiniKBService；results 是检索得到、随后可供 Rerank 和 Prompt 使用的文本块。
    `local_kb`、`temp_kb` 和 `search_engine` 的数据源不同，因此先分流，得到统一
    结构的 results 后再汇合到回答/SSE 流程。user_id 始终参与知识库归属、对话
    校验和消息读写，避免不同用户之间共享状态。
    """
    if request.mode == "local_kb":
        # local_kb 使用用户长期保存的知识库。这里先确认知识库归属并取得
        # MiniKBService；会话准备完成后，再用这个服务对象进入 search_docs()。
        service = get_local_kb_service(request.kb_name, user_id=user_id)

        if service is None:
            return {
                "error": "knowledge base not found"
            }

        mode_meta = {"kb_name": request.kb_name}
    elif request.mode == "temp_kb":
        # temp_kb 来自临时文件问答。这里先验证临时 ID，再按 user_id 取得对应的
        # MiniKBService；后续与正式知识库一样进入 search_docs()，但不会混用目录。
        if not request.temp_kb_id:
            return {
                "error": "temp_kb_id is required for temp_kb mode"
            }

        service = get_temp_kb_service(request.temp_kb_id, user_id=user_id)

        if service is None:
            return {
                "error": "temp knowledge base not found"
            }

        mode_meta = {"temp_kb_id": request.temp_kb_id}
    elif request.mode == "search_engine":
        # search_engine 不读取本地知识库，因此不创建 MiniKBService；会话准备完成后，
        # 程序会进入 search_web() 获取联网搜索结果，并整理成统一的 results。
        service = None
        mode_meta = {}
    else:
        return {
            "error": "invalid mode"
        }

    # 三种合法模式在上面只完成各自的数据源校验和服务对象准备；确认数据源可用后才统一
    # 确定消息写入哪个对话。没有 conversation_id 就创建新对话，复用已有对话时则校验
    # 用户归属，防止读取或追加其他用户的消息。
    conversation_id = request.conversation_id

    if conversation_id is None:
        conversation_id = create_conversation(request.query, user_id=user_id)
    elif get_conversation(conversation_id, user_id=user_id) is None:
        return {
            "error": "conversation not found"
        }

    # 用户归属确认后，先保存本轮问题，再读取完整历史消息；这些消息会在检索完成后
    # 与知识库上下文一起交给 LLM，因此当前问题也必须包含在历史中。
    save_message(conversation_id, "user", request.query, user_id=user_id)
    history = get_conversation_messages(conversation_id, user_id=user_id)

    # response_meta 记录本次回答属于哪个对话、模式和数据源；流式响应时会随 SSE 的
    # sources 事件发给前端，避免 Sources 被关联到错误的会话或知识库。
    response_meta = {
        "conversation_id": conversation_id,
        "mode": request.mode,
        **mode_meta,
    }

    # 三种模式从这里重新汇合。top_k 是普通检索希望返回的数量；开启 Rerank 后，
    # retrieval_top_k 会扩大为粗检索候选池，让后面的精排有足够结果可选。它不是
    # 最终回答数量，真正保留多少条由后面的 rerank_top_n 决定。
    retrieval_top_k = (
        get_rerank_candidate_count(request.top_k, request.rerank_top_n)
        if request.rerank
        else request.top_k
    )

    if request.mode == "search_engine":
        # 搜索引擎模式进入 search_web() 执行联网搜索，返回统一结构的候选 results；
        # 调用结束后回到这里，与两种知识库模式共同进入可选的 Rerank。
        results = search_web(
            request.query,
            top_k=retrieval_top_k
        )
    else:
        # local_kb 和 temp_kb 在这里进入 MiniKBService.search_docs()，由它执行
        # FAISS + BM25 混合检索并返回候选文本块；调用结束后回到这里继续 Rerank。
        results = service.search_docs(
            request.query,
            top_k=retrieval_top_k,
            score_threshold=request.score_threshold,
            # 在召回时过滤文本块，避免全库 top-k 提前挤掉目标文件中的候选内容。
            metadata_filter=get_metadata_filter(request),
        )

    if request.rerank:
        # 前面的混合检索或联网搜索只负责找出一批候选结果。开启 Rerank 后，这里
        # 根据用户问题与候选文本块的余弦相似度重新排序，只保留 rerank_top_n 条；
        # 随后这些结果会继续用于构建最终上下文并生成回答。
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
    staged_path,
    filename,
    chunk_size=300,
    chunk_overlap=50,
    user_id=None,
):
    """从已完成大小校验的 staging 文件创建临时知识库。"""
    filename = validate_filename(filename or "uploaded.txt")
    migrate_legacy_demo_files()

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

    try:
        for path in (
            upload_path,
            content_path,
            vector_store_path,
        ):
            os.makedirs(path, exist_ok=True)

        original_path = safe_join(upload_path, filename, field_name="filename")
        install_staged_file(staged_path, original_path)

        txt_filename = f"{os.path.splitext(filename)[0]}.txt"
        txt_path = safe_join(content_path, txt_filename, field_name="filename")
        parse_file_to_text_file(original_path, txt_path)

        temp_kb_services[(user_id, temp_kb_id)] = MiniKBService(
            temp_kb_id,
            root_path=temp_root_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            user_id=user_id,
        )
    except Exception:
        temp_kb_services.pop((user_id, temp_kb_id), None)
        shutil.rmtree(temp_kb_path, ignore_errors=True)
        raise

    return {
        "temp_kb_id": temp_kb_id,
        "message": f"{filename} uploaded to temp knowledge base"
    }
