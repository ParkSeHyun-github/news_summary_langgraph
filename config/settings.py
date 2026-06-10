from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-in-prod")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.news",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_TZ = True

# ── 뉴스봇 설정 ──────────────────────────────────────────────
NEWSBOT = {
    "MAX_ARTICLES_PER_FEED": 5,
    "MAX_FACT_CHECK_ITERATIONS": 2,
    "LLM_PROVIDER": os.environ.get("LLM_PROVIDER", "groq"),
    "LLM_MODEL": os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile"),
    "DEFAULT_URLS": [],

    # ── 카테고리별 RSS 피드 ──────────────────────────────────
    # fetch_rss_node 가 쿼리 키워드로 관련 카테고리를 자동 선택
    "RSS_FEEDS_BY_CATEGORY": {
        "general": [
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        ],
        "technology": [
            "https://feeds.bbci.co.uk/news/technology/rss.xml",
            "https://techcrunch.com/feed/",
            "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        ],
        "science": [
            "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
            "https://www.sciencedaily.com/rss/all.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
        ],
        "business": [
            "https://feeds.bbci.co.uk/news/business/rss.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        ],
        "health": [
            "https://feeds.bbci.co.uk/news/health/rss.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
        ],
        "sports": [
            "https://feeds.bbci.co.uk/sport/rss.xml",
        ],
        "world": [
            "https://feeds.bbci.co.uk/news/world/rss.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        ],
        "weather": [
            "https://feeds.bbci.co.uk/news/rss.xml",
        ],
        "entertainment": [
            "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        ],
        "politics": [
            "https://feeds.bbci.co.uk/news/politics/rss.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        ],
    },

    # ── 카테고리 키워드 매핑 ─────────────────────────────────
    # 쿼리에 아래 키워드가 포함되면 해당 카테고리 피드 사용
    "CATEGORY_KEYWORDS": {
        "technology": ["ai", "인공지능", "기술", "tech", "소프트웨어", "반도체", "컴퓨터", "로봇", "it", "앱", "스마트폰", "데이터"],
        "science":    ["과학", "연구", "우주", "물리", "화학", "생물", "기후", "환경", "지구", "탄소", "에너지"],
        "business":   ["경제", "주식", "금융", "투자", "시장", "gdp", "인플레이션", "환율", "무역", "기업", "스타트업"],
        "health":     ["건강", "의료", "병원", "바이러스", "백신", "암", "의학", "약", "치료", "코로나", "질병"],
        "sports":     ["스포츠", "축구", "야구", "농구", "골프", "올림픽", "월드컵", "선수", "경기", "리그"],
        "world":      ["세계", "국제", "전쟁", "외교", "유엔", "nato", "중국", "미국", "러시아", "유럽"],
        "weather":    ["날씨", "기온", "비", "눈", "태풍", "폭풍", "폭염", "한파", "강수", "weather", "기상"],
        "entertainment": ["영화", "드라마", "음악", "연예", "예능", "공연", "게임", "넷플릭스", "아이돌", "k-pop"],
        "politics":   ["정치", "대통령", "국회", "선거", "정당", "정책", "법안", "장관", "여당", "야당"],
    },
}
