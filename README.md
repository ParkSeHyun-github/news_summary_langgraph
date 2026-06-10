# 📰 멀티소스 뉴스 요약봇

여러 출처(RSS, PDF, URL)를 **동시에** 수집하고, 기사 간 정보 충돌을 감지하면 자동으로 팩트체크를 수행해 신뢰도 높은 요약을 생성하는 Django + LangGraph 프로젝트입니다.

---

## 핵심 기능

| 기능 | 설명 |
|------|------|
| 멀티소스 병렬 수집 | RSS 피드, 웹 URL, PDF 파일을 동시에 수집 |
| 충돌 감지 | 출처 간 상충하는 주장을 LLM이 자동 탐지 |
| 팩트체크 루프 | 충돌 발견 시 추가 검증 후 재평가 (최대 2회) |
| 신뢰도 점수 | 요약의 신뢰도를 0.0 ~ 1.0으로 수치화 |
| 웹 UI + CLI | Django 웹 인터페이스 및 `manage.py` 커맨드 동시 지원 |
| 결과 영속화 | Django ORM으로 보고서·기사·충돌 기록을 SQLite에 저장 |

---

## LangGraph 구조

```
START
  ├─► fetch_rss_node  ─┐
  ├─► fetch_pdf_node  ─┤  (병렬 실행)
  └─► fetch_url_node  ─┘
              │
         aggregate_node      (중복 제거)
              │
         summarize_node      (초벌 요약 + 신뢰도)
              │
      conflict_detect_node   (충돌 감지 + 분기 판단)
         /           \
   (충돌 없음)    (충돌 있음)
        │               ↓
        │         fact_check_node  ──┐
        │               │           │ 루프 (max 2회)
        │         conflict_detect ◄─┘
        │
    finalize_node          (최종 요약 완성)
              │
             END
```

`python manage.py generate_graph` 를 실행하면 위 구조를 **graph.png** 파일로 저장합니다.

```bash
uv run python manage.py generate_graph
uv run python manage.py generate_graph --output my_graph.png
```

---

## LangGraph 포인트별 구현 위치

### 1. 병렬 노드 실행

> **"여러 출처를 동시에 수집한다"**

```
apps/news/graph/state.py   → articles 필드 정의
apps/news/graph/builder.py → 병렬 엣지 연결
apps/news/graph/nodes.py   → fetch_rss_node / fetch_pdf_node / fetch_url_node
```

병렬 실행의 핵심은 **State 설계**입니다. 세 노드가 동시에 `articles` 리스트에 쓸 수 있도록 `Annotated + operator.add`를 사용했습니다.

```python
# apps/news/graph/state.py
class NewsState(TypedDict):
    articles: Annotated[list[dict], operator.add]  # ← 각 노드가 독립적으로 append
```

그래프에서 `START → fetch_rss`, `START → fetch_pdf`, `START → fetch_url` 세 엣지를 동시에 연결하면 LangGraph가 자동으로 병렬 실행합니다.

```python
# apps/news/graph/builder.py
builder.add_edge(START, "fetch_rss")
builder.add_edge(START, "fetch_pdf")   # 세 엣지가 동시 출발
builder.add_edge(START, "fetch_url")

builder.add_edge("fetch_rss", "aggregate")
builder.add_edge("fetch_pdf", "aggregate")  # 셋 모두 끝나야 aggregate 실행
builder.add_edge("fetch_url", "aggregate")
```

실제 수집 로직은 출처별로 분리되어 있습니다.

```
apps/news/sources/rss.py  → feedparser로 RSS 수집
apps/news/sources/url.py  → requests + BeautifulSoup으로 웹 크롤링
apps/news/sources/pdf.py  → pypdf로 PDF 텍스트 추출
```

---

### 2. 신뢰도 판단 분기 (Conditional Edge)

> **"충돌이 있으면 팩트체크, 없으면 바로 완료"**

```
apps/news/graph/builder.py → add_conditional_edges 정의
apps/news/graph/nodes.py   → conflict_detect_node (충돌 감지 + needs_fact_check 설정)
```

`conflict_detect_node`는 LLM에게 기사 목록을 분석시켜 충돌 여부를 판단하고, 결과를 State에 기록합니다.

```python
# apps/news/graph/nodes.py - conflict_detect_node
return {
    "conflicts": conflicts,
    "needs_fact_check": True,   # ← 이 값으로 분기 결정
    "iteration_count": iteration,
}
```

분기 라우터 함수가 이 값을 읽어 다음 노드를 결정합니다.

```python
# apps/news/graph/builder.py
def _route_after_conflict(state: NewsState) -> str:
    if state.get("needs_fact_check") and state.get("iteration_count", 0) < state.get("max_iterations", 2):
        return "fact_check"   # 충돌 있음 → 팩트체크
    return "finalize"         # 충돌 없음 → 바로 완료

builder.add_conditional_edges(
    "conflict_detect",
    _route_after_conflict,
    {"fact_check": "fact_check", "finalize": "finalize"},
)
```

---

### 3. 팩트체크 루프 (Cycle)

> **"팩트체크 후 다시 충돌 감지 — 최대 2회 반복"**

```
apps/news/graph/builder.py → fact_check → conflict_detect 엣지
apps/news/graph/state.py   → iteration_count 필드 (루프 카운터)
```

```python
# apps/news/graph/builder.py
builder.add_edge("fact_check", "conflict_detect")  # ← 루프 형성
```

무한루프 방지는 `iteration_count`를 State에서 관리해 `max_iterations`(기본 2)를 초과하면 `_route_after_conflict`가 `"finalize"`로 탈출합니다.

```
settings.py → NEWSBOT["MAX_FACT_CHECK_ITERATIONS"] 로 루프 횟수 조정 가능
```

---

## 프로젝트 구조

```
002_news/
├── manage.py
├── pyproject.toml                      # uv 패키지 관리
├── config/
│   ├── settings.py                     # NEWSBOT 설정 딕셔너리
│   └── urls.py
└── apps/
    └── news/
        ├── models.py                   # SummaryReport / Article / ConflictRecord
        ├── views.py                    # 웹 뷰 (폼, 폴링, 결과)
        ├── forms.py                    # NewsBotForm
        ├── service.py                  # 백그라운드 스레드 실행
        ├── admin.py                    # Django Admin 등록
        ├── graph/
        │   ├── state.py                # ★ NewsState (TypedDict + operator.add)
        │   ├── nodes.py                # ★ 8개 노드 함수
        │   └── builder.py              # ★ 그래프 조립 + graph.png 생성
        ├── sources/
        │   ├── rss.py                  # RSS 수집 (feedparser)
        │   ├── url.py                  # URL 크롤링 (requests + BS4)
        │   └── pdf.py                  # PDF 파싱 (pypdf)
        ├── management/commands/
        │   ├── run_newsbot.py          # python manage.py run_newsbot
        │   └── generate_graph.py       # python manage.py generate_graph
        └── templates/news/
            ├── index.html              # 검색 폼
            ├── loading.html            # 진행 상태 (JS 폴링)
            ├── result.html             # 요약 결과 (탭 UI)
            └── report_list.html        # 보고서 목록
```

---

## 빠른 시작

```bash
# 1. 패키지 설치
uv add django langgraph langchain-groq langchain-core \
        feedparser pypdf requests beautifulsoup4 python-dotenv

# 2. 환경 변수 설정
cp .env.example .env
# .env 에 GROQ_API_KEY=gsk_... 입력 (https://console.groq.com/keys)

# 3. DB 초기화
uv run python manage.py migrate
uv run python manage.py createsuperuser

# 4. 서버 실행
uv run python manage.py runserver
# → http://localhost:8000
```

---

## 설정

`config/settings.py` 의 `NEWSBOT` 딕셔너리에서 모든 파라미터를 조정합니다.

```python
NEWSBOT = {
    "LLM_PROVIDER": "groq",                    # groq | ollama | anthropic
    "LLM_MODEL": "llama-3.1-8b-instant",       # 모델명
    "MAX_ARTICLES_PER_FEED": 5,                # RSS 피드당 최대 기사 수
    "MAX_FACT_CHECK_ITERATIONS": 2,            # 팩트체크 루프 최대 횟수
    "DEFAULT_RSS_FEEDS": [...],                # 기본 RSS 피드 목록
    "DEFAULT_URLS": [...],                     # 기본 크롤링 URL 목록
}
```

### 지원 LLM 프로바이더

| 프로바이더 | 비용 | 설정 |
|-----------|------|------|
| **Groq** (기본) | 무료 | `GROQ_API_KEY` 환경변수 |
| **Ollama** | 무료 (로컬) | Ollama 설치 후 `LLM_PROVIDER=ollama` |
| **Anthropic** | 유료 | `ANTHROPIC_API_KEY` 환경변수 |

---

## 주요 명령어

```bash
uv run python manage.py run_newsbot --query "AI 반도체 규제"   # CLI 실행
uv run python manage.py generate_graph                         # graph.png 생성
uv run python manage.py runserver                              # 웹 서버 실행
```
