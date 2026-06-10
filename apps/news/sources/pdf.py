import os


def fetch_pdf(pdf_paths: list[str]) -> list[dict]:
    articles = []

    for path in pdf_paths:
        if not os.path.exists(path):
            print(f"[PDF] 파일 없음: {path}")
            continue
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            filename = os.path.basename(path)
            articles.append({
                "title": filename,
                "content": text[:3000],
                "source": "pdf",
                "source_name": filename,
                "url": None,
                "published": None,
            })
        except Exception as e:
            print(f"[PDF] {path} 파싱 실패: {e}")

    return articles
