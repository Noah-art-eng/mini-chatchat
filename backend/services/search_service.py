import logging

from ddgs import DDGS


SEARCH_TIMEOUT_SECONDS = 10
logger = logging.getLogger("mini-chatchat")


def search_web(query, top_k=3):
    """执行联网搜索并转换成与知识库文本块相近的结果结构。

    chat_service 和 Agent 可以因此复用后续结果处理。外部服务失败时返回空列表，
    让上层按“没有搜索结果”继续，而不是泄露搜索库异常。
    """
    results = []

    try:
        # 搜索工具使用独立超时，避免外部搜索服务拖住 Agent 工作线程。
        with DDGS(timeout=SEARCH_TIMEOUT_SECONDS) as ddgs:
            search_results = ddgs.text(
                query,
                max_results=top_k
            )
    except Exception as exc:
        logger.warning("Web search failed: %s", exc)
        return []

    for index, item in enumerate(search_results[:top_k], start=1):
        title = item.get("title") or ""
        source = item.get("href") or item.get("url") or ""
        body = item.get("body") or item.get("snippet") or ""

        chunk = body
        if title:
            chunk = f"{title}\n{body}"

        results.append({
            "id": index,
            "chunk": chunk,
            "source": source,
            "title": title,
            "distance": 0,
            "chunk_id": index
        })

    return results
