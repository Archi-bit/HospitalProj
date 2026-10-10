"""
Фильтры django-filter для Hospital REST API.

DoctorFilter      — фильтрация по специализации, опыту, цене; поиск по ФИО.
AppointmentFilter — фильтрация по статусу, дате, врачу и пациенту.
DoctorReviewFilter — фильтрация по врачу, оценке и дате.
"""
import django_filters
from django.db.models import QuerySet

from .models import Appointment, Doctor, DoctorReview


# ---------------------------------------------------------------------------
# DoctorFilter
# ---------------------------------------------------------------------------

class DoctorFilter(django_filters.FilterSet):
    """
    Поддерживаемые параметры запроса:
      ?specialization=<id>
      ?experience_min=<int>        — стаж от N лет
      ?experience_max=<int>        — стаж до N лет
      ?price_min=<decimal>         — цена от
      ?price_max=<decimal>         — цена до
      ?search=<str>                — поиск по ФИО и названию специализации
                                     (обрабатывается SearchFilter во view,
                                      здесь оставлен для единства документации)
    """

    specialization = django_filters.NumberFilter(
        field_name="specialization__id",
        label="ID специализации",
    )
    specialization_name = django_filters.CharFilter(
        field_name="specialization__name",
        lookup_expr="icontains",
        label="Название специализации (частичное совпадение)",
    )
    experience_min = django_filters.NumberFilter(
        field_name="experience_years",
        lookup_expr="gte",
        label="Стаж от (лет)",
    )
    experience_max = django_filters.NumberFilter(
        field_name="experience_years",
        lookup_expr="lte",
        label="Стаж до (лет)",
    )
    price_min = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="gte",
        label="Цена от (₽)",
    )
    price_max = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="lte",
        label="Цена до (₽)",
    )

    class Meta:
        model  = Doctor
        fields = [
            "specialization",
            "specialization_name",
            "experience_min",
            "experience_max",
            "price_min",
            "price_max",
        ]


# ---------------------------------------------------------------------------
# AppointmentFilter
# ---------------------------------------------------------------------------

class AppointmentFilter(django_filters.FilterSet):
    """
    Поддерживаемые параметры запроса:
      ?status=pending|confirmed|cancelled|completed
      ?date_from=YYYY-MM-DD    — записи начиная с даты
      ?date_to=YYYY-MM-DD      — записи до даты
      ?doctor=<id>
      ?patient=<id>            — только для staff
    """

    status = django_filters.ChoiceFilter(
        choices=Appointment.Status.choices,
        label="Статус записи",
    )
    date_from = django_filters.DateFilter(
        field_name="date_time",
        lookup_expr="date__gte",
        label="Дата приёма от (YYYY-MM-DD)",
    )
    date_to = django_filters.DateFilter(
        field_name="date_time",
        lookup_expr="date__lte",
        label="Дата приёма до (YYYY-MM-DD)",
    )
    doctor = django_filters.NumberFilter(
        field_name="doctor__id",
        label="ID врача",
    )
    patient = django_filters.NumberFilter(
        field_name="patient__id",
        label="ID пациента (только для staff)",
    )

    class Meta:
        model  = Appointment
        fields = ["status", "date_from", "date_to", "doctor", "patient"]


# ---------------------------------------------------------------------------
# DoctorReviewFilter
# ---------------------------------------------------------------------------

class DoctorReviewFilter(django_filters.FilterSet):
    """
    Поддерживаемые параметры запроса:
      ?doctor=<id>
      ?stars=<1-5>
      ?stars_min=<1-5>
      ?stars_max=<1-5>
      ?created_from=YYYY-MM-DD
      ?created_to=YYYY-MM-DD
    """

    doctor = django_filters.NumberFilter(
        field_name="doctor__id",
        label="ID врача",
    )
    stars = django_filters.NumberFilter(
        field_name="stars",
        label="Точная оценка",
    )
    stars_min = django_filters.NumberFilter(
        field_name="stars",
        lookup_expr="gte",
        label="Оценка от",
    )
    stars_max = django_filters.NumberFilter(
        field_name="stars",
        lookup_expr="lte",
        label="Оценка до",
    )
    created_from = django_filters.DateFilter(
        field_name="created_date",
        lookup_expr="date__gte",
        label="Дата отзыва от",
    )
    created_to = django_filters.DateFilter(
        field_name="created_date",
        lookup_expr="date__lte",
        label="Дата отзыва до",
    )

    class Meta:
        model  = DoctorReview
        fields = [
            "doctor",
            "stars",
            "stars_min",
            "stars_max",
            "created_from",
            "created_to",
        ]
