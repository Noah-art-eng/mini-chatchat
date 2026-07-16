STRICT_PROMPT = """
Answer the question strictly using only the provided context.
If the answer is not directly supported by the context, say that the information is not found in the knowledge base.
Use conversation history only for continuity.
Do not use outside knowledge.
Do not infer facts that are not stated in the context.

Conversation History:
{history_text}

Context:
{context}

Question:
{question}

Answer:
"""
