import numpy as np


def _normalize_vectors(vectors):
    """把向量转成单位长度，使后面的点积等价于余弦相似度。"""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return vectors / norms


def rerank_docs(query, docs, model, top_n=3):
    """对粗检索候选做第二次相关性排序。

    `run_kb_chat()` 把用户问题和候选文本块交给这里。问题与文本块使用同一个
    embedding 模型编码，再按余弦相似度排序并保留 top_n 条；完成后回到
    `run_kb_chat()` 继续构建 Context。
    """
    if not query or not docs or model is None:
        return docs

    top_n = max(1, int(top_n or 3))
    chunks = [doc.get("chunk", "") for doc in docs]

    # 使用归一化向量的点积（余弦相似度）对初检索候选重新排序。
    query_vector = model.encode([query])
    doc_vectors = model.encode(chunks)

    query_vector = np.array(query_vector).astype("float32")
    doc_vectors = np.array(doc_vectors).astype("float32")

    query_vector = _normalize_vectors(query_vector)
    doc_vectors = _normalize_vectors(doc_vectors)

    scores = np.dot(doc_vectors, query_vector[0])

    ranked_docs = []
    for doc, score in zip(docs, scores):
        ranked_doc = dict(doc)
        ranked_doc["rerank_score"] = float(score)
        ranked_docs.append(ranked_doc)

    ranked_docs.sort(
        key=lambda item: item["rerank_score"],
        reverse=True
    )

    return ranked_docs[:top_n]
