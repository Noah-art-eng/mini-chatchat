from ddgs import DDGS


SEARCH_TIMEOUT_SECONDS = 10


def search_web(query, top_k=3):
    """负责 search_web 的函数职责。"""
    results = []

    try:
        # 搜索工具使用独立超时，避免外部搜索服务拖住 Agent 工作线程。
        with DDGS(timeout=SEARCH_TIMEOUT_SECONDS) as ddgs:
            search_results = ddgs.text(
                query,
                max_results=top_k
            )
    except Exception as e:
        print(f"[SearchService] web search failed: {e}")
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
