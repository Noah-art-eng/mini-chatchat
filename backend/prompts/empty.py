EMPTY_PROMPT = """
The knowledge base did not return any relevant context for this question.
Tell the user that the information is not found in the knowledge base.
Use conversation history only for continuity.
Do not answer from general knowledge.
Do not invent facts.

Conversation History:
{history_text}

Context:
{context}

Question:
{question}

Answer:
"""
