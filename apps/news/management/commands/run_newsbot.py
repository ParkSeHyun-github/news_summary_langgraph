"""
python manage.py run_newsbot --query "AI 반도체 규제"
"""
from django.core.management.base import BaseCommand
from django.conf import settings

from apps.news.graph.builder import build_graph
from apps.news.models import SummaryReport, Article, ConflictRecord


class Command(BaseCommand):
    help = "멀티소스 뉴스 요약봇 실행"

    def add_arguments(self, parser):
        parser.add_argument("--query", default="최신 AI 기술 동향", help="검색 주제")
        parser.add_argument("--rss", nargs="*", help="RSS 피드 URL (없으면 settings 기본값)")
        parser.add_argument("--pdf", nargs="*", default=[], help="PDF 파일 경로")
        parser.add_argument("--url", nargs="*", help="크롤링 URL (없으면 settings 기본값)")
        parser.add_argument("--no-save", action="store_true", help="DB 저장 안 함")

    def handle(self, *args, **options):
        query = options["query"]
        rss_feeds = options["rss"] or []   # 비우면 fetch_rss_node 가 쿼리 기반 자동 선택
        pdf_paths = options["pdf"]
        urls = options["url"] or settings.NEWSBOT.get("DEFAULT_URLS", [])
        save_to_db = not options["no_save"]

        self.stdout.write(self.style.HTTP_INFO(f"\n{'='*60}"))
        self.stdout.write(self.style.HTTP_INFO(f"쿼리: {query}"))
        self.stdout.write(self.style.HTTP_INFO(
            f"RSS {len(rss_feeds)}개 | PDF {len(pdf_paths)}개 | URL {len(urls)}개"
        ))
        self.stdout.write(self.style.HTTP_INFO(f"{'='*60}"))

        graph = build_graph()
        initial_state = {
            "query": query,
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
        }

        result = graph.invoke(initial_state)

        # ── 결과 출력 ──
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("최종 요약"))
        self.stdout.write("=" * 60)
        self.stdout.write(result.get("final_summary", "요약 실패"))

        # ── DB 저장 ──
        if save_to_db:
            report = SummaryReport.objects.create(
                query=query,
                final_summary=result.get("final_summary", ""),
                confidence_score=result.get("confidence_score", 0.0),
                fact_checked=bool(result.get("fact_check_results")),
            )
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
            self.stdout.write(self.style.SUCCESS(f"\nDB 저장 완료 (보고서 ID: {report.pk})"))
