from django.db import models


class SummaryReport(models.Model):
    """실행 1회 = 보고서 1건"""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_PENDING, "대기"),
        (STATUS_RUNNING, "실행 중"),
        (STATUS_DONE, "완료"),
        (STATUS_ERROR, "오류"),
    ]

    query = models.CharField("검색 주제", max_length=255)
    final_summary = models.TextField("최종 요약", blank=True)
    confidence_score = models.FloatField("신뢰도", default=0.0)
    fact_checked = models.BooleanField("팩트체크 여부", default=False)
    status = models.CharField("상태", max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField("오류 메시지", blank=True)
    created_at = models.DateTimeField("생성 시각", auto_now_add=True)

    class Meta:
        verbose_name = "요약 보고서"
        verbose_name_plural = "요약 보고서 목록"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.query}"


class Article(models.Model):
    SOURCE_CHOICES = [("rss", "RSS"), ("pdf", "PDF"), ("url", "URL"), ("search", "검색")]

    report = models.ForeignKey(
        SummaryReport,
        on_delete=models.CASCADE,
        related_name="articles",
        verbose_name="보고서",
    )
    title = models.CharField("제목", max_length=512)
    content = models.TextField("본문")
    source = models.CharField("소스 타입", max_length=10, choices=SOURCE_CHOICES)
    source_name = models.CharField("출처명", max_length=255)
    url = models.URLField("URL", blank=True, null=True)
    published = models.CharField("발행일", max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "기사"
        verbose_name_plural = "기사 목록"

    def __str__(self):
        return self.title


class ConflictRecord(models.Model):
    """팩트체크에서 발견된 충돌"""

    report = models.ForeignKey(
        SummaryReport,
        on_delete=models.CASCADE,
        related_name="conflicts",
        verbose_name="보고서",
    )
    topic = models.CharField("충돌 주제", max_length=255)
    claim_a = models.TextField("주장 A")
    claim_b = models.TextField("주장 B")
    source_a = models.CharField("출처 A", max_length=255)
    source_b = models.CharField("출처 B", max_length=255)
    verdict = models.TextField("검증 결과", blank=True)
    resolved = models.BooleanField("해결됨", default=False)

    class Meta:
        verbose_name = "충돌 기록"
        verbose_name_plural = "충돌 기록 목록"

    def __str__(self):
        return f"{self.topic} ({self.source_a} vs {self.source_b})"
