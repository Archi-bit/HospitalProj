"""
Административная панель Django для медицинской клиники.

Все модели зарегистрированы с полным набором list_display, list_filter,
search_fields. Используются TabularInline:
  - ScheduleInline   внутри DoctorAdmin
  - MedicalRecordInline внутри AppointmentAdmin
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    Appointment,
    Doctor,
    DoctorReview,
    MedicalRecord,
    Schedule,
    Specialization,
    UserProfile,
)


# ---------------------------------------------------------------------------
# Inline-классы
# ---------------------------------------------------------------------------

class ScheduleInline(admin.TabularInline):
    """Расписание врача — вкладка внутри карточки врача."""

    model           = Schedule
    extra           = 1
    fields          = ("day_of_week", "start_time", "end_time")
    ordering        = ("day_of_week",)
    verbose_name        = "Слот расписания"
    verbose_name_plural = "Расписание"


class MedicalRecordInline(admin.StackedInline):
    """Медицинская карта — вкладка внутри карточки приёма."""

    model          = MedicalRecord
    extra          = 0
    can_delete     = False
    fields         = ("diagnosis", "prescription", "created_date")
    readonly_fields = ("created_date",)
    verbose_name        = "Медицинская карта"
    verbose_name_plural = "Медицинская карта"


# ---------------------------------------------------------------------------
# UserProfileAdmin
# ---------------------------------------------------------------------------

@admin.register(UserProfile)
class UserProfileAdmin(UserAdmin):
    """Расширенная карточка пользователя."""

    fieldsets = UserAdmin.fieldsets + (
        (
            _("Дополнительно"),
            {
                "fields": (
                    "birth_date",
                    "phone_number",
                    "address",
                    "blood_group",
                    "date_register",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            _("Дополнительно"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "birth_date",
                    "phone_number",
                    "blood_group",
                )
            },
        ),
    )
    readonly_fields = ("date_register",)
    list_display   = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone_number",
        "blood_group",
        "is_staff",
        "date_register",
    )
    list_filter    = ("is_staff", "is_superuser", "is_active", "blood_group")
    search_fields  = ("username", "email", "first_name", "last_name", "phone_number")
    ordering       = ("-date_register",)


# ---------------------------------------------------------------------------
# SpecializationAdmin
# ---------------------------------------------------------------------------

@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    """Специализации врачей."""

    list_display   = ("name", "description_short", "has_image")
    search_fields  = ("name", "description")
    ordering       = ("name",)

    @admin.display(description="Описание")
    def description_short(self, obj: Specialization) -> str:
        return (obj.description[:80] + "…") if len(obj.description) > 80 else obj.description

    @admin.display(description="Есть фото", boolean=True)
    def has_image(self, obj: Specialization) -> bool:
        return bool(obj.image)


# ---------------------------------------------------------------------------
# DoctorAdmin
# ---------------------------------------------------------------------------

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """Карточка врача со встроенным расписанием."""

    inlines        = [ScheduleInline]
    list_display   = (
        "get_full_name",
        "specialization",
        "experience_years",
        "price",
        "avg_rating",
        "appointment_count",
        "photo_preview",
    )
    list_filter    = ("specialization", "experience_years")
    search_fields  = (
        "first_name",
        "last_name",
        "patronymic",
        "specialization__name",
    )
    ordering       = ("last_name", "first_name")
    list_select_related = ("specialization",)

    @admin.display(description="ФИО")
    def get_full_name(self, obj: Doctor) -> str:
        return obj.get_full_name()

    @admin.display(description="Рейтинг")
    def avg_rating(self, obj: Doctor) -> str:
        rating = obj.get_avg_rating()
        return f"{rating} ★" if rating is not None else "—"

    @admin.display(description="Записей")
    def appointment_count(self, obj: Doctor) -> int:
        return obj.get_appointment_count()

    @admin.display(description="Фото")
    def photo_preview(self, obj: Doctor) -> str:
        if obj.photo:
            return format_html(
                '<img src="{}" style="height:40px; border-radius:4px;" />',
                obj.photo.url,
            )
        return "—"


# ---------------------------------------------------------------------------
# ScheduleAdmin
# ---------------------------------------------------------------------------

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    """Расписания (глобальный список)."""

    list_display  = ("doctor", "day_of_week", "start_time", "end_time")
    list_filter   = ("day_of_week", "doctor__specialization")
    search_fields = ("doctor__first_name", "doctor__last_name")
    ordering      = ("doctor", "day_of_week")
    list_select_related = ("doctor",)


# ---------------------------------------------------------------------------
# AppointmentAdmin
# ---------------------------------------------------------------------------

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Записи на приём со встроенной медицинской картой."""

    inlines        = [MedicalRecordInline]
    list_display   = (
        "id",
        "patient",
        "doctor",
        "date_time",
        "status",
        "created_date",
    )
    list_filter    = ("status", "date_time", "doctor__specialization")
    search_fields  = (
        "patient__username",
        "patient__first_name",
        "patient__last_name",
        "doctor__first_name",
        "doctor__last_name",
        "complaint",
    )
    ordering           = ("-date_time",)
    readonly_fields    = ("created_date",)
    list_select_related = ("patient", "doctor")
    date_hierarchy     = "date_time"

    fieldsets = (
        (
            "Информация о записи",
            {"fields": ("patient", "doctor", "date_time", "complaint", "status")},
        ),
        (
            "Служебные данные",
            {"fields": ("created_date",), "classes": ("collapse",)},
        ),
    )


# ---------------------------------------------------------------------------
# MedicalRecordAdmin
# ---------------------------------------------------------------------------

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    """Медицинские карты."""

    list_display   = ("id", "appointment", "diagnosis_short", "created_date")
    list_filter    = ("created_date",)
    search_fields  = (
        "appointment__patient__username",
        "appointment__patient__first_name",
        "appointment__patient__last_name",
        "appointment__doctor__last_name",
        "diagnosis",
    )
    ordering        = ("-created_date",)
    readonly_fields = ("created_date",)
    list_select_related = ("appointment__patient", "appointment__doctor")

    @admin.display(description="Диагноз")
    def diagnosis_short(self, obj: MedicalRecord) -> str:
        return (obj.diagnosis[:80] + "…") if len(obj.diagnosis) > 80 else obj.diagnosis


# ---------------------------------------------------------------------------
# DoctorReviewAdmin
# ---------------------------------------------------------------------------

@admin.register(DoctorReview)
class DoctorReviewAdmin(admin.ModelAdmin):
    """Отзывы пациентов о врачах."""

    list_display   = ("id", "patient", "doctor", "stars_display", "comment_short", "created_date")
    list_filter    = ("stars", "doctor__specialization", "created_date")
    search_fields  = (
        "patient__username",
        "patient__first_name",
        "patient__last_name",
        "doctor__first_name",
        "doctor__last_name",
        "comment",
    )
    ordering            = ("-created_date",)
    readonly_fields     = ("created_date",)
    list_select_related = ("patient", "doctor")

    @admin.display(description="Оценка")
    def stars_display(self, obj: DoctorReview) -> str:
        return "★" * obj.stars + "☆" * (5 - obj.stars)

    @admin.display(description="Комментарий")
    def comment_short(self, obj: DoctorReview) -> str:
        return (obj.comment[:80] + "…") if len(obj.comment) > 80 else obj.comment
