"""
Кастомные классы разрешений для Hospital REST API.

Матрица доступа:
┌──────────────────────────────────┬──────────┬───────────┬────────────┐
│ Ресурс                           │ Аноним   │ Пациент   │ Персонал   │
├──────────────────────────────────┼──────────┼───────────┼────────────┤
│ Specialization (list/retrieve)   │    ✓     │     ✓     │     ✓      │
│ Specialization (CUD)             │    ✗     │     ✗     │     ✓      │
│ Doctor (list/retrieve)           │    ✓     │     ✓     │     ✓      │
│ Doctor (CUD)                     │    ✗     │     ✗     │     ✓      │
│ Schedule (list/retrieve)         │    ✓     │     ✓     │     ✓      │
│ Schedule (CUD)                   │    ✗     │     ✗     │     ✓      │
│ Appointment (create)             │    ✗     │     ✓     │     ✓      │
│ Appointment (my list)            │    ✗     │     ✓     │     ✓      │
│ Appointment (status change)      │    ✗     │     ✗     │     ✓      │
│ MedicalRecord (create/edit)      │    ✗     │     ✗     │     ✓      │
│ MedicalRecord (retrieve)         │    ✗     │  только   │     ✓      │
│                                  │          │  свои     │            │
│ DoctorReview (create)            │    ✗     │     ✓     │     ✓      │
│ DoctorReview (delete)            │    ✗     │ только    │     ✓      │
│                                  │          │  свои     │            │
└──────────────────────────────────┴──────────┴───────────┴────────────┘
"""
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from rest_framework.request import Request
from rest_framework.views import APIView


# ---------------------------------------------------------------------------
# Вспомогательные миксины
# ---------------------------------------------------------------------------

class _IsStaffOrReadOnly(BasePermission):
    """
    Базовый класс: безопасные методы (GET, HEAD, OPTIONS) разрешены всем,
    небезопасные — только staff / superuser.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


# ---------------------------------------------------------------------------
# Публичные ресурсы (чтение открыто, запись — только персоналу)
# ---------------------------------------------------------------------------

class IsStaffOrReadOnly(_IsStaffOrReadOnly):
    """
    Специализации, врачи, расписания.
    Чтение: все (включая неавторизованных).
    Создание / редактирование / удаление: только is_staff.
    """


# ---------------------------------------------------------------------------
# Запись на приём
# ---------------------------------------------------------------------------

class IsPatientOrStaff(IsAuthenticated):
    """
    Создание и просмотр записей на приём.
    Любой авторизованный пользователь может создать запись.
    Просмотр и отмена — только если запись принадлежит текущему пользователю
    или пользователь is_staff (проверяется на уровне объекта).
    """

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:  # noqa: ANN001
        # Персонал видит и редактирует любые записи
        if request.user.is_staff:
            return True
        # Пациент — только свои
        return obj.patient == request.user


class IsStaffForStatusChange(IsAuthenticated):
    """
    Смена статуса записи (pending → confirmed → completed / cancelled).
    Только персонал / врачи (is_staff).
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not super().has_permission(request, view):
            return False
        return request.user.is_staff


# ---------------------------------------------------------------------------
# Медицинская карта
# ---------------------------------------------------------------------------

class IsMedicalRecordOwnerOrStaff(IsAuthenticated):
    """
    MedicalRecord:
    - Создание и редактирование — только is_staff.
    - Просмотр — пациент, к которому привязана запись, или is_staff.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not super().has_permission(request, view):
            return False
        # Небезопасные методы только для персонала
        if request.method not in SAFE_METHODS:
            return request.user.is_staff
        return True

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:  # noqa: ANN001
        if request.user.is_staff:
            return True
        # Пациент видит только карту, привязанную к его записи
        return obj.appointment.patient == request.user


# ---------------------------------------------------------------------------
# Отзывы
# ---------------------------------------------------------------------------

class IsReviewAuthorOrStaff(IsAuthenticated):
    """
    DoctorReview:
    - Создание — любой авторизованный.
    - Удаление / редактирование — автор отзыва или is_staff.
    - Чтение — все (IsAuthenticated уже обеспечивает base level).
    """

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:  # noqa: ANN001
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        return obj.patient == request.user


# ---------------------------------------------------------------------------
# Профиль текущего пользователя
# ---------------------------------------------------------------------------

class IsOwnerOrStaff(IsAuthenticated):
    """
    Профиль UserProfile: пользователь редактирует только свой аккаунт,
    персонал может редактировать любой.
    """

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:  # noqa: ANN001
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        return obj == request.user
