"""
LangGraph 그래프 조립 및 graph.png 생성.
"""
from langgraph.graph import StateGraph, START, END

from apps.news.graph.state import NewsState
from apps.news.graph.nodes import (
    fetch_rss_node, fetch_pdf_node, fetch_url_node, fetch_search_node,
    aggregate_node, summarize_node,
    conflict_detect_node, fact_check_node, finalize_node,
)


def _route_after_conflict(state: NewsState) -> str:
    iteration = state.get("iteration_count", 0)
    max_iter  = state.get("max_iterations", 2)
    # 첫 번째 패스는 충돌 여부와 무관하게 항상 팩트체크 실행
    if iteration == 0:
        return "fact_check"
    # 이후 패스: 충돌이 남아 있고 한도 미초과 시에만 재실행
    if state.get("needs_fact_check") and iteration < max_iter:
        return "fact_check"
    return "finalize"


def build_graph():
    builder = StateGraph(NewsState)

    builder.add_node("fetch_rss", fetch_rss_node)
    builder.add_node("fetch_pdf", fetch_pdf_node)
    builder.add_node("fetch_url", fetch_url_node)
    builder.add_node("fetch_search", fetch_search_node)
    builder.add_node("aggregate", aggregate_node)
    builder.add_node("summarize", summarize_node)
    builder.add_node("conflict_detect", conflict_detect_node)
    builder.add_node("fact_check", fact_check_node)
    builder.add_node("finalize", finalize_node)

    # START → 4개 병렬 페치 (search 는 항상 실행)
    builder.add_edge(START, "fetch_search")
    builder.add_edge(START, "fetch_rss")
    builder.add_edge(START, "fetch_pdf")
    builder.add_edge(START, "fetch_url")

    # 4개 모두 완료 → aggregate
    builder.add_edge("fetch_search", "aggregate")
    builder.add_edge("fetch_rss", "aggregate")
    builder.add_edge("fetch_pdf", "aggregate")
    builder.add_edge("fetch_url", "aggregate")

    # 직렬 파이프라인
    builder.add_edge("aggregate", "summarize")
    builder.add_edge("summarize", "conflict_detect")

    # 조건 분기
    builder.add_conditional_edges(
        "conflict_detect",
        _route_after_conflict,
        {"fact_check": "fact_check", "finalize": "finalize"},
    )

    # 팩트체크 루프 (max_iterations 로 탈출)
    builder.add_edge("fact_check", "conflict_detect")
    builder.add_edge("finalize", END)

    return builder.compile()


def save_graph_image(output_path: str = "graph.png") -> None:
    graph = build_graph()
    try:
        png_bytes = graph.get_graph().draw_mermaid_png()
        with open(output_path, "wb") as f:
            f.write(png_bytes)
        print(f"graph.png 저장 완료: {output_path}")
    except Exception as e:
        mmd_path = output_path.replace(".png", ".mmd")
        with open(mmd_path, "w", encoding="utf-8") as f:
            f.write(graph.get_graph().draw_mermaid())
        print(f"PNG 실패({e}) → Mermaid 저장: {mmd_path}")
