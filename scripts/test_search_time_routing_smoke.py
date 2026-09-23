import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from agent_service import choose_tool_without_llm  # noqa: E402
from rag import build_prompt  # noqa: E402
from services.tools.current_time import execute_current_time  # noqa: E402


FORBIDDEN_TEXT = (
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "invalid_api_key",
    "OpenAI 401",
)


def pass_step(message):
    """负责 pass_step 的函数职责。"""
    print(f"[PASS] {message}")


def fail_step(message):
    """负责 fail_step 的函数职责。"""
    print(f"[FAIL] {message}")
    sys.exit(1)


def assert_safe_text(text, step_name):
    """负责 assert_safe_text 的函数职责。"""
    lowered = text.lower()
    for forbidden in FORBIDDEN_TEXT:
        if forbidden.lower() in lowered:
            fail_step(f"{step_name}: forbidden text found: {forbidden}")


def assert_true(condition, message):
    """负责 assert_true 的函数职责。"""
    if not condition:
        fail_step(message)


def sample_results():
    """负责 sample_results 的函数职责。"""
    return [
        {
            "id": 1,
            "chunk": "Docker is a container platform.",
            "source": "sample_rag.txt",
            "chunk_id": 1,
            "distance": 0.1,
        }
    ]


def check_prompt_semantics():
    """负责 check_prompt_semantics 的函数职责。"""
    local_prompt = build_prompt(
        "What is Docker?",
        sample_results(),
        [],
        source_type="local_kb",
    )
    temp_prompt = build_prompt(
        "What is Docker?",
        sample_results(),
        [],
        source_type="temp_kb",
    )
    search_prompt = build_prompt(
        "OpenAI recent updates",
        [
            {
                "id": 1,
                "chunk": "OpenAI announced a public update.",
                "source": "https://example.com/openai",
                "chunk_id": 1,
                "distance": 0,
            }
        ],
        [],
        source_type="search_engine",
    )

    assert_safe_text(local_prompt, "local prompt")
    assert_safe_text(temp_prompt, "temp prompt")
    assert_safe_text(search_prompt, "search prompt")

    assert_true(
        "local knowledge base" in local_prompt,
        "local_kb prompt missing local knowledge base source semantics",
    )
    assert_true(
        "temporary file" in temp_prompt,
        "temp_kb prompt missing temporary file source semantics",
    )
    assert_true(
        "web search results" in search_prompt,
        "search_engine prompt missing web search source semantics",
    )
    assert_true(
        "knowledge base" not in search_prompt.lower(),
        "search_engine prompt should not mention knowledge base",
    )

    pass_step("Prompt source semantics")


def check_current_time_default():
    """负责 check_current_time_default 的函数职责。"""
    result = execute_current_time({}).to_dict()
    assert_true(result["ok"], "current_time default returned ok=false")
    payload = result.get("result") or {}
    assert_true(payload.get("utc"), "current_time default missing utc")
    assert_true(payload.get("local"), "current_time default missing local")
    assert_true(
        payload.get("iso_datetime"),
        "current_time default missing iso_datetime",
    )
    pass_step("current_time default compatibility")


def check_current_time_timezone(timezone_name):
    """负责 check_current_time_timezone 的函数职责。"""
    result = execute_current_time({"timezone": timezone_name}).to_dict()
    assert_safe_text(str(result), f"current_time {timezone_name}")
    assert_true(result["ok"], f"current_time {timezone_name} returned ok=false")
    payload = result.get("result") or {}
    assert_true(
        payload.get("timezone") == timezone_name,
        f"current_time timezone mismatch for {timezone_name}",
    )
    assert_true(
        payload.get("iso_datetime"),
        f"current_time {timezone_name} missing iso_datetime",
    )
    assert_true(
        payload.get("utc_offset"),
        f"current_time {timezone_name} missing utc_offset",
    )
    print(
        f"{timezone_name} summary="
        f"{payload.get('readable_datetime')} {payload.get('utc_offset')}"
    )
    pass_step(f"current_time timezone {timezone_name}")


def check_current_time_invalid_timezone():
    """负责 check_current_time_invalid_timezone 的函数职责。"""
    result = execute_current_time({"timezone": "Mars/Colony"}).to_dict()
    assert_safe_text(str(result), "current_time invalid timezone")
    assert_true(not result["ok"], "invalid timezone should return ok=false")
    assert_true(
        "unknown timezone" in (result.get("error") or ""),
        "invalid timezone missing readable error",
    )
    pass_step("current_time invalid timezone")


def check_agent_routing():
    """负责 check_agent_routing 的函数职责。"""
    tools = [
        {"name": "current_time"},
        {"name": "browser_search"},
        {"name": "kb_search"},
    ]

    time_call = choose_tool_without_llm("新西兰现在几点", tools)
    assert_true(
        time_call.get("tool") == "current_time",
        f"expected current_time, got {time_call}",
    )
    assert_true(
        time_call.get("arguments", {}).get("timezone") == "Pacific/Auckland",
        f"expected Pacific/Auckland, got {time_call}",
    )

    news_call = choose_tool_without_llm("今天 OpenAI 有什么新闻", tools)
    assert_true(
        news_call.get("tool") == "browser_search",
        f"expected browser_search, got {news_call}",
    )

    kb_call = choose_tool_without_llm("总结知识库中的 Docker 文档", tools)
    assert_true(
        kb_call.get("tool") == "kb_search",
        f"expected kb_search, got {kb_call}",
    )

    pass_step("Agent deterministic routing")


def main():
    """负责 main 的函数职责。"""
    check_prompt_semantics()
    check_current_time_default()
    check_current_time_timezone("Pacific/Auckland")
    check_current_time_timezone("Asia/Shanghai")
    check_current_time_timezone("UTC")
    check_current_time_invalid_timezone()
    check_agent_routing()
    pass_step("Search/time routing smoke test complete")


if __name__ == "__main__":
    main()
