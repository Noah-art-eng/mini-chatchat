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
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    return text


def split_documents(documents, chunk_size=300, overlap=50):
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


def build_faiss_index(chunks, model): # 把文本块转成向量, 然后建立faiss索引
    texts = [chunk["text"] for chunk in chunks]
    vectors = model.encode(texts)

    vectors = np.array(vectors).astype("float32")

    dimension = vectors.shape[1]

    index = faiss.IndexFlatL2(dimension)

    index.add(vectors)

    return index, vectors


def search(
    query,
    index,
    chunks,
    model,
    top_k=3,
    score_threshold=1.5
): # 把用户的查询转成向量, 在faiss索引中搜索最相似的文本块
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


def build_context(results, context_token_budget=DEFAULT_CONTEXT_TOKEN_BUDGET):
    if not results:
        return ""

    context_parts = []
    used_tokens = 0

    for result in results:
        context_part = f"Source {result['id']}:\n{result['chunk']}"
        part_tokens = estimate_tokens(context_part)

        if (
            context_token_budget is not None
            and used_tokens + part_tokens > context_token_budget
        ):
            break

        context_parts.append(context_part)
        used_tokens += part_tokens

    return "\n\n".join(context_parts)


def build_history(history):
    if not history:
        return ""

    return "\n".join(
        [
            f"{item['role']}: {item['content']}"
            for item in history
        ]
    )


def build_prompt(query, results, history, prompt_name="default"):
    context = build_context(results)
    history_text = build_history(history)

    if not results:
        prompt_name = "empty"

    prompt_template = get_prompt_template(prompt_name)
    return prompt_template.format(
        question=query,
        context=context,
        history_text=history_text
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
): # 使用GPT-4.1-mini模型生成答案, 只使用搜索到的文本块作为上下文
    prompt = build_prompt(query, results, history, prompt_name)

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
):
    prompt = build_prompt(query, results, history, prompt_name)

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
    documents = load_documents("documents") # 读取知识库文件

    load_dotenv()
    client = get_openai_client()

    chunks = split_documents(documents)
    model = SentenceTransformer(get_embedding_model_name()) # 使用更小的模型, 把文字转成向量

    index, vectors = build_faiss_index(chunks, model)

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
