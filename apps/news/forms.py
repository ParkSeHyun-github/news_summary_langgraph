from django import forms
from django.conf import settings


class NewsBotForm(forms.Form):
    query = forms.CharField(
        label="검색 주제",
        max_length=255,
        widget=forms.TextInput(attrs={
            "placeholder": "예: AI 반도체 규제, 기후변화 최신 동향...",
            "class": "query-input",
            "autofocus": True,
        }),
    )
    rss_feeds = forms.CharField(
        label="RSS 피드 (줄바꿈으로 구분)",
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "비워두면 기본 피드(BBC, CNN, Reuters) 사용",
            "class": "source-input",
        }),
    )
    urls = forms.CharField(
        label="크롤링 URL (줄바꿈으로 구분)",
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "https://techcrunch.com",
            "class": "source-input",
        }),
    )

    def get_rss_list(self) -> list[str]:
        raw = self.cleaned_data.get("rss_feeds", "").strip()
        if not raw:
            return []  # 비우면 fetch_rss_node 가 쿼리 기반 자동 선택
        return [line.strip() for line in raw.splitlines() if line.strip()]

    def get_url_list(self) -> list[str]:
        raw = self.cleaned_data.get("urls", "").strip()
        if not raw:
            return settings.NEWSBOT["DEFAULT_URLS"]
        return [line.strip() for line in raw.splitlines() if line.strip()]
