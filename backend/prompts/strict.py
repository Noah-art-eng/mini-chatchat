STRICT_PROMPT = """
{source_instruction}
If the answer is not directly supported by the context, {missing_instruction}
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
