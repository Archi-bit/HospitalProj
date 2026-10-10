"""
Сериализаторы DRF для Hospital REST API.

Соглашения об именовании:
  <Model>ReadSerializer  — для GET-ответов (вложенные объекты, SerializerMethodField).
  <Model>WriteSerializer — для POST/PUT/PATCH (PrimaryKeyRelatedField, валидация).

Где чтение и запись совпадают — используется единый <Model>Serializer.
"""
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Appointment,
    Doctor,
    DoctorReview,
    MedicalRecord,
    Schedule,
    Specialization,
    UserProfile,
)


# ===========================================================================
# Auth / UserProfile
# ===========================================================================

class RegisterSerializer(serializers.ModelSerializer):
    """Регистрация нового пациента. Пароль принимается дважды для подтверждения."""

    password  = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="Подтверждение пароля")

    class Meta:
        model  = UserProfile
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password2",
            "phone_number",
            "birth_date",
            "address",
            "blood_group",
        ]
        extra_kwargs = {
            "email":      {"required": True},
            "first_name": {"required": True},
            "last_name":  {"required": True},
        }

    def validate_password(self, value: str) -> str:  # noqa: D102
        validate_password(value)
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "Пароли не совпадают."})
        return attrs

    def create(self, validated_data: dict) -> UserProfile:
        password = validated_data.pop("password")
        user = UserProfile(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Профиль текущего пользователя (чтение и частичное обновление)."""

    class Meta:
        model  = UserProfile
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "birth_date",
            "phone_number",
            "address",
            "blood_group",
            "is_staff",
            "date_register",
        ]
        read_only_fields = ["id", "username", "is_staff", "date_register"]


# ===========================================================================
# Specialization
# ===========================================================================

class SpecializationSerializer(serializers.ModelSerializer):
    """Сериализатор специализации (используется и для чтения, и для записи)."""

    # Дефолтные изображения для специализаций (по индексу id % len)
    _SPEC_FALLBACK_IMAGES = [
        "https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=500&q=80",  # кардиология
        "https://images.unsplash.com/photo-1551190822-a9333d879b1f?auto=format&fit=crop&w=500&q=80",  # хирургия
        "https://images.unsplash.com/photo-1559757175-0eb30cd8c063?auto=format&fit=crop&w=500&q=80",  # неврология
        "https://images.unsplash.com/photo-1585435557343-3b092031a831?auto=format&fit=crop&w=500&q=80",  # офтальмология
        "https://images.unsplash.com/photo-1631815588090-d4bfec5b1ccb?auto=format&fit=crop&w=500&q=80",  # эндокринология
        "https://images.unsplash.com/photo-1530026405186-ed1f139313f8?auto=format&fit=crop&w=500&q=80",  # ортопедия
        "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&w=500&q=80",  # дерматология
        "https://images.unsplash.com/photo-1581595219315-a187dd40c322?auto=format&fit=crop&w=500&q=80",  # педиатрия
    ]

    image_url = serializers.SerializerMethodField()

    class Meta:
        model  = Specialization
        fields = ["id", "name", "description", "image", "image_url"]

    def get_image_url(self, obj: Specialization) -> str:
        """Возвращает URL изображения: загруженное или Unsplash-заглушка."""
        request = self.context.get("request")
        if obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        # Выбираем из списка по id специализации
        idx = (obj.id - 1) % len(self._SPEC_FALLBACK_IMAGES)
        return self._SPEC_FALLBACK_IMAGES[idx]


# ===========================================================================
# Schedule
# ===========================================================================

class ScheduleSerializer(serializers.ModelSerializer):
    """Расписание врача."""

    day_of_week_display = serializers.CharField(
        source="get_day_of_week_display", read_only=True
    )

    class Meta:
        model  = Schedule
        fields = [
            "id",
            "doctor",
            "day_of_week",
            "day_of_week_display",
            "start_time",
            "end_time",
        ]

    def validate(self, attrs: dict) -> dict:
        start = attrs.get("start_time") or getattr(self.instance, "start_time", None)
        end   = attrs.get("end_time")   or getattr(self.instance, "end_time",   None)
        if start and end and start >= end:
            raise serializers.ValidationError(
                {"end_time": "Время окончания должно быть позже времени начала."}
            )
        return attrs


# ===========================================================================
# Doctor
# ===========================================================================

class DoctorReadSerializer(serializers.ModelSerializer):
    """
    Чтение: полные вложенные данные о специализации, расписании,
    вычисляемые поля avg_rating и appointment_count.
    """

    # Набор профессиональных фото врачей с Unsplash (10 штук, выбор по id % 10)
    _DOCTOR_FALLBACK_PHOTOS = [
        "https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&w=500&q=80",
        "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=500&q=80",
        "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&w=500&q=80",
        "https://images.unsplash.com/photo-1594824476967-48c8b964273f?auto=format&fit=crop&w=500&q=80",
        "https://images.unsplash.com/photo-1582750433449-648ed127bb54?auto=format&fit=crop&w=500&q=80",
        "https://images.unsplash.com/photo-1651008376811-b90baee60c1f?auto=format&fit=crop&w=500&q=80",
        "https://images.unsplash.com/photo-1537368910025-700350fe46c7?auto=format&fit=crop&w=500&q=80",
        "https://images.unsplash.com/photo-1638202993928-7267aad84c31?auto=format&fit=crop&w=500&q=80",
        "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?auto=format&fit=crop&w=500&q=80",
        "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=500&q=80",
    ]

    specialization    = SpecializationSerializer(read_only=True)
    schedules         = ScheduleSerializer(many=True, read_only=True)
    avg_rating        = serializers.SerializerMethodField()
    appointment_count = serializers.SerializerMethodField()
    full_name         = serializers.SerializerMethodField()
    photo_url         = serializers.SerializerMethodField()

    class Meta:
        model  = Doctor
        fields = [
            "id",
            "full_name",
            "first_name",
            "last_name",
            "patronymic",
            "photo",
            "photo_url",
            "experience_years",
            "price",
            "specialization",
            "schedules",
            "avg_rating",
            "appointment_count",
        ]

    def get_avg_rating(self, obj: Doctor):  # noqa: ANN201
        return obj.get_avg_rating()

    def get_appointment_count(self, obj: Doctor) -> int:
        return obj.get_appointment_count()

    def get_full_name(self, obj: Doctor) -> str:
        return obj.get_full_name()

    def get_photo_url(self, obj: Doctor) -> str:
        """Возвращает URL фото: загруженное или детерминированная Unsplash-заглушка."""
        request = self.context.get("request")
        if obj.photo:
            return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url
        # Детерминированный выбор по id врача — один и тот же врач всегда получает одно фото
        idx = (obj.id - 1) % len(self._DOCTOR_FALLBACK_PHOTOS)
        return self._DOCTOR_FALLBACK_PHOTOS[idx]


class DoctorWriteSerializer(serializers.ModelSerializer):
    """Запись: принимает specialization по PK."""

    class Meta:
        model  = Doctor
        fields = [
            "id",
            "first_name",
            "last_name",
            "patronymic",
            "photo",
            "experience_years",
            "price",
            "specialization",
        ]

    def to_representation(self, instance: Doctor) -> dict:
        """После создания/обновления возвращаем полное представление."""
        return DoctorReadSerializer(instance, context=self.context).data


# ===========================================================================
# Appointment
# ===========================================================================

class AppointmentReadSerializer(serializers.ModelSerializer):
    """Чтение: вложенные данные о враче и краткий профиль пациента."""

    doctor  = DoctorReadSerializer(read_only=True)
    patient = UserProfileSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model  = Appointment
        fields = [
            "id",
            "patient",
            "doctor",
            "date_time",
            "complaint",
            "status",
            "status_display",
            "created_date",
        ]


class AppointmentWriteSerializer(serializers.ModelSerializer):
    """
    Создание записи пациентом.

    Валидация:
    - Нельзя записаться в прошлое.
    - Нельзя записаться, если у врача уже занят этот временной слот.
    """

    class Meta:
        model  = Appointment
        fields = ["id", "doctor", "date_time", "complaint"]

    def validate_date_time(self, value):  # noqa: ANN001, ANN201
        if value <= timezone.now():
            raise serializers.ValidationError(
                "Нельзя создать запись на прошедшее время."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        doctor    = attrs.get("doctor")
        date_time = attrs.get("date_time")

        if doctor and date_time:
            # Проверяем пересечение: у врача не должно быть записи на то же время
            # (статус cancelled исключаем как неактивные)
            conflict = Appointment.objects.filter(
                doctor=doctor,
                date_time=date_time,
            ).exclude(status=Appointment.Status.CANCELLED)

            # При обновлении исключаем саму себя
            if self.instance:
                conflict = conflict.exclude(pk=self.instance.pk)

            if conflict.exists():
                raise serializers.ValidationError(
                    {
                        "date_time": (
                            "Врач уже занят в указанное время. "
                            "Пожалуйста, выберите другой слот."
                        )
                    }
                )
        return attrs

    def create(self, validated_data: dict) -> Appointment:
        # Пациент берётся из контекста запроса (устанавливается во view)
        validated_data["patient"] = self.context["request"].user
        return super().create(validated_data)

    def to_representation(self, instance: Appointment) -> dict:
        return AppointmentReadSerializer(instance, context=self.context).data


class AppointmentStatusSerializer(serializers.ModelSerializer):
    """
    Смена статуса записи персоналом/врачом.
    Разрешённые переходы: pending→confirmed, confirmed→completed,
    pending|confirmed→cancelled.
    """

    ALLOWED_TRANSITIONS = {
        Appointment.Status.PENDING:   {
            Appointment.Status.CONFIRMED,
            Appointment.Status.CANCELLED,
        },
        Appointment.Status.CONFIRMED: {
            Appointment.Status.COMPLETED,
            Appointment.Status.CANCELLED,
        },
        # Из completed и cancelled переходов нет
        Appointment.Status.COMPLETED: set(),
        Appointment.Status.CANCELLED: set(),
    }

    class Meta:
        model  = Appointment
        fields = ["id", "status"]

    def validate_status(self, value: str) -> str:
        current = self.instance.status
        allowed = self.ALLOWED_TRANSITIONS.get(current, set())
        if value not in allowed:
            raise serializers.ValidationError(
                f"Переход из '{current}' в '{value}' недопустим. "
                f"Разрешённые переходы: {', '.join(allowed) or 'нет'}."
            )
        return value

    def to_representation(self, instance: Appointment) -> dict:
        return AppointmentReadSerializer(instance, context=self.context).data


# ===========================================================================
# MedicalRecord
# ===========================================================================

class MedicalRecordReadSerializer(serializers.ModelSerializer):
    """Чтение медкарты с вложенными данными о приёме."""

    appointment = AppointmentReadSerializer(read_only=True)

    class Meta:
        model  = MedicalRecord
        fields = [
            "id",
            "appointment",
            "diagnosis",
            "prescription",
            "created_date",
        ]


class MedicalRecordWriteSerializer(serializers.ModelSerializer):
    """
    Создание медицинской карты.

    Валидация:
    - Карту можно создать только для приёма со статусом completed.
      Если статус confirmed — автоматически переводим в completed.
    - Нельзя создать вторую карту для одной записи (OneToOneField).
    """

    class Meta:
        model  = MedicalRecord
        fields = ["id", "appointment", "diagnosis", "prescription"]

    def validate_appointment(self, appointment: Appointment) -> Appointment:
        # Проверяем, что карты ещё нет
        if hasattr(appointment, "medical_record"):
            raise serializers.ValidationError(
                "Медицинская карта для этого приёма уже существует."
            )
        # Разрешаем создание только для активных или завершённых записей
        if appointment.status == Appointment.Status.CANCELLED:
            raise serializers.ValidationError(
                "Нельзя создать медицинскую карту для отменённого приёма."
            )
        if appointment.status == Appointment.Status.PENDING:
            raise serializers.ValidationError(
                "Нельзя создать медицинскую карту: приём ещё не подтверждён."
            )
        return appointment

    def create(self, validated_data: dict) -> MedicalRecord:
        appointment = validated_data["appointment"]
        # Автоматически переводим статус приёма в completed при выписке карты
        if appointment.status != Appointment.Status.COMPLETED:
            appointment.status = Appointment.Status.COMPLETED
            appointment.save(update_fields=["status"])
        return super().create(validated_data)

    def to_representation(self, instance: MedicalRecord) -> dict:
        return MedicalRecordReadSerializer(instance, context=self.context).data


# ===========================================================================
# DoctorReview
# ===========================================================================

class DoctorReviewReadSerializer(serializers.ModelSerializer):
    """Чтение отзыва: вложенный краткий профиль пациента."""

    patient = UserProfileSerializer(read_only=True)

    class Meta:
        model  = DoctorReview
        fields = [
            "id",
            "doctor",
            "patient",
            "stars",
            "comment",
            "created_date",
        ]


class DoctorReviewWriteSerializer(serializers.ModelSerializer):
    """
    Создание отзыва.

    Валидация:
    - Оценка от 1 до 5.
    - Пациент не может оставить два отзыва одному врачу.
    """

    class Meta:
        model  = DoctorReview
        fields = ["id", "doctor", "stars", "comment"]

    def validate_stars(self, value: int) -> int:
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Оценка должна быть от 1 до 5.")
        return value

    def validate(self, attrs: dict) -> dict:
        patient = self.context["request"].user
        doctor  = attrs.get("doctor")
        if doctor and DoctorReview.objects.filter(doctor=doctor, patient=patient).exists():
            raise serializers.ValidationError(
                {"doctor": "Вы уже оставили отзыв этому врачу."}
            )
        return attrs

    def create(self, validated_data: dict) -> DoctorReview:
        validated_data["patient"] = self.context["request"].user
        return super().create(validated_data)

    def to_representation(self, instance: DoctorReview) -> dict:
        return DoctorReviewReadSerializer(instance, context=self.context).data
