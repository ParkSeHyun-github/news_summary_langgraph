import feedparser
from django.conf import settings


def fetch_rss(feed_urls: list[str]) -> list[dict]:
    max_per_feed = settings.NEWSBOT.get("MAX_ARTICLES_PER_FEED", 5)
    articles = []

    for url in feed_urls:
        try:
            feed = feedparser.parse(url)
            source_name = feed.feed.get("title", url)
            for entry in feed.entries[:max_per_feed]:
                content = (
                    entry.get("summary", "")
                    or entry.get("description", "")
                    or (entry.get("content") or [{}])[0].get("value", "")
                )
                articles.append({
                    "title": entry.get("title", "제목 없음"),
                    "content": content[:2000],
                    "source": "rss",
                    "source_name": source_name,
                    "url": entry.get("link"),
                    "published": entry.get("published"),
                })
        except Exception as e:
            print(f"[RSS] {url} 수집 실패: {e}")

    return articles
