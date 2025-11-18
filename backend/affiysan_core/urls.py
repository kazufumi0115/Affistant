from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # --- DRF Spectacular ドキュメント ---
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # --- API本体 ---
    # 認証エンドポイント (usersアプリをインクルード)
    # /api/v1/auth/register/, /api/v1/auth/login/, /api/v1/auth/logout/ などにルーティング
    path("api/v1/auth/", include("users.urls")),
    # SEO/トラッキング関連エンドポイント (trackingアプリをインクルード)
    # /api/v1/seo/keywords/, /api/v1/seo/runs/ などにルーティング
    path("api/v1/seo/", include("tracking.urls")),
    # DRFの認証機能（ブラウザでデバッグする際などに便利）
    path("api-auth/", include("rest_framework.urls")),
]
