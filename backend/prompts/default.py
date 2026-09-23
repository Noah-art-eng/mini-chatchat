DEFAULT_PROMPT = """
{source_instruction}
If the context does not contain the answer, {missing_instruction}
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
