from django.contrib import admin
from .models import SummaryReport, Article, ConflictRecord


class ArticleInline(admin.TabularInline):
    model = Article
    extra = 0
    fields = ("source", "source_name", "title", "url")
    readonly_fields = fields


class ConflictInline(admin.TabularInline):
    model = ConflictRecord
    extra = 0
    fields = ("topic", "source_a", "source_b", "verdict", "resolved")
    readonly_fields = fields


@admin.register(SummaryReport)
class SummaryReportAdmin(admin.ModelAdmin):
    list_display = ("query", "confidence_score", "fact_checked", "article_count", "created_at")
    list_filter = ("fact_checked",)
    search_fields = ("query", "final_summary")
    readonly_fields = ("created_at", "confidence_score", "fact_checked")
    inlines = [ArticleInline, ConflictInline]

    @admin.display(description="기사 수")
    def article_count(self, obj):
        return obj.articles.count()


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "source_name", "report")
    list_filter = ("source",)
    search_fields = ("title", "content", "source_name")


@admin.register(ConflictRecord)
class ConflictRecordAdmin(admin.ModelAdmin):
    list_display = ("topic", "source_a", "source_b", "resolved", "report")
    list_filter = ("resolved",)
