from ddgs import DDGS


def search_web(query, top_k=3):
    results = []

    try:
        with DDGS() as ddgs:
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
