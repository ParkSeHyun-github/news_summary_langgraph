from django.urls import path
from . import views

app_name = "news"

urlpatterns = [
    path("", views.index, name="index"),
    path("reports/", views.report_list, name="report_list"),
    path("reports/<int:pk>/", views.result, name="result"),
    path("reports/<int:pk>/loading/", views.loading, name="loading"),
    path("reports/<int:pk>/status.json", views.status_json, name="status_json"),
]
