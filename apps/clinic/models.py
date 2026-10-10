"""
Модели данных для медицинской клиники.

Иерархия:
    UserProfile  ←──── Appointment ────→ Doctor ←── Schedule
                             │                └──── DoctorReview
                             └─── MedicalRecord
"""
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg


# ---------------------------------------------------------------------------
# UserProfile — расширенная модель пользователя
# ---------------------------------------------------------------------------

class UserProfile(AbstractUser):
    """Пользователь системы (пациент или сотрудник клиники)."""

    class BloodGroup(models.TextChoices):
        I_POS   = "I+",   "I (0) Rh+"
        I_NEG   = "I-",   "I (0) Rh-"
        II_POS  = "II+",  "II (A) Rh+"
        II_NEG  = "II-",  "II (A) Rh-"
        III_POS = "III+", "III (B) Rh+"
        III_NEG = "III-", "III (B) Rh-"
        IV_POS  = "IV+",  "IV (AB) Rh+"
        IV_NEG  = "IV-",  "IV (AB) Rh-"

    birth_date    = models.DateField(null=True, blank=True, verbose_name="Дата рождения")
    phone_number  = models.CharField(max_length=20, blank=True, verbose_name="Телефон")
    address       = models.TextField(blank=True, verbose_name="Адрес")
    blood_group   = models.CharField(
        max_length=4,
        choices=BloodGroup.choices,
        blank=True,
        verbose_name="Группа крови",
    )
    date_register = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")

    class Meta:
        verbose_name        = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering            = ["-date_register"]

    def __str__(self) -> str:
        return f"{self.get_full_name() or self.username} ({self.email})"


# ---------------------------------------------------------------------------
# Specialization — специализация врача
# ---------------------------------------------------------------------------

class Specialization(models.Model):
    """Медицинская специализация (кардиолог, хирург и т.д.)."""

    name        = models.CharField(max_length=120, unique=True, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    image       = models.ImageField(
        upload_to="specializations/",
        null=True,
        blank=True,
        verbose_name="Изображение",
    )

    class Meta:
        verbose_name        = "Специализация"
        verbose_name_plural = "Специализации"
        ordering            = ["name"]

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# Doctor — врач
# ---------------------------------------------------------------------------

class Doctor(models.Model):
    """Врач клиники."""

    first_name       = models.CharField(max_length=100, verbose_name="Имя")
    last_name        = models.CharField(max_length=100, verbose_name="Фамилия")
    patronymic       = models.CharField(max_length=100, blank=True, verbose_name="Отчество")
    photo            = models.ImageField(
        upload_to="doctors/photos/",
        null=True,
        blank=True,
        verbose_name="Фото",
    )
    experience_years = models.PositiveIntegerField(default=0, verbose_name="Стаж (лет)")
    price            = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Стоимость приёма (₽)",
    )
    specialization   = models.ForeignKey(
        Specialization,
        on_delete=models.PROTECT,
        related_name="doctors",
        verbose_name="Специализация",
    )

    class Meta:
        verbose_name        = "Врач"
        verbose_name_plural = "Врачи"
        ordering            = ["last_name", "first_name"]

    def __str__(self) -> str:
        return self.get_full_name()

    def get_full_name(self) -> str:
        parts = [self.last_name, self.first_name]
        if self.patronymic:
            parts.append(self.patronymic)
        return " ".join(parts)

    def get_avg_rating(self) -> float | None:
        """Средняя оценка врача по всем отзывам. Возвращает None если отзывов нет."""
        result = self.reviews.aggregate(avg=Avg("stars"))["avg"]
        return round(result, 2) if result is not None else None

    def get_appointment_count(self) -> int:
        """Общее число записей к данному врачу."""
        return self.appointments.count()


# ---------------------------------------------------------------------------
# Schedule — расписание врача
# ---------------------------------------------------------------------------

class Schedule(models.Model):
    """Рабочее расписание врача по дням недели."""

    class DayOfWeek(models.TextChoices):
        MON = "mon", "Понедельник"
        TUE = "tue", "Вторник"
        WED = "wed", "Среда"
        THU = "thu", "Четверг"
        FRI = "fri", "Пятница"
        SAT = "sat", "Суббота"
        SUN = "sun", "Воскресенье"

    doctor     = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="schedules",
        verbose_name="Врач",
    )
    day_of_week = models.CharField(
        max_length=3,
        choices=DayOfWeek.choices,
        verbose_name="День недели",
    )
    start_time  = models.TimeField(verbose_name="Начало приёма")
    end_time    = models.TimeField(verbose_name="Конец приёма")

    class Meta:
        verbose_name        = "Расписание"
        verbose_name_plural = "Расписания"
        ordering            = ["doctor", "day_of_week"]
        # Один врач — не более одного слота на один день
        unique_together = [("doctor", "day_of_week")]

    def __str__(self) -> str:
        return (
            f"{self.doctor} | {self.get_day_of_week_display()} "
            f"{self.start_time:%H:%M}–{self.end_time:%H:%M}"
        )

    def clean(self) -> None:
        from django.core.exceptions import ValidationError
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError(
                {"end_time": "Время окончания приёма должно быть позже времени начала."}
            )


# ---------------------------------------------------------------------------
# Appointment — запись на приём
# ---------------------------------------------------------------------------

class Appointment(models.Model):
    """Запись пациента к врачу."""

    class Status(models.TextChoices):
        PENDING   = "pending",   "Ожидает подтверждения"
        CONFIRMED = "confirmed", "Подтверждена"
        CANCELLED = "cancelled", "Отменена"
        COMPLETED = "completed", "Завершена"

    patient      = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="appointments",
        verbose_name="Пациент",
    )
    doctor       = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="appointments",
        verbose_name="Врач",
    )
    date_time    = models.DateTimeField(verbose_name="Дата и время приёма")
    complaint    = models.TextField(verbose_name="Жалоба")
    status       = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус",
    )
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания записи")

    class Meta:
        verbose_name        = "Запись на приём"
        verbose_name_plural = "Записи на приём"
        ordering            = ["-date_time"]

    def __str__(self) -> str:
        return (
            f"{self.patient} → {self.doctor} "
            f"[{self.date_time:%d.%m.%Y %H:%M}] — {self.get_status_display()}"
        )


# ---------------------------------------------------------------------------
# MedicalRecord — медицинская карта по итогам приёма
# ---------------------------------------------------------------------------

class MedicalRecord(models.Model):
    """Медицинская карта, создаётся после завершения приёма."""

    appointment  = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name="medical_record",
        verbose_name="Запись на приём",
    )
    diagnosis    = models.TextField(verbose_name="Диагноз")
    prescription = models.TextField(verbose_name="Назначения / лечение")
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name        = "Медицинская карта"
        verbose_name_plural = "Медицинские карты"
        ordering            = ["-created_date"]

    def __str__(self) -> str:
        return f"Карта #{self.pk} | {self.appointment}"


# ---------------------------------------------------------------------------
# DoctorReview — отзыв о враче
# ---------------------------------------------------------------------------

class DoctorReview(models.Model):
    """Отзыв пациента о враче."""

    doctor       = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Врач",
    )
    patient      = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Пациент",
    )
    stars        = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Оценка (1–5)",
    )
    comment      = models.TextField(verbose_name="Комментарий")
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата отзыва")

    class Meta:
        verbose_name        = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering            = ["-created_date"]
        # Пациент может оставить только один отзыв конкретному врачу
        unique_together = [("doctor", "patient")]

    def __str__(self) -> str:
        return f"{'★' * self.stars} {self.patient} → {self.doctor}"
