from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
from dotenv import load_dotenv
import os
from pypdf import PdfReader
from model_config import (
    get_default_chat_model,
    get_default_temperature,
    get_default_max_tokens,
    get_embedding_model_name,
    get_openai_client
)
from prompts import get_prompt_template

DEFAULT_CONTEXT_TOKEN_BUDGET = 3000
DEFAULT_EMBEDDING_BATCH_SIZE = 64

SOURCE_SEMANTICS = {
    "local_kb": {
        "source_instruction": (
            "Answer the question using the provided local knowledge base "
            "materials."
        ),
        "missing_instruction": (
            "say that the information is not found in the local knowledge base."
        ),
        "empty_source_instruction": (
            "The local knowledge base did not return relevant context for "
            "this question."
        ),
    },
    "temp_kb": {
        "source_instruction": (
            "Answer the question using the temporary file content uploaded "
            "by the user for this chat."
        ),
        "missing_instruction": (
            "say that the information is not found in the uploaded temporary "
            "file."
        ),
        "empty_source_instruction": (
            "The uploaded temporary file did not return relevant context for "
            "this question."
        ),
    },
    "search_engine": {
        "source_instruction": (
            "Answer the question using the web search results provided in "
            "the context. Prefer verifiable and newer sources when the query "
            "asks about recent or changing information. If sources conflict, "
            "state the uncertainty. Describe the sources only as web search "
            "results or web pages, not as private/local document material. "
            "When answering in Chinese, prefer wording such as "
            "根据检索到的网页信息 or 根据联网检索结果."
        ),
        "missing_instruction": (
            "say that the web search results do not confirm the answer. For "
            "real-time date or clock questions, do not invent the current "
            "value; explain that search results may only provide timezone "
            "rules or page summaries."
        ),
        "empty_source_instruction": (
            "The web search did not return relevant results for this question."
        ),
    },
}


def get_source_semantics(source_type="local_kb"):
    """负责 get_source_semantics 的函数职责。"""
    return SOURCE_SEMANTICS.get(source_type, SOURCE_SEMANTICS["local_kb"])


def estimate_tokens(text):
    """
    Lightweight token estimate for prompt budgeting.
    English text is roughly 4 chars/token; CJK text is closer to 1 char/token.
    """
    if not text:
        return 0

    cjk_chars = sum(
        1
        for char in text
        if "\u4e00" <= char <= "\u9fff"
    )
    non_cjk_chars = len(text) - cjk_chars

    return cjk_chars + max(1, non_cjk_chars // 4)


def load_documents(folder_path):
    """负责 load_documents 的函数职责。"""
    documents = []

    for filename in os.listdir(folder_path):
        if not filename.endswith(".txt"):
            continue

        with open(
            os.path.join(folder_path, filename),
            "r",
            encoding="utf-8"
        ) as file:
            text = file.read()

            documents.append({
                "text": text,
                "source": filename
            })

    return documents


def load_pdf(file_path):
    """负责 load_pdf 的函数职责。"""
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    return text


def split_documents(documents, chunk_size=300, overlap=50):
    """负责 split_documents 的函数职责。"""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between 0 and chunk_size - 1")

    chunks = []
    for document in documents:
        text = document["text"]
        source = document["source"]
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            chunks.append({
    "text": chunk_text,
    "source": source,
    "chunk_id": len(chunks) + 1
})
            start = end - overlap
    return chunks


def load_and_split_documents(folder_path, chunk_size=300, overlap=50):
    """逐个读取 content 文件并直接生成与旧逻辑兼容的 chunk 列表。

    最终 chunks 仍需供 BM25、FAISS 位置映射和持久化使用；这里消除的是
    rebuild 期间额外保留的完整 documents 正文集合。每个文件只维护一个最多
    ``chunk_size`` 字符的滑动窗口，同时保持旧 split_documents() 的切分边界。
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between 0 and chunk_size - 1")

    chunks = []
    step = chunk_size - overlap

    for filename in os.listdir(folder_path):
        if not filename.endswith(".txt"):
            continue

        with open(
            os.path.join(folder_path, filename),
            "r",
            encoding="utf-8",
        ) as file:
            buffer = ""
            reached_eof = False

            while True:
                while len(buffer) < chunk_size and not reached_eof:
                    text = file.read(chunk_size - len(buffer))
                    if text:
                        buffer += text
                    else:
                        reached_eof = True

                if not buffer:
                    break

                chunks.append({
                    "text": buffer[:chunk_size],
                    "source": filename,
                    "chunk_id": len(chunks) + 1,
                })

                # 即使已经到达 EOF，也继续按旧逻辑移动 start；这会保留旧实现
                # 在文件末尾可能产生的短 overlap chunk，而不是悄悄改变 chunk_id。
                if reached_eof and len(buffer) <= step:
                    break
                buffer = buffer[step:]

    return chunks


def build_faiss_index(
    chunks,
    model,
    batch_size=DEFAULT_EMBEDDING_BATCH_SIZE,
):
    """分批生成向量并按 chunk 顺序加入 IndexFlatL2。

    返回值继续保持 ``(index, vectors)`` 两项兼容形状，但第二项不再保留全量
    vectors，而是 ``None``。FAISS 自身已经持有向量，额外保留 NumPy 矩阵只会
    抬高 rebuild 的内存峰值，现有检索代码也没有使用它。
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    index = None

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        texts = [chunk["text"] for chunk in batch]
        vectors = np.asarray(model.encode(texts), dtype="float32")

        if index is None:
            index = faiss.IndexFlatL2(vectors.shape[1])

        # IndexFlatL2 支持重复 add；逐批加入仍保持 FAISS position 与 chunks
        # 的顺序一一对应，同时不需要完整 texts/vectors 临时副本。
        index.add(vectors)

    return index, None


def search(
    query,
    index,
    chunks,
    model,
    top_k=3,
    score_threshold=1.5
): # 把用户的查询转成向量, 在faiss索引中搜索最相似的文本块
    """负责 search 的函数职责。"""
    query_vector = model.encode([query])

    query_vector = np.array(query_vector).astype("float32")

    distances, indexes = index.search(query_vector, top_k)

    results = []

    for i in range(len(indexes[0])):
        distance = float(distances[0][i])

        if distance > score_threshold:
           continue

        chunk_index = indexes[0][i]
        if chunk_index == -1:
           continue

        results.append({
        "id": len(results) + 1,
        "chunk": chunks[chunk_index]["text"],
        "source": chunks[chunk_index]["source"],
        "distance": distance,
        "chunk_id": chunks[chunk_index]["chunk_id"]
    })

    return results


def _normalize_context_text(text):
    """负责 _normalize_context_text 的函数职责。"""
    return " ".join((text or "").split()).casefold()


def _shared_suffix_prefix_length(left, right):
    """负责 _shared_suffix_prefix_length 的函数职责。"""
    max_length = min(len(left), len(right))
    for length in range(max_length, 0, -1):
        if left[-length:] == right[:length]:
            return length
    return 0


def _is_near_duplicate_context(result, accepted_by_source):
    """只删除同源、几乎重复的相邻片段，避免 overlap 挤占 Context 预算。"""
    normalized = _normalize_context_text(result.get("chunk", ""))
    source = result.get("source") or ""
    previous = accepted_by_source.get(source)

    if not normalized or previous is None:
        return False, normalized

    previous_text, previous_chunk_id = previous
    if normalized == previous_text:
        return True, normalized

    current_chunk_id = result.get("chunk_id")
    if (
        isinstance(current_chunk_id, int)
        and isinstance(previous_chunk_id, int)
        and current_chunk_id == previous_chunk_id + 1
    ):
        overlap = _shared_suffix_prefix_length(previous_text, normalized)
        shorter_length = min(len(previous_text), len(normalized))
        if shorter_length and overlap / shorter_length >= 0.8:
            return True, normalized

    return False, normalized


def build_context(
    results,
    context_token_budget=DEFAULT_CONTEXT_TOKEN_BUDGET,
    return_results=False,
):
    """构造预算受限 Context，可选返回真正进入 Prompt 的来源列表。"""
    if not results:
        return ("", []) if return_results else ""

    context_parts = []
    context_results = []
    used_tokens = 0
    accepted_by_source = {}

    for result in results:
        is_duplicate, normalized = _is_near_duplicate_context(
            result,
            accepted_by_source,
        )
        if is_duplicate:
            continue

        context_part = f"Source {result['id']}:\n{result['chunk']}"
        part_tokens = estimate_tokens(context_part)

        if (
            context_token_budget is not None
            and used_tokens + part_tokens > context_token_budget
        ):
            break

        context_parts.append(context_part)
        context_results.append(result)
        used_tokens += part_tokens
        accepted_by_source[result.get("source") or ""] = (
            normalized,
            result.get("chunk_id"),
        )

    context = "\n\n".join(context_parts)
    return (context, context_results) if return_results else context


def build_history(history):
    """负责 build_history 的函数职责。"""
    if not history:
        return ""

    return "\n".join(
        [
            f"{item['role']}: {item['content']}"
            for item in history
        ]
    )


def build_prompt(
    query,
    results,
    history,
    prompt_name="default",
    source_type="local_kb",
    context=None,
):
    # RAG 主链路：检索结果 → 去重后的受预算 Context → Prompt → LLM。
    """负责 build_prompt 的函数职责。"""
    context = build_context(results) if context is None else context
    history_text = build_history(history)
    source_semantics = get_source_semantics(source_type)

    if not context:
        prompt_name = "empty"

    prompt_template = get_prompt_template(prompt_name)
    return prompt_template.format(
        question=query,
        context=context,
        history_text=history_text,
        **source_semantics,
    )


def generate_answer(
    query,
    results,
    client,
    history,
    model=None,
    temperature=None,
    max_tokens=None,
    prompt_name="default",
    source_type="local_kb",
    context=None,
): # 使用GPT-4.1-mini模型生成答案, 只使用搜索到的文本块作为上下文
    """负责 generate_answer 的函数职责。"""
    prompt = build_prompt(
        query,
        results,
        history,
        prompt_name,
        source_type=source_type,
        context=context,
    )

    completion_args = {
        "model": model or get_default_chat_model(),
        "temperature": (
            temperature
            if temperature is not None
            else get_default_temperature()
        ),
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    if max_tokens is not None:
        completion_args["max_tokens"] = max_tokens
    elif get_default_max_tokens() is not None:
        completion_args["max_tokens"] = get_default_max_tokens()

    response = client.chat.completions.create(**completion_args)

    return response.choices[0].message.content


def stream_answer(
    query,
    results,
    client,
    history,
    model=None,
    temperature=None,
    max_tokens=None,
    prompt_name="default",
    source_type="local_kb",
    context=None,
):
    """负责 stream_answer 的函数职责。"""
    prompt = build_prompt(
        query,
        results,
        history,
        prompt_name,
        source_type=source_type,
        context=context,
    )

    completion_args = {
        "model": model or get_default_chat_model(),
        "temperature": (
            temperature
            if temperature is not None
            else get_default_temperature()
        ),
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    if max_tokens is not None:
        completion_args["max_tokens"] = max_tokens
    elif get_default_max_tokens() is not None:
        completion_args["max_tokens"] = get_default_max_tokens()

    response = client.chat.completions.create(**completion_args)

    for chunk in response:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        token = getattr(delta, "content", None)

        if token:
            yield token

def main():
    """负责 main 的函数职责。"""
    documents = load_documents("documents") # 读取知识库文件

    load_dotenv()
    client = get_openai_client()

    chunks = split_documents(documents)
    model = SentenceTransformer(get_embedding_model_name()) # 使用更小的模型, 把文字转成向量

    index, _ = build_faiss_index(chunks, model)

    query = input("Ask a question: ")

    results = search(query, index, chunks, model)
    history = []
    try:
        answer = generate_answer(query, results, client, history)
        print("\nAnswer:")
        print(answer)
    except Exception as e:
        print("\n GPT answer failed:")
        print(e)

    for i, result in enumerate(results, start=1):
        print(f"Result {i}")
        print(f"Source: {result['source']}")
        print(f"Distance: {result['distance']:.4f}")
        print(result['chunk'])
        print()


if __name__ == "__main__":
    main()
