EMPTY_PROMPT = """
{empty_source_instruction}
{missing_instruction}
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
