from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv
import os
from pypdf import PdfReader

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


def generate_answer(query, results, client, history): # 使用GPT-4.1-mini模型生成答案, 只使用搜索到的文本块作为上下文
    context = "\n\n".join(
    [
        f"Source {result['id']}:\n{result['chunk']}"
        for result in results
    ]

)
    history_text = "\n".join(
    [
        f"{item['role']}: {item['content']}"
        for item in history
    ]
)
    prompt = f"""
Use the conversation history and context below.

Conversation History:
{history_text}

Context:
{context}

Question:
{query}

Answer:
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content

def main():
    documents = load_documents("documents") # 读取知识库文件

    load_dotenv()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    chunks = split_documents(documents)
    model = SentenceTransformer("all-MiniLM-L6-v2") # 使用更小的模型, 把文字转成向量

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