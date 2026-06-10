"""
LangGraph 노드 함수.
django.conf.settings 에서 설정을 읽으므로 DJANGO_SETTINGS_MODULE 이 설정된 후 임포트해야 합니다.
"""
import json
import time
import re
from django.conf import settings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from apps.news.sources.rss import fetch_rss
from apps.news.sources.pdf import fetch_pdf
from apps.news.sources.url import fetch_url
from apps.news.sources.search import fetch_search
from apps.news.graph.state import NewsState

_llm: BaseChatModel | None = None


def get_llm() -> BaseChatModel:
    global _llm
    if _llm is None:
        provider = settings.NEWSBOT.get("LLM_PROVIDER", "groq")

        if provider == "groq":
            from langchain_groq import ChatGroq
            _llm = ChatGroq(
                model=settings.NEWSBOT.get("LLM_MODEL", "llama-3.3-70b-versatile"),
                temperature=0,
            )
        elif provider == "ollama":
            from langchain_ollama import ChatOllama
            _llm = ChatOllama(
                model=settings.NEWSBOT.get("LLM_MODEL", "llama3.2"),
                temperature=0,
            )
        else:  # anthropic
            from langchain_anthropic import ChatAnthropic
            _llm = ChatAnthropic(
                model=settings.NEWSBOT.get("LLM_MODEL", "claude-haiku-4-5-20251001"),
                temperature=0,
            )
    return _llm


def llm_invoke(messages: list[BaseMessage], max_retries: int = 4) -> BaseMessage:
    """Rate limit 발생 시 자동 재시도 (최대 4회, 지수 백오프)."""
    for attempt in range(max_retries):
        try:
            return get_llm().invoke(messages)
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit" in err.lower() or "rate limit" in err.lower():
                # 에러 메시지에서 대기 시간 파싱 (없으면 기본값 사용)
                wait_match = re.search(r"try again in ([\d.]+)s", err)
                wait = float(wait_match.group(1)) + 1 if wait_match else (2 ** attempt) * 5
                print(f"  [LLM] Rate limit — {wait:.0f}초 후 재시도 ({attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
    return get_llm().invoke(messages)


# ── 병렬 페치 노드 ────────────────────────────────────────────

def _select_rss_feeds(query: str, user_feeds: list[str]) -> list[str]:
    """쿼리 키워드로 관련 카테고리 RSS 피드 자동 선택."""
    if user_feeds:
        return user_feeds

    feeds_by_cat = settings.NEWSBOT.get("RSS_FEEDS_BY_CATEGORY", {})
    cat_keywords  = settings.NEWSBOT.get("CATEGORY_KEYWORDS", {})
    query_lower   = query.lower()

    matched_categories: list[str] = []
    for category, keywords in cat_keywords.items():
        if any(kw in query_lower for kw in keywords):
            matched_categories.append(category)

    # 매칭된 카테고리가 없으면 general 사용
    if not matched_categories:
        matched_categories = ["general"]

    feeds: list[str] = []
    for cat in matched_categories:
        feeds.extend(feeds_by_cat.get(cat, []))

    print(f"  [RSS] 선택된 카테고리: {matched_categories}")
    return feeds


def fetch_rss_node(state: NewsState) -> dict:
    feeds = _select_rss_feeds(state.get("query", ""), state.get("rss_feeds", []))
    articles = fetch_rss(feeds)
    print(f"  [RSS] {len(articles)}건")
    return {"articles": articles}


def fetch_pdf_node(state: NewsState) -> dict:
    articles = fetch_pdf(state.get("pdf_paths", []))
    print(f"  [PDF] {len(articles)}건")
    return {"articles": articles}


def fetch_url_node(state: NewsState) -> dict:
    articles = fetch_url(state.get("urls", []))
    print(f"  [URL] {len(articles)}건")
    return {"articles": articles}


def fetch_search_node(state: NewsState) -> dict:
    """쿼리 기반 DuckDuckGo 뉴스 검색 — 항상 실행되는 핵심 소스."""
    query = state.get("query", "")
    articles = fetch_search(query, max_results=10)
    print(f"  [Search] '{query}' → {len(articles)}건")
    return {"articles": articles}


# ── 집계 노드 ─────────────────────────────────────────────────

def aggregate_node(state: NewsState) -> dict:
    query = state.get("query", "").lower()
    query_keywords = set(query.split())

    seen: set = set()
    all_articles = []
    for a in state.get("articles", []):
        key = a.get("url") or a["title"]
        if key not in seen:
            seen.add(key)
            all_articles.append(a)

    # source=search 기사는 무조건 유지, 나머지는 쿼리 관련성 필터링
    def is_relevant(article: dict) -> bool:
        if article["source"] in ("search", "pdf"):
            return True
        text = (article["title"] + " " + article["content"]).lower()
        return any(kw in text for kw in query_keywords)

    relevant = [a for a in all_articles if is_relevant(a)]

    # 관련 기사가 너무 적으면 전체 유지 (쿼리가 너무 광범위한 경우)
    if len(relevant) < 3:
        relevant = all_articles

    print(f"  [Aggregate] 전체 {len(all_articles)}건 → 관련 {len(relevant)}건")
    return {"articles": relevant}


# ── 요약 노드 ─────────────────────────────────────────────────

def summarize_node(state: NewsState) -> dict:
    articles = state.get("articles", [])
    query = state.get("query", "")

    if not articles:
        return {"summary": "수집된 기사가 없습니다.", "confidence_score": 0.0}

    articles_text = "\n\n".join(
        f"[{i+1}] {a['source_name']} ({a['source']})\n"
        f"제목: {a['title']}\n내용: {a['content'][:500]}"
        for i, a in enumerate(articles[:15])
    )

    response = llm_invoke([
        SystemMessage(content=(
            "당신은 전문 뉴스 분석가입니다. "
            "반드시 주어진 주제와 직접 관련된 내용만 요약하세요. "
            "주제와 무관한 기사는 완전히 무시하세요."
        )),
        HumanMessage(content=(
            f"검색 주제: {query}\n\n"
            f"수집된 기사:\n{articles_text}\n\n"
            f"위 기사 중 '{query}'와 직접 관련된 내용만 골라 다음을 작성하세요:\n"
            "1. 핵심 요약 (3~5문장)\n"
            "2. 주요 팩트 (bullet)\n"
            "3. 출처별 관점 차이 (있다면)\n\n"
            "주제와 무관한 기사(예: 주제가 날씨인데 AI 기사 등)는 절대 포함하지 마세요.\n"
            '마지막 줄에 신뢰도 JSON: {"confidence": 0.0~1.0}'
        )),
    ])

    text = response.content
    confidence = 0.7
    try:
        last = text.strip().split("\n")[-1]
        confidence = float(json.loads(last).get("confidence", 0.7))
        text = text[: text.rfind(last)].strip()
    except Exception:
        pass

    print(f"  [Summarize] 완료 (신뢰도 {confidence:.2f})")
    return {"summary": text, "confidence_score": confidence}


# ── 충돌 감지 노드 ────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """LLM 응답에서 JSON 블록을 최대한 추출."""
    import re
    # 코드블록 안 JSON 우선
    block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if block:
        return json.loads(block.group(1))
    # 중괄호 범위 탐색 (가장 바깥쪽)
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(text[start:end])
    raise ValueError("JSON 없음")


def conflict_detect_node(state: NewsState) -> dict:
    articles  = state.get("articles", [])
    iteration = state.get("iteration_count", 0)
    max_iter  = state.get("max_iterations", settings.NEWSBOT.get("MAX_FACT_CHECK_ITERATIONS", 2))

    # 기사가 3건 미만이거나 루프 한도 초과면 스킵
    if len(articles) < 3 or iteration >= max_iter:
        return {"conflicts": [], "needs_fact_check": False, "iteration_count": iteration}

    articles_text = "\n\n".join(
        f"[{i+1}] {a['source_name']}: {a['title']}\n{a['content'][:300]}"
        for i, a in enumerate(articles[:10])
    )

    response = llm_invoke([
        SystemMessage(content=(
            "당신은 팩트체커입니다. 반드시 JSON만 반환하고 다른 텍스트는 쓰지 마세요."
        )),
        HumanMessage(content=(
            f"아래 기사들 사이에 사실 충돌이 있는지 분석하세요.\n\n"
            f"{articles_text}\n\n"
            "반드시 아래 형식의 JSON만 반환:\n"
            "{\n"
            '  "has_conflict": true,\n'
            '  "conflicts": [\n'
            '    {"topic": "충돌 주제", "claim_a": "주장A", "claim_b": "주장B", '
            '"source_a": "출처A", "source_b": "출처B"}\n'
            "  ]\n"
            "}"
        )),
    ])

    conflicts, needs_check = [], False
    try:
        data = _extract_json(response.content)
        needs_check = bool(data.get("has_conflict", False))
        conflicts   = [c for c in data.get("conflicts", []) if c.get("topic")]
    except Exception as e:
        print(f"  [ConflictDetect] 파싱 실패: {e}\n  원문: {response.content[:200]}")
        # 파싱 실패 시 기사가 많으면 팩트체크 강제 실행
        needs_check = len(articles) >= 5

    print(f"  [ConflictDetect] 충돌 {len(conflicts)}건, 팩트체크 필요: {needs_check}")
    return {"conflicts": conflicts, "needs_fact_check": needs_check, "iteration_count": iteration}


# ── 팩트체크 노드 ─────────────────────────────────────────────

def fact_check_node(state: NewsState) -> dict:
    conflicts  = state.get("conflicts", [])
    articles   = state.get("articles", [])
    summary    = state.get("summary", "")
    iteration  = state.get("iteration_count", 0)

    all_content = "\n".join(f"{a['source_name']}: {a['content'][:400]}" for a in articles)

    # 충돌이 있으면 충돌 검증, 없으면 핵심 주장 사실 여부 검증
    if conflicts:
        conflict_text = "\n".join(
            f"- {c['topic']}: {c['source_a']}={c['claim_a']} / {c['source_b']}={c['claim_b']}"
            for c in conflicts
        )
        check_target = f"다음 충돌 사항을 검증하세요:\n{conflict_text}"
    else:
        check_target = (
            f"아래 요약의 주요 사실들이 수집된 기사와 일치하는지 검증하세요:\n{summary[:800]}"
        )

    response = llm_invoke([
        SystemMessage(content="팩트체커입니다. 반드시 JSON 배열만 반환하세요."),
        HumanMessage(content=(
            f"{check_target}\n\n"
            f"참고 기사:\n{all_content[:3000]}\n\n"
            "반드시 아래 형식의 JSON 배열만 반환:\n"
            '[{"topic": "주제", "verdict": "정확/부정확/불확실", '
            '"evidence": "근거 한 문장", "resolved": true}]'
        )),
    ])

    results = []
    try:
        text = response.content
        # 코드블록 제거 후 배열 추출
        import re
        block = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
        raw = block.group(1) if block else text[text.find("["):text.rfind("]") + 1]
        results = json.loads(raw)
    except Exception as e:
        print(f"  [FactCheck] 파싱 실패: {e}")

    print(f"  [FactCheck] {len(results)}건 검증 (iteration {iteration + 1})")
    return {"fact_check_results": results, "iteration_count": iteration + 1}


# ── 최종 요약 노드 ────────────────────────────────────────────

def finalize_node(state: NewsState) -> dict:
    summary = state.get("summary", "")
    conflicts = state.get("conflicts", [])
    fact_results = state.get("fact_check_results", [])
    query = state.get("query", "")

    if not conflicts:
        return {"final_summary": f"# {query} — 뉴스 요약\n\n{summary}"}

    fact_text = "\n".join(
        f"- {r.get('topic')}: {r.get('verdict')} ({r.get('evidence','')})"
        for r in fact_results
    )

    response = llm_invoke([
        SystemMessage(content="팩트체크 결과를 반영해 최종 요약을 작성합니다."),
        HumanMessage(content=(
            f"초벌 요약:\n{summary}\n\n팩트체크 결과:\n{fact_text}\n\n"
            "팩트체크를 반영한 최종 요약을 작성하세요. 수정 부분에 '※ 수정:' 표시를 붙이세요."
        )),
    ])

    print("  [Finalize] 팩트체크 반영 완료")
    return {"final_summary": f"# {query} — 뉴스 요약 (팩트체크 완료)\n\n{response.content}"}
