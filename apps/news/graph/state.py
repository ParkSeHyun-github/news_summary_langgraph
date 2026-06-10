import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict


class NewsState(TypedDict):
    query: str
    rss_feeds: list[str]
    pdf_paths: list[str]
    urls: list[str]

    # 병렬 노드가 동시에 append → operator.add 로 자동 병합
    articles: Annotated[list[dict], operator.add]

    summary: str
    conflicts: list[dict]
    fact_check_results: list[dict]
    final_summary: str

    confidence_score: float
    needs_fact_check: bool
    iteration_count: int
    max_iterations: int
