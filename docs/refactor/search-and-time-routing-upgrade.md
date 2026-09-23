# Search Accuracy & Smart Routing Upgrade

Date: 2026-08-04

## 1. Original Problem

Search mode was correctly sending `mode: "search_engine"` and returning URL sources, but answers could still say phrases equivalent to “according to the knowledge base.” This made web search answers look like local KB answers.

A second issue was routing: questions such as “新西兰现在几点” are real-time clock questions. Web search can provide pages, snippets, or timezone rules, but it is not the most reliable mechanism for the actual current time. Agent mode should prefer the `current_time` tool for those questions.

## 2. Frontend Mode Investigation

The previous Network investigation confirmed the React mode wiring is correct:

- `ChatModeControls` selected `chat-mode-search-engine`.
- Search mode status was visible.
- `useChatStream` sent `/kb_chat` with `mode: "search_engine"`.
- The payload did not include `kb_name`.
- SSE sources were web URLs.

No frontend mode wiring change was required.

## 3. Prompt Root Cause

The root cause was in backend prompt construction:

- `backend/rag.py` used one prompt template for all RAG modes.
- `backend/prompts/default.py`, `strict.py`, and `empty.py` hard-coded knowledge-base missing-context language.
- `chat_service.py` did not pass the current retrieval mode into prompt construction.

The fix moves source semantics into prompt construction instead of replacing strings after answer generation.

## 4. RAG Mode Source Semantics

`rag.build_prompt()`, `generate_answer()`, and `stream_answer()` now accept `source_type`.

Current source semantics:

- `local_kb`: answer from local knowledge base materials.
- `temp_kb`: answer from the temporary file uploaded by the user for this chat.
- `search_engine`: answer from web search results and describe sources as web results/pages.

## 5. Search Pipeline

Search mode still follows the existing flow:

```text
User query
↓
search_web()
↓
DDGS text search
↓
title / href / body snippet
↓
RAG prompt context
↓
LLM answer
↓
SSE sources/token/done
```

The search adapter was not replaced.

## 6. Search Current Limits

`backend/services/search_service.py` currently returns:

- `title`
- `source` URL
- `chunk` built from title + snippet/body
- `distance = 0`
- `chunk_id`

It does not fetch full page content. Context is based on search result snippets. This is acceptable for this phase, but means search mode should be careful with real-time values and conflicting/partial results.

## 7. current_time Original Capability

Before this change, `current_time` returned:

- UTC ISO time
- server local ISO time
- server local timezone metadata

It did not accept timezone input.

## 8. current_time Enhancement

`current_time` now accepts optional:

```json
{
  "timezone": "Pacific/Auckland"
}
```

The implementation uses Python standard library `zoneinfo`.

Returned fields now include:

- `utc`
- `local`
- `timezone`
- `iso_datetime`
- `readable_datetime`
- `utc_offset`

Invalid timezone strings return `ok=false` with a readable error. No guessed or fabricated timezone is returned.

## 9. Timezone Mapping Strategy

The Agent deterministic router uses a deliberately small mapping:

- `新西兰`, `奥克兰`, `Auckland` -> `Pacific/Auckland`
- `中国`, `北京`, `Shanghai`, `Beijing` -> `Asia/Shanghai`
- `UTC` -> `UTC`

No large city database was added. Unknown locations are not guessed.

## 10. Agent Routing Adjustment

Agent tool-selection prompt and deterministic fallback were updated.

The router now prefers:

- `current_time` for clock/date questions such as “现在几点”, “当前时间”, “今天几号”, “今天星期几”, `time now`, `current date`, `current time`.
- `browser_search` for latest news, public web updates, current product prices, recent releases, current events, and explicit web search.
- `kb_search` for local KB, uploaded materials, and project document questions.

If the LLM chooses `current_time` but omits timezone, `apply_tool_defaults()` injects the limited timezone mapping when the query clearly contains one.

## 11. Compatibility

No API contract changed.

Unchanged:

- `/kb_chat` request shape
- SSE event contract
- local KB retrieval
- temp KB retrieval
- search adapter response shape
- FAISS/BM25/hybrid search
- reranker
- metadata filters
- Agent endpoint payloads
- Tool IDs
- database schema

## 12. Test Results

New deterministic smoke:

```bash
.venv/bin/python scripts/test_search_time_routing_smoke.py
```

Result: PASS

Covered:

- local prompt source semantics
- temp prompt source semantics
- search prompt source semantics
- search prompt avoids knowledge-base wording
- current_time default compatibility
- `Pacific/Auckland`
- `Asia/Shanghai`
- `UTC`
- invalid timezone
- deterministic Agent routing for current_time / browser_search / kb_search

Relevant smoke tests:

- `test_tool_registry_smoke.py`: PASS
- `test_agent_tool_calling_smoke.py`: PASS
- `test_browser_search_tool_smoke.py`: PASS
- `test_temp_kb_api_smoke.py`: PASS

Unified runner:

```bash
.venv/bin/python scripts/run_smoke_tests.py
```

Result: PASS, 26 scripts, total elapsed 105.6s.

## 13. Browser Network Evidence

Search mode request:

```json
{
  "mode": "search_engine",
  "query": "OpenAI 最近有什么公开更新？",
  "stream": true,
  "conversation_id": 725,
  "top_k": 3,
  "score_threshold": 0.8,
  "prompt_name": "default",
  "rerank": false,
  "rerank_top_n": 3
}
```

Search sources were web URLs, including:

- `https://openai.com/products/release-notes/`
- `https://openai.com/zh-Hans-CN/news/product-releases/`

Search time question response used web wording:

> 根据联网检索结果...

It did not claim the answer came from the local KB and did not fabricate a real-time minute when snippets were insufficient.

Agent mode request:

```json
{
  "query": "新西兰现在几点？",
  "kb_name": "default",
  "tools": [
    "calculator",
    "current_time",
    "kb_search",
    "sqlite_readonly_query",
    "filesystem_readonly_read",
    "browser_read",
    "browser_search"
  ],
  "conversation_id": 725,
  "max_steps": 3
}
```

Agent selected `current_time` with:

```json
{
  "timezone": "Pacific/Auckland"
}
```

## 14. Known Limits

- Search mode still uses search snippets, not full web page body.
- Search mode should not be treated as a precise clock or live market data tool.
- Agent timezone mapping is intentionally small.
- Unknown locations should be clarified by UX or future Agent behavior instead of guessed.
- Frontend could later show a non-blocking hint in Search mode: real-time clock/date questions are better handled by Agent current_time.

## 15. Follow-up Suggestions

- Add a small frontend hint for Search mode time/date questions.
- Consider safe optional search enrichment with `browser_read` only after separate design and tests.
- Add `/chat/:conversationId` deep links separately from routing logic.
