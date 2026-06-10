import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (NewsBot/1.0)"}


def fetch_url(urls: list[str]) -> list[dict]:
    articles = []

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            body = soup.find("article") or soup.find("main") or soup.find("body")
            paragraphs = body.find_all("p") if body else []
            content = " ".join(p.get_text(strip=True) for p in paragraphs)

            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else url

            articles.append({
                "title": title,
                "content": content[:3000],
                "source": "url",
                "source_name": url,
                "url": url,
                "published": None,
            })
        except Exception as e:
            print(f"[URL] {url} 수집 실패: {e}")

    return articles
