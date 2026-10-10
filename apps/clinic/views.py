"""
Представления DRF для Hospital REST API.

Все ViewSet'ы снабжены @extend_schema-декораторами drf-spectacular
для генерации документации OpenAPI 3.0.

Структура модуля:
  AuthViewSet          — регистрация, профиль текущего пользователя
  SpecializationViewSet — CRUD специализаций
  DoctorViewSet         — CRUD врачей + фильтрация/поиск/сортировка
  ScheduleViewSet       — CRUD расписаний
  AppointmentViewSet    — записи пациента + смена статуса персоналом
  MedicalRecordViewSet  — медицинские карты
  DoctorReviewViewSet   — отзывы о врачах
"""
from django.db.models import Avg, QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .filters import AppointmentFilter, DoctorFilter, DoctorReviewFilter
from .models import Appointment, Doctor, DoctorReview, MedicalRecord, Schedule, Specialization
from .permissions import (
    IsMedicalRecordOwnerOrStaff,
    IsOwnerOrStaff,
    IsPatientOrStaff,
    IsReviewAuthorOrStaff,
    IsStaffForStatusChange,
    IsStaffOrReadOnly,
)
from .serializers import (
    AppointmentReadSerializer,
    AppointmentStatusSerializer,
    AppointmentWriteSerializer,
    DoctorReadSerializer,
    DoctorReviewReadSerializer,
    DoctorReviewWriteSerializer,
    DoctorWriteSerializer,
    MedicalRecordReadSerializer,
    MedicalRecordWriteSerializer,
    RegisterSerializer,
    ScheduleSerializer,
    SpecializationSerializer,
    UserProfileSerializer,
)


# ===========================================================================
# Auth
# ===========================================================================

@extend_schema(tags=["auth"])
class AuthViewSet(viewsets.GenericViewSet):
    """Аутентификация и профиль пользователя."""

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == "register":
            return RegisterSerializer
        return UserProfileSerializer

    def get_permissions(self):
        if self.action == "register":
            return [AllowAny()]
        return [IsAuthenticated()]

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Регистрация нового пациента",
        description=(
            "Создаёт новую учётную запись пациента. "
            "После регистрации используйте `/api/auth/token/` для получения JWT."
        ),
        request=RegisterSerializer,
        responses={
            201: UserProfileSerializer,
            400: OpenApiResponse(description="Ошибки валидации"),
        },
        examples=[
            OpenApiExample(
                "Пример запроса",
                value={
                    "username": "ivanov",
                    "email": "ivanov@example.com",
                    "first_name": "Иван",
                    "last_name": "Иванов",
                    "password": "strongpass123",
                    "password2": "strongpass123",
                    "phone_number": "+7 900 000-00-00",
                    "birth_date": "1990-05-15",
                    "blood_group": "II+",
                },
                request_only=True,
            )
        ],
    )
    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request: Request) -> Response:
        """Регистрация нового пациента."""
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        out = UserProfileSerializer(user, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Профиль текущего пользователя",
        description="Возвращает профиль авторизованного пользователя.",
        responses={200: UserProfileSerializer},
    )
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request: Request) -> Response:
        """Профиль текущего авторизованного пользователя."""
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Обновление профиля",
        description="Частичное обновление профиля текущего пользователя (PATCH).",
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
    )
    @action(detail=False, methods=["patch"], url_path="me/update")
    def me_update(self, request: Request) -> Response:
        """Частичное обновление профиля текущего пользователя."""
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ===========================================================================
# Specialization
# ===========================================================================

@extend_schema_view(
    list=extend_schema(
        summary="Список специализаций",
        description="Доступен всем пользователям, включая неавторизованных.",
        tags=["specializations"],
    ),
    retrieve=extend_schema(
        summary="Детали специализации",
        tags=["specializations"],
    ),
    create=extend_schema(
        summary="Создать специализацию",
        description="Только для персонала (is_staff).",
        tags=["specializations"],
    ),
    update=extend_schema(
        summary="Обновить специализацию (PUT)",
        tags=["specializations"],
    ),
    partial_update=extend_schema(
        summary="Частично обновить специализацию (PATCH)",
        tags=["specializations"],
    ),
    destroy=extend_schema(
        summary="Удалить специализацию",
        tags=["specializations"],
    ),
)
class SpecializationViewSet(viewsets.ModelViewSet):
    """CRUD специализаций врачей. Чтение открыто, запись только для staff."""

    queryset           = Specialization.objects.all()
    serializer_class   = SpecializationSerializer
    permission_classes = [IsStaffOrReadOnly]
    parser_classes     = [JSONParser, MultiPartParser, FormParser]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ["name", "description"]
    ordering_fields    = ["name"]
    ordering           = ["name"]


# ===========================================================================
# Doctor
# ===========================================================================

@extend_schema_view(
    list=extend_schema(
        summary="Список врачей",
        description=(
            "Поддерживает фильтрацию по специализации, опыту и цене; "
            "поиск по ФИО и специализации; сортировку по цене и рейтингу."
        ),
        tags=["doctors"],
        parameters=[
            OpenApiParameter("specialization", int,   description="ID специализации"),
            OpenApiParameter("experience_min", int,   description="Стаж от (лет)"),
            OpenApiParameter("experience_max", int,   description="Стаж до (лет)"),
            OpenApiParameter("price_min",      float, description="Цена от (₽)"),
            OpenApiParameter("price_max",      float, description="Цена до (₽)"),
            OpenApiParameter("search",         str,   description="Поиск по ФИО / специализации"),
            OpenApiParameter(
                "ordering",
                str,
                description="Сортировка: price, -price, experience_years, -experience_years",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Детали врача",
        tags=["doctors"],
    ),
    create=extend_schema(
        summary="Добавить врача",
        description="Только для персонала (is_staff).",
        tags=["doctors"],
    ),
    update=extend_schema(
        summary="Обновить врача (PUT)",
        tags=["doctors"],
    ),
    partial_update=extend_schema(
        summary="Частично обновить врача (PATCH)",
        tags=["doctors"],
    ),
    destroy=extend_schema(
        summary="Удалить врача",
        tags=["doctors"],
    ),
)
class DoctorViewSet(viewsets.ModelViewSet):
    """
    CRUD врачей.
    Чтение доступно всем, запись — только is_staff.
    Фильтрация через DoctorFilter, поиск по ФИО и специализации.
    Сортировка по цене и опыту; сортировка по рейтингу реализована
    через аннотацию avg_rating.
    """

    permission_classes = [IsStaffOrReadOnly]
    parser_classes     = [JSONParser, MultiPartParser, FormParser]
    filterset_class    = DoctorFilter
    filter_backends    = [
        filters.SearchFilter,
        filters.OrderingFilter,
        __import__("django_filters.rest_framework", fromlist=["DjangoFilterBackend"]).DjangoFilterBackend,
    ]
    search_fields   = [
        "first_name",
        "last_name",
        "patronymic",
        "specialization__name",
    ]
    ordering_fields = ["price", "experience_years", "avg_rating"]
    ordering        = ["last_name"]

    def get_queryset(self) -> QuerySet:
        # ВАЖНО: .annotate() сбрасывает Meta.ordering в Django ORM,
        # из-за чего DRF не может гарантировать стабильный порядок при пагинации
        # (UnorderedObjectListWarning → дублирующиеся/пропущенные записи на страницах).
        # Явный .order_by() восстанавливает детерминированную сортировку.
        return (
            Doctor.objects.select_related("specialization")
            .prefetch_related("schedules", "reviews")
            .annotate(avg_rating=Avg("reviews__stars"))
            .order_by("last_name", "first_name", "id")
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return DoctorWriteSerializer
        return DoctorReadSerializer


# ===========================================================================
# Schedule
# ===========================================================================

@extend_schema_view(
    list=extend_schema(
        summary="Список расписаний",
        description="Фильтруется по параметру ?doctor=<id>. Доступен всем.",
        tags=["schedules"],
        parameters=[
            OpenApiParameter("doctor", int, description="ID врача"),
        ],
    ),
    retrieve=extend_schema(summary="Детали расписания", tags=["schedules"]),
    create=extend_schema(
        summary="Добавить слот расписания",
        description="Только для персонала (is_staff).",
        tags=["schedules"],
    ),
    update=extend_schema(summary="Обновить расписание (PUT)", tags=["schedules"]),
    partial_update=extend_schema(
        summary="Частично обновить расписание (PATCH)", tags=["schedules"]
    ),
    destroy=extend_schema(summary="Удалить слот расписания", tags=["schedules"]),
)
class ScheduleViewSet(viewsets.ModelViewSet):
    """CRUD расписаний врачей. Чтение открыто, запись только для staff."""

    serializer_class   = ScheduleSerializer
    permission_classes = [IsStaffOrReadOnly]
    filter_backends    = [
        __import__("django_filters.rest_framework", fromlist=["DjangoFilterBackend"]).DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    ordering_fields = ["day_of_week", "start_time"]
    ordering        = ["day_of_week"]

    def get_queryset(self) -> QuerySet:
        qs = Schedule.objects.select_related("doctor")
        doctor_id = self.request.query_params.get("doctor")
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)
        return qs


# ===========================================================================
# Appointment
# ===========================================================================

@extend_schema(tags=["appointments"])
class AppointmentViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Записи на приём.

    Пациент:
      POST   /api/appointments/          — создать запись
      GET    /api/appointments/          — свои записи
      GET    /api/appointments/{id}/     — своя запись (детально)
      DELETE /api/appointments/{id}/     — отменить свою запись
      PATCH  /api/appointments/{id}/cancel/ — явная отмена (алиас)

    Персонал (is_staff):
      GET  /api/appointments/            — все записи (+ фильтры)
      GET  /api/appointments/all/        — все записи (алиас)
      PATCH /api/appointments/{id}/set_status/ — смена статуса
    """

    filterset_class = AppointmentFilter
    filter_backends = [
        __import__("django_filters.rest_framework", fromlist=["DjangoFilterBackend"]).DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    ordering_fields = ["date_time", "created_date", "status"]
    ordering        = ["-date_time"]

    def get_queryset(self) -> QuerySet:
        qs = (
            Appointment.objects.select_related(
                "patient",
                "doctor__specialization",
            )
            .prefetch_related("doctor__schedules", "doctor__reviews")
        )
        # Пациент видит только свои записи, персонал — все
        if not self.request.user.is_staff:
            qs = qs.filter(patient=self.request.user)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return AppointmentWriteSerializer
        if self.action == "set_status":
            return AppointmentStatusSerializer
        return AppointmentReadSerializer

    def get_permissions(self):
        if self.action == "set_status":
            return [IsStaffForStatusChange()]
        return [IsPatientOrStaff()]

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Создать запись на приём",
        description=(
            "Пациент создаёт запись к врачу. "
            "Автоматически устанавливается статус `pending` и привязывается текущий пользователь."
        ),
        request=AppointmentWriteSerializer,
        responses={201: AppointmentReadSerializer},
        examples=[
            OpenApiExample(
                "Пример запроса",
                value={
                    "doctor": 1,
                    "date_time": "2026-11-01T10:00:00",
                    "complaint": "Боли в грудной клетке",
                },
                request_only=True,
            )
        ],
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
        return super().create(request, *args, **kwargs)

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Список записей",
        description=(
            "Пациент видит только свои записи. "
            "Персонал видит все записи. Поддерживается фильтрация по статусу и дате."
        ),
        parameters=[
            OpenApiParameter("status",    str,  description="Статус: pending/confirmed/cancelled/completed"),
            OpenApiParameter("date_from", str,  description="Дата от (YYYY-MM-DD)"),
            OpenApiParameter("date_to",   str,  description="Дата до (YYYY-MM-DD)"),
            OpenApiParameter("doctor",    int,  description="ID врача"),
            OpenApiParameter("patient",   int,  description="ID пациента (только staff)"),
        ],
        responses={200: AppointmentReadSerializer(many=True)},
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Детали записи на приём",
        responses={200: AppointmentReadSerializer},
    )
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return super().retrieve(request, *args, **kwargs)

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Отменить запись (DELETE)",
        description=(
            "Пациент может отменить только свою запись со статусом `pending` или `confirmed`. "
            "Физически запись не удаляется — статус меняется на `cancelled`."
        ),
        responses={204: None, 400: OpenApiResponse(description="Невозможно отменить")},
    )
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Отмена записи (soft-delete через смену статуса)."""
        appointment = self.get_object()
        self.check_object_permissions(request, appointment)

        if appointment.status in (
            Appointment.Status.COMPLETED,
            Appointment.Status.CANCELLED,
        ):
            return Response(
                {
                    "detail": (
                        f"Нельзя отменить запись со статусом "
                        f"'{appointment.get_status_display()}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=["status"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Явная отмена записи (PATCH)",
        description="Альтернативный эндпоинт отмены — удобен для фронтенда.",
        responses={
            200: AppointmentReadSerializer,
            400: OpenApiResponse(description="Невозможно отменить"),
        },
    )
    @action(detail=True, methods=["patch"], url_path="cancel")
    def cancel(self, request: Request, pk=None) -> Response:  # noqa: ANN001
        """Отмена записи через PATCH /api/appointments/{id}/cancel/."""
        appointment = self.get_object()
        self.check_object_permissions(request, appointment)

        if appointment.status in (
            Appointment.Status.COMPLETED,
            Appointment.Status.CANCELLED,
        ):
            return Response(
                {
                    "detail": (
                        f"Нельзя отменить запись со статусом "
                        f"'{appointment.get_status_display()}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=["status"])
        out = AppointmentReadSerializer(appointment, context={"request": request})
        return Response(out.data)

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Сменить статус записи (только персонал)",
        description=(
            "Допустимые переходы:\n"
            "- `pending` → `confirmed` | `cancelled`\n"
            "- `confirmed` → `completed` | `cancelled`\n"
            "- `completed` и `cancelled` — финальные состояния."
        ),
        request=AppointmentStatusSerializer,
        responses={
            200: AppointmentReadSerializer,
            400: OpenApiResponse(description="Недопустимый переход статуса"),
            403: OpenApiResponse(description="Нет прав (не staff)"),
        },
        examples=[
            OpenApiExample(
                "Подтверждение записи",
                value={"status": "confirmed"},
                request_only=True,
            ),
            OpenApiExample(
                "Завершение приёма",
                value={"status": "completed"},
                request_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["patch"], url_path="set_status")
    def set_status(self, request: Request, pk=None) -> Response:  # noqa: ANN001
        """Смена статуса записи персоналом / врачом."""
        appointment = self.get_object()
        serializer  = AppointmentStatusSerializer(
            appointment,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        out = AppointmentReadSerializer(appointment, context={"request": request})
        return Response(out.data)


# ===========================================================================
# MedicalRecord
# ===========================================================================

@extend_schema(tags=["medical-records"])
class MedicalRecordViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Медицинские карты.

    GET    /api/medical-records/       — список (пациент видит только свои)
    GET    /api/medical-records/{id}/  — детали (пациент видит только свои)
    POST   /api/medical-records/       — создать (только staff)
    PUT    /api/medical-records/{id}/  — обновить (только staff)
    PATCH  /api/medical-records/{id}/  — частично обновить (только staff)
    """

    permission_classes = [IsMedicalRecordOwnerOrStaff]
    filter_backends    = [filters.OrderingFilter]
    ordering_fields    = ["created_date"]
    ordering           = ["-created_date"]

    def get_queryset(self) -> QuerySet:
        qs = MedicalRecord.objects.select_related(
            "appointment__patient",
            "appointment__doctor__specialization",
        )
        if not self.request.user.is_staff:
            qs = qs.filter(appointment__patient=self.request.user)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MedicalRecordWriteSerializer
        return MedicalRecordReadSerializer

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Создать медицинскую карту",
        description=(
            "Доступно только персоналу. "
            "Приём должен иметь статус `confirmed` (будет автоматически переведён в `completed`) "
            "или уже быть `completed`. Статус `pending` и `cancelled` недопустимы."
        ),
        request=MedicalRecordWriteSerializer,
        responses={201: MedicalRecordReadSerializer},
        examples=[
            OpenApiExample(
                "Пример запроса",
                value={
                    "appointment": 1,
                    "diagnosis": "ИБС. Стенокардия напряжения II ФК.",
                    "prescription": "Аспирин 75 мг/сут, Бисопролол 5 мг/сут. Контроль через 2 недели.",
                },
                request_only=True,
            )
        ],
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
        return super().create(request, *args, **kwargs)

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Список медицинских карт",
        description="Пациент видит только свои карты. Персонал — все.",
        responses={200: MedicalRecordReadSerializer(many=True)},
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Детали медицинской карты",
        responses={200: MedicalRecordReadSerializer},
    )
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return super().retrieve(request, *args, **kwargs)

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Обновить медицинскую карту (PUT)",
        description="Только для персонала.",
        request=MedicalRecordWriteSerializer,
        responses={200: MedicalRecordReadSerializer},
    )
    def update(self, request: Request, *args, **kwargs) -> Response:
        return super().update(request, *args, **kwargs)

    # ------------------------------------------------------------------
    @extend_schema(
        summary="Частично обновить медицинскую карту (PATCH)",
        description="Только для персонала.",
        request=MedicalRecordWriteSerializer,
        responses={200: MedicalRecordReadSerializer},
    )
    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        return super().partial_update(request, *args, **kwargs)


# ===========================================================================
# DoctorReview
# ===========================================================================

@extend_schema_view(
    list=extend_schema(
        summary="Список отзывов",
        description=(
            "Фильтрация: ?doctor=<id>, ?stars=<1-5>, "
            "?stars_min, ?stars_max, ?created_from, ?created_to."
        ),
        tags=["reviews"],
        parameters=[
            OpenApiParameter("doctor",       int, description="ID врача"),
            OpenApiParameter("stars",        int, description="Точная оценка (1-5)"),
            OpenApiParameter("stars_min",    int, description="Оценка от"),
            OpenApiParameter("stars_max",    int, description="Оценка до"),
            OpenApiParameter("created_from", str, description="Дата отзыва от (YYYY-MM-DD)"),
            OpenApiParameter("created_to",   str, description="Дата отзыва до (YYYY-MM-DD)"),
        ],
    ),
    retrieve=extend_schema(
        summary="Детали отзыва",
        tags=["reviews"],
    ),
    create=extend_schema(
        summary="Оставить отзыв",
        description=(
            "Авторизованный пациент оставляет отзыв врачу. "
            "Один пациент — один отзыв одному врачу."
        ),
        tags=["reviews"],
        examples=[
            OpenApiExample(
                "Пример запроса",
                value={"doctor": 1, "stars": 5, "comment": "Отличный врач, всё объяснил!"},
                request_only=True,
            )
        ],
    ),
    destroy=extend_schema(
        summary="Удалить отзыв",
        description="Только автор отзыва или персонал.",
        tags=["reviews"],
    ),
)
class DoctorReviewViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Отзывы о врачах.
    Чтение: все авторизованные.
    Создание: любой авторизованный пациент.
    Удаление: только автор или персонал.
    Обновление (редактирование) намеренно отключено — пациент пишет отзыв один раз.
    """

    filterset_class    = DoctorReviewFilter
    permission_classes = [IsReviewAuthorOrStaff]
    filter_backends    = [
        __import__("django_filters.rest_framework", fromlist=["DjangoFilterBackend"]).DjangoFilterBackend,
        filters.OrderingFilter,
    ]
    ordering_fields = ["stars", "created_date"]
    ordering        = ["-created_date"]

    def get_queryset(self) -> QuerySet:
        return DoctorReview.objects.select_related("doctor__specialization", "patient")

    def get_serializer_class(self):
        if self.action == "create":
            return DoctorReviewWriteSerializer
        return DoctorReviewReadSerializer
