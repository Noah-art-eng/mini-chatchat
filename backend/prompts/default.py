DEFAULT_PROMPT = """
Answer the question using the provided context.
If the context does not contain the answer, say that the information is not found in the knowledge base.
Use conversation history only for continuity.
Do not invent facts.

Conversation History:
{history_text}

Context:
{context}

Question:
{question}

Answer:
"""
