from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("news/", include("apps.news.urls")),
    path("", include(("apps.news.urls", "news_root"))),
]
