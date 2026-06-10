"""백그라운드 스레드로 그래프 실행 후 DB 저장."""
import threading
from django.conf import settings
from django.db import close_old_connections
from apps.news.models import SummaryReport, Article, ConflictRecord


def _run(report_id: int, rss_feeds: list, pdf_paths: list, urls: list) -> None:
    # 새 스레드에서 이전 커넥션을 닫아 SQLite 스레드 충돌 방지
    close_old_connections()

    from apps.news.graph.builder import build_graph

    report = SummaryReport.objects.get(pk=report_id)
    report.status = SummaryReport.STATUS_RUNNING
    report.save(update_fields=["status"])
    print(f"  [Service] report#{report_id} → 실행 중")

    try:
        graph = build_graph()
        result = graph.invoke({
            "query": report.query,
            "rss_feeds": rss_feeds,
            "pdf_paths": pdf_paths,
            "urls": urls,
            "articles": [],
            "summary": "",
            "conflicts": [],
            "fact_check_results": [],
            "final_summary": "",
            "confidence_score": 0.0,
            "needs_fact_check": False,
            "iteration_count": 0,
            "max_iterations": settings.NEWSBOT.get("MAX_FACT_CHECK_ITERATIONS", 2),
        })

        report.final_summary = result.get("final_summary", "")
        report.confidence_score = result.get("confidence_score", 0.0)
        report.fact_checked = bool(result.get("fact_check_results"))
        report.status = SummaryReport.STATUS_DONE
        report.save()
        print(f"  [Service] report#{report_id} → 완료")

        Article.objects.bulk_create([
            Article(
                report=report,
                title=a["title"],
                content=a["content"],
                source=a["source"],
                source_name=a["source_name"],
                url=a.get("url"),
                published=a.get("published"),
            )
            for a in result.get("articles", [])
        ])

        for c in result.get("conflicts", []):
            verdict_entry = next(
                (r for r in result.get("fact_check_results", []) if r.get("topic") == c.get("topic")),
                {},
            )
            ConflictRecord.objects.create(
                report=report,
                topic=c.get("topic", ""),
                claim_a=c.get("claim_a", ""),
                claim_b=c.get("claim_b", ""),
                source_a=c.get("source_a", ""),
                source_b=c.get("source_b", ""),
                verdict=verdict_entry.get("verdict", ""),
                resolved=verdict_entry.get("resolved", False),
            )

    except Exception as e:
        print(f"  [Service] report#{report_id} → 오류: {e}")
        report.status = SummaryReport.STATUS_ERROR
        report.error_message = str(e)
        report.save(update_fields=["status", "error_message"])
        raise
    finally:
        close_old_connections()


def run_newsbot_async(report_id: int, rss_feeds: list, pdf_paths: list, urls: list) -> None:
    t = threading.Thread(target=_run, args=(report_id, rss_feeds, pdf_paths, urls), daemon=True)
    t.start()
