"""
URL-роутинг приложения clinic.

Все маршруты регистрируются через DefaultRouter и подключаются
в config/urls.py под префиксом /api/.

Карта эндпоинтов
─────────────────────────────────────────────────────────────────
AUTH
  POST   /api/auth/register/          — регистрация пациента
  GET    /api/auth/me/                — профиль текущего пользователя
  PATCH  /api/auth/me/update/         — обновление профиля
  POST   /api/auth/token/             — получение JWT (email+password)
  POST   /api/auth/token/refresh/     — обновление access-токена
  POST   /api/auth/token/blacklist/   — инвалидация refresh-токена (logout)

SPECIALIZATIONS
  GET    /api/specializations/        — список
  POST   /api/specializations/        — создать (staff)
  GET    /api/specializations/{id}/   — детали
  PUT    /api/specializations/{id}/   — обновить (staff)
  PATCH  /api/specializations/{id}/   — частично обновить (staff)
  DELETE /api/specializations/{id}/   — удалить (staff)

DOCTORS
  GET    /api/doctors/                — список (+ фильтры/поиск/сортировка)
  POST   /api/doctors/                — создать (staff)
  GET    /api/doctors/{id}/           — детали
  PUT    /api/doctors/{id}/           — обновить (staff)
  PATCH  /api/doctors/{id}/           — частично обновить (staff)
  DELETE /api/doctors/{id}/           — удалить (staff)

SCHEDULES
  GET    /api/schedules/              — список (?doctor=<id>)
  POST   /api/schedules/              — создать (staff)
  GET    /api/schedules/{id}/         — детали
  PUT    /api/schedules/{id}/         — обновить (staff)
  PATCH  /api/schedules/{id}/         — частично обновить (staff)
  DELETE /api/schedules/{id}/         — удалить (staff)

APPOINTMENTS
  GET    /api/appointments/               — список (свои / все для staff)
  POST   /api/appointments/               — создать запись
  GET    /api/appointments/{id}/          — детали
  DELETE /api/appointments/{id}/          — отменить (soft-delete)
  PATCH  /api/appointments/{id}/cancel/   — отменить (алиас)
  PATCH  /api/appointments/{id}/set_status/ — сменить статус (staff)

MEDICAL RECORDS
  GET    /api/medical-records/        — список (свои / все для staff)
  POST   /api/medical-records/        — создать (staff)
  GET    /api/medical-records/{id}/   — детали
  PUT    /api/medical-records/{id}/   — обновить (staff)
  PATCH  /api/medical-records/{id}/   — частично обновить (staff)

REVIEWS
  GET    /api/reviews/                — список (+ фильтры)
  POST   /api/reviews/                — оставить отзыв (авторизованный)
  GET    /api/reviews/{id}/           — детали
  DELETE /api/reviews/{id}/           — удалить (автор или staff)

SCHEMA / DOCS
  GET    /api/schema/                 — OpenAPI 3.0 YAML/JSON
  GET    /api/schema/swagger-ui/      — Swagger UI
  GET    /api/schema/redoc/           — ReDoc UI
─────────────────────────────────────────────────────────────────
"""
from rest_framework.routers import DefaultRouter

from .views import (
    AppointmentViewSet,
    AuthViewSet,
    DoctorReviewViewSet,
    DoctorViewSet,
    MedicalRecordViewSet,
    ScheduleViewSet,
    SpecializationViewSet,
)

router = DefaultRouter()

# Auth
router.register(r"auth", AuthViewSet, basename="auth")

# Public / staff-managed resources
router.register(r"specializations", SpecializationViewSet, basename="specialization")
router.register(r"doctors",         DoctorViewSet,         basename="doctor")
router.register(r"schedules",       ScheduleViewSet,       basename="schedule")

# Patient / staff resources
router.register(r"appointments",    AppointmentViewSet,    basename="appointment")
router.register(r"medical-records", MedicalRecordViewSet,  basename="medical-record")
router.register(r"reviews",         DoctorReviewViewSet,   basename="review")

urlpatterns = router.urls
