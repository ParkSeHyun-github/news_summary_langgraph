"""DuckDuckGo 뉴스 검색 — API 키 불필요."""
from ddgs import DDGS


def fetch_search(query: str, max_results: int = 10) -> list[dict]:
    articles = []
    try:
        results = DDGS().news(query, max_results=max_results)
        for r in results:
            articles.append({
                "title": r.get("title", ""),
                "content": r.get("body", "")[:2000],
                "source": "search",
                "source_name": r.get("source", "DuckDuckGo"),
                "url": r.get("url"),
                "published": r.get("date"),
            })
    except Exception as e:
        print(f"[Search] DuckDuckGo 검색 실패: {e}")
    return articles
