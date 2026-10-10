"""
Корневой URL-конфигурация проекта Hospital.

Все API-маршруты доступны под префиксом /api/.
Административная панель Django доступна по /admin/.
Swagger UI — /api/schema/swagger-ui/
ReDoc      — /api/schema/redoc/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

# ---------------------------------------------------------------------------
# Административная панель
# ---------------------------------------------------------------------------
admin.site.site_header = "Hospital — Административная панель"
admin.site.site_title  = "Hospital Admin"
admin.site.index_title = "Управление клиникой"

# ---------------------------------------------------------------------------
# JWT-эндпоинты
# ---------------------------------------------------------------------------
jwt_urlpatterns = [
    path("token/",           TokenObtainPairView.as_view(),  name="token_obtain_pair"),
    path("token/refresh/",   TokenRefreshView.as_view(),     name="token_refresh"),
    path("token/blacklist/", TokenBlacklistView.as_view(),   name="token_blacklist"),
]

# ---------------------------------------------------------------------------
# Основные URL-паттерны
# ---------------------------------------------------------------------------
urlpatterns = [
    # Административная панель Django
    path("admin/", admin.site.urls),

    # JWT-аутентификация (смонтирована внутри /api/auth/ для удобства)
    path("api/auth/", include((jwt_urlpatterns, "jwt"), namespace="jwt")),

    # Основные API-маршруты приложения
    path("api/", include("apps.clinic.urls")),

    # OpenAPI Schema + документация (без namespace — SpectacularSwaggerView
    # ищет url_name="schema" в глобальном пространстве имён)
    path("api/schema/",            SpectacularAPIView.as_view(),                      name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/",      SpectacularRedocView.as_view(url_name="schema"),   name="redoc"),
]

# ---------------------------------------------------------------------------
# Обслуживание медиафайлов в режиме разработки
# ---------------------------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
