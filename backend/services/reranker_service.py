import numpy as np


def _normalize_vectors(vectors):
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return vectors / norms


def rerank_docs(query, docs, model, top_n=3):
    if not query or not docs or model is None:
        return docs

    top_n = max(1, int(top_n or 3))
    chunks = [doc.get("chunk", "") for doc in docs]

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
        key=lambda item: item.get("rerank_score", 0),
        reverse=True
    )

    return ranked_docs[:top_n]
