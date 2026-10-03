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
    """拒绝能逃出临时知识库目录的编号，只允许单段安全名称。"""
    return (
        bool(temp_kb_id)
        and ".." not in temp_kb_id
        and "/" not in temp_kb_id
        and "\\" not in temp_kb_id
    )


def get_temp_root_path(user_id=None):
    """返回当前用户独立的临时知识库根目录。"""
    return get_user_temp_root(user_id)


def get_temp_kb_service(temp_kb_id: str, user_id=None):
    """取得当前用户临时知识库的 MiniKBService，不允许跨用户复用缓存对象。"""
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
    """把 RAG 回答转换成前端消费的 sources/token/error/done SSE 事件。

    函数先确定真正进入 Prompt 的 context_results，并把同一批结果作为 Sources。
    流结束后才持久化助手消息；中途失败时也保存已经生成的部分回答，使刷新前后
    看到的内容一致。
    """
    def event_stream():
        """执行模型流并按固定顺序发送 RAG SSE 事件。"""
        answer_parts = []
        stream_failed = False
        # build_context() 同时返回最终文本和实际采用的文本块，避免 Sources 引用被预算截掉的结果。
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
    """兼容旧 /chat：检索当前 MiniKBService，生成回答并保存会话消息。"""
    # 先建立或校验当前用户的会话，再执行知识库检索。旧接口与 /kb_chat 一样保持
    # conversation ownership，不能通过会话编号读取或追加其他用户的数据。
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

    # 直接返回模式到检索结果为止，不进入 Context 和 LLM。
    if request.return_direct:
        return {
            "conversation_id": conversation_id,
            "question": request.question,
            "answer": "",
            "sources": results,
            "return_direct": True
        }

    # 流式模式把后续 Context、SSE 和助手消息保存交给统一构造函数。
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

    # 非流式模式只用预算内的 context_results 生成答案和 Sources。
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
    """兼容旧 /file_chat：按 temp_kb_id 检索隔离索引并生成回答。"""
    # temp_kb_id 会和 user_id 一起查找服务，避免不同用户猜到编号后共享临时文件。
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

    # 临时知识库与正式知识库从这里汇入相同 SSE 构造流程，只改变来源语义。
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

    # 非流式回答仍然以实际进入 Context 的结果作为最终 Sources。
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
    """计算开启 Rerank 时，粗检索阶段需要先找多少条结果。

    top_k 是普通检索希望返回的数量，rerank_top_n 是 Rerank 后希望保留的数量。
    这里取两者较大值的 4 倍，让后面的 Rerank 有更大的候选池可供重新排序。
    """
    return max(int(top_k), int(rerank_top_n)) * 4

def run_kb_chat(request, client, user_id=None):
    """编排一轮 RAG 问答。

    `kb_chat()` 把前端请求交给这里。程序依次选择数据源、准备会话、执行检索和
    可选 Rerank，然后继续生成回答。普通响应和 SSE 响应也从这里返回给路由层。
    """
    if request.mode == "local_kb":
        # local_kb 使用用户长期保存的知识库。这里先检查知识库是否属于当前用户，
        # 再取得负责该知识库检索的 MiniKBService。验证完成后继续准备会话。
        service = get_local_kb_service(request.kb_name, user_id=user_id)

        if service is None:
            return {
                "error": "knowledge base not found"
            }

        mode_meta = {"kb_name": request.kb_name}
    elif request.mode == "temp_kb":
        # temp_kb 使用临时文件生成的知识库。这里先检查临时知识库 ID，再取得属于
        # 当前用户的 MiniKBService。验证完成后继续准备会话。
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
        # search_engine 不读取知识库，因此不需要 MiniKBService。这里完成模式准备后，
        # 先与其他模式汇合处理会话，稍后再进入 search_web()。
        service = None
        mode_meta = {}
    else:
        return {
            "error": "invalid mode"
        }

    # 三种模式的数据源已经准备完成，现在汇合处理会话。没有 conversation_id 就创建
    # 新会话；已有 ID 必须属于当前用户。验证通过后，本轮问题才能写入这段会话。
    conversation_id = request.conversation_id

    if conversation_id is None:
        conversation_id = create_conversation(request.query, user_id=user_id)
    elif get_conversation(conversation_id, user_id=user_id) is None:
        return {
            "error": "conversation not found"
        }

    # 先保存用户本轮问题，再读取这段会话的历史消息。检索完成后，回答流程会继续
    # 使用这些历史消息。
    save_message(conversation_id, "user", request.query, user_id=user_id)
    history = get_conversation_messages(conversation_id, user_id=user_id)

    # 记录本轮使用的会话、模式和数据源。后面的响应流程会用这些信息关联前端状态。
    response_meta = {
        "conversation_id": conversation_id,
        "mode": request.mode,
        **mode_meta,
    }

    # top_k 是普通检索希望返回多少条。开启 Rerank 时，retrieval_top_k 表示粗检索
    # 先多找多少条候选；它不是最终结果数量，后面的 Rerank 会再缩小结果集。
    retrieval_top_k = (
        get_rerank_candidate_count(request.top_k, request.rerank_top_n)
        if request.rerank
        else request.top_k
    )

    if request.mode == "search_engine":
        # 联网模式从这里进入 search_web()。它返回搜索结果后，程序回到这里，继续
        # 执行与知识库模式相同的可选 Rerank。
        results = search_web(
            request.query,
            top_k=retrieval_top_k
        )
    else:
        # 知识库模式从这里进入 MiniKBService.search_docs()。search_docs() 会先走
        # FAISS 和 BM25 两路召回；执行完成后回到这里，继续处理可选的 Rerank。
        results = service.search_docs(
            request.query,
            top_k=retrieval_top_k,
            score_threshold=request.score_threshold,
            # 在召回时过滤文本块，避免全库 top-k 提前挤掉目标文件中的候选内容。
            metadata_filter=get_metadata_filter(request),
        )

    if request.rerank:
        # 前一步只得到粗检索候选。开启 Rerank 后，这里重新计算用户问题与候选文本块
        # 的相关性并排序，只保留 rerank_top_n 条。完成后继续进入回答生成流程。
        rerank_model = get_rerank_model(service)

        if rerank_model is not None:
            results = rerank_docs(
                request.query,
                results,
                rerank_model,
                top_n=request.rerank_top_n
            )

    if request.return_direct:
        # return_direct 只把召回结果交给调用方，不构建 Prompt，也不调用 LLM。
        # 这个分支用于直接检查检索结果，因此 Sources 保留当前 results。
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
        # 流式模式从这里进入 build_streaming_response()。后者会构建 Context，调用
        # LLM 流式接口，发送 Sources/token/error/done，并在结束时保存助手消息。
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

    # 非流式模式先确定真正送入 Prompt 的 Context。context_results 只包含预算内实际
    # 采用的文本块，后面的 Sources 和数据库 metadata 都使用同一份结果。
    context, context_results = get_context_and_sources(results)

    try:
        # 这里进入 rag.generate_answer() 构造 Prompt 并调用 LLM。调用失败时只使用
        # 已进入 Context 的第一段内容回退，不把未采用的召回结果冒充回答依据。
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

    # 回答生成完成后组装对外响应。Sources 与上面的 context_results 保持一致。
    response = {
        "question": request.query,
        "answer": answer,
        "sources": context_results,
        "mode": request.mode
    }

    if conversation_id is not None:
        # 助手回答和 Sources 一起保存。页面刷新后，历史消息可以恢复当时展示的来源。
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
    """从已完成大小校验的 staging 文件创建一次会话使用的临时知识库。

    临时文件仍走“安装原文件 → 解析标准文本 → 创建 MiniKBService”的主流程，
    但目录和服务对象按 user_id + temp_kb_id 隔离，不写入正式知识库列表。
    """
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

    # 先准备该临时知识库自己的 uploads、content 和 vector_store 目录。
    try:
        for path in (
            upload_path,
            content_path,
            vector_store_path,
        ):
            os.makedirs(path, exist_ok=True)

        # staging 完整安装后再解析，避免一次性把上传内容重新读回内存。
        original_path = safe_join(upload_path, filename, field_name="filename")
        install_staged_file(staged_path, original_path)

        txt_filename = f"{os.path.splitext(filename)[0]}.txt"
        txt_path = safe_join(content_path, txt_filename, field_name="filename")
        parse_file_to_text_file(original_path, txt_path)

        # 服务对象按用户和临时编号保存。后续 temp_kb 问答只能取得自己的实例。
        temp_kb_services[(user_id, temp_kb_id)] = MiniKBService(
            temp_kb_id,
            root_path=temp_root_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            user_id=user_id,
        )
    except Exception:
        # 任一阶段失败都撤掉服务注册和半成品目录，不让失败上传留下可访问状态。
        temp_kb_services.pop((user_id, temp_kb_id), None)
        shutil.rmtree(temp_kb_path, ignore_errors=True)
        raise

    return {
        "temp_kb_id": temp_kb_id,
        "message": f"{filename} uploaded to temp knowledge base"
    }
