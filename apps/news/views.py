from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .forms import NewsBotForm
from .models import SummaryReport
from .service import run_newsbot_async


def index(request):
    if request.method == "POST":
        form = NewsBotForm(request.POST)
        if form.is_valid():
            report = SummaryReport.objects.create(
                query=form.cleaned_data["query"],
                status=SummaryReport.STATUS_PENDING,
            )
            run_newsbot_async(
                report_id=report.pk,
                rss_feeds=form.get_rss_list(),
                pdf_paths=[],
                urls=form.get_url_list(),
            )
            return redirect("news:loading", pk=report.pk)
    else:
        form = NewsBotForm()

    recent = SummaryReport.objects.filter(status=SummaryReport.STATUS_DONE).order_by("-created_at")[:5]
    return render(request, "news/index.html", {"form": form, "recent": recent})


def loading(request, pk: int):
    report = get_object_or_404(SummaryReport, pk=pk)
    if report.status == SummaryReport.STATUS_DONE:
        return redirect("news:result", pk=pk)
    if report.status == SummaryReport.STATUS_ERROR:
        return render(request, "news/error.html", {"report": report})
    return render(request, "news/loading.html", {"report": report})


@require_GET
def status_json(request, pk: int):
    report = get_object_or_404(SummaryReport, pk=pk)
    return JsonResponse({
        "status": report.status,
        "redirect": f"/news/reports/{pk}/" if report.status == SummaryReport.STATUS_DONE else None,
    })


def result(request, pk: int):
    report = get_object_or_404(SummaryReport, pk=pk)
    articles_by_source = {
        "search": report.articles.filter(source="search"),
        "rss": report.articles.filter(source="rss"),
        "pdf": report.articles.filter(source="pdf"),
        "url": report.articles.filter(source="url"),
    }
    return render(request, "news/result.html", {
        "report": report,
        "articles_by_source": articles_by_source,
        "conflicts": report.conflicts.all(),
    })


@require_GET
def report_list(request):
    reports = SummaryReport.objects.order_by("-created_at")[:20]
    return render(request, "news/report_list.html", {"reports": reports})
