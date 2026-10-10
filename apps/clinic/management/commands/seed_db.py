"""
Management command: seed_db

Заполняет базу данных реалистичными тестовыми данными:
  - 8 специализаций
  - 20 врачей (2–3 на специализацию)
  - расписания для каждого врача (3–5 дней в неделю)
  - 1 суперпользователь-администратор
  - 15 пациентов
  - 40 записей на приём (разные статусы)
  - медицинские карты для completed-записей
  - 30 отзывов

Использование:
    python manage.py seed_db
    python manage.py seed_db --clear   # сначала очистить БД
"""
import random
from datetime import date, time, timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clinic.models import (
    Appointment,
    Doctor,
    DoctorReview,
    MedicalRecord,
    Schedule,
    Specialization,
    UserProfile,
)

# ───────────────────────────── справочники ──────────────────────────────────

SPECIALIZATIONS = [
    {
        "name": "Кардиолог",
        "description": (
            "Диагностика и лечение заболеваний сердечно-сосудистой системы: "
            "ИБС, гипертония, аритмии, сердечная недостаточность."
        ),
        "image_url": "https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=500&q=80",
    },
    {
        "name": "Хирург",
        "description": (
            "Оперативное лечение заболеваний органов брюшной полости, "
            "грыж, варикозного расширения вен."
        ),
        "image_url": "https://images.unsplash.com/photo-1551190822-a9333d879b1f?auto=format&fit=crop&w=500&q=80",
    },
    {
        "name": "Невролог",
        "description": (
            "Диагностика и лечение заболеваний нервной системы: "
            "мигрень, остеохондроз, инсульт, эпилепсия."
        ),
        "image_url": "https://images.unsplash.com/photo-1559757175-0eb30cd8c063?auto=format&fit=crop&w=500&q=80",
    },
    {
        "name": "Офтальмолог",
        "description": (
            "Диагностика и лечение болезней глаз: катаракта, глаукома, "
            "близорукость, дальнозоркость."
        ),
        "image_url": "https://images.unsplash.com/photo-1585435557343-3b092031a831?auto=format&fit=crop&w=500&q=80",
    },
    {
        "name": "Эндокринолог",
        "description": (
            "Лечение заболеваний эндокринной системы: сахарный диабет, "
            "болезни щитовидной железы, ожирение."
        ),
        "image_url": "https://images.unsplash.com/photo-1631815588090-d4bfec5b1ccb?auto=format&fit=crop&w=500&q=80",
    },
    {
        "name": "Ортопед",
        "description": (
            "Диагностика и лечение заболеваний опорно-двигательного аппарата: "
            "артрит, артроз, переломы, сколиоз."
        ),
        "image_url": "https://images.unsplash.com/photo-1530026405186-ed1f139313f8?auto=format&fit=crop&w=500&q=80",
    },
    {
        "name": "Дерматолог",
        "description": (
            "Диагностика и лечение кожных заболеваний: псориаз, экзема, "
            "акне, дерматиты, грибковые инфекции."
        ),
        "image_url": "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&w=500&q=80",
    },
    {
        "name": "Педиатр",
        "description": (
            "Медицинское обслуживание детей от рождения до 18 лет: "
            "профилактика, диагностика и лечение детских болезней."
        ),
        "image_url": "https://images.unsplash.com/photo-1581595219315-a187dd40c322?auto=format&fit=crop&w=500&q=80",
    },
]

# (фамилия, имя, отчество, опыт_лет, цена, photo_url)
DOCTORS = [
    # Кардиологи
    ("Соколов",    "Андрей",    "Владимирович", 18, "3500.00",
     "https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&w=500&q=80"),
    ("Морозова",   "Елена",     "Сергеевна",    12, "3200.00",
     "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=500&q=80"),
    ("Черников",   "Пётр",      "Александрович",25, "4500.00",
     "https://images.unsplash.com/photo-1537368910025-700350fe46c7?auto=format&fit=crop&w=500&q=80"),
    # Хирурги
    ("Волков",     "Дмитрий",   "Иванович",     20, "5000.00",
     "https://images.unsplash.com/photo-1594824476967-48c8b964273f?auto=format&fit=crop&w=500&q=80"),
    ("Зайцева",    "Ирина",     "Петровна",      9, "4200.00",
     "https://images.unsplash.com/photo-1582750433449-648ed127bb54?auto=format&fit=crop&w=500&q=80"),
    # Неврологи
    ("Лебедев",    "Сергей",    "Николаевич",   15, "3000.00",
     "https://images.unsplash.com/photo-1651008376811-b90baee60c1f?auto=format&fit=crop&w=500&q=80"),
    ("Орлова",     "Наталья",   "Викторовна",    7, "2800.00",
     "https://images.unsplash.com/photo-1638202993928-7267aad84c31?auto=format&fit=crop&w=500&q=80"),
    ("Громов",     "Михаил",    "Юрьевич",      22, "3800.00",
     "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&w=500&q=80"),
    # Офтальмологи
    ("Фёдорова",   "Светлана",  "Олеговна",     11, "2500.00",
     "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?auto=format&fit=crop&w=500&q=80"),
    ("Белов",      "Николай",   "Аркадьевич",   16, "2700.00",
     "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=500&q=80"),
    # Эндокринологи
    ("Новикова",   "Татьяна",   "Борисовна",    13, "3100.00",
     "https://images.unsplash.com/photo-1527613426441-4da17471b66d?auto=format&fit=crop&w=500&q=80"),
    ("Козлов",     "Артём",     "Денисович",     5, "2600.00",
     "https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&w=500&q=80"),
    # Ортопеды
    ("Павлова",    "Анна",      "Геннадьевна",  19, "3600.00",
     "https://images.unsplash.com/photo-1594824476967-48c8b964273f?auto=format&fit=crop&w=500&q=80"),
    ("Семёнов",    "Виктор",    "Михайлович",   28, "4800.00",
     "https://images.unsplash.com/photo-1537368910025-700350fe46c7?auto=format&fit=crop&w=500&q=80"),
    # Дерматологи
    ("Тихонова",   "Ольга",     "Васильевна",    8, "2400.00",
     "https://images.unsplash.com/photo-1582750433449-648ed127bb54?auto=format&fit=crop&w=500&q=80"),
    ("Родионов",   "Алексей",   "Сергеевич",    14, "2900.00",
     "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=500&q=80"),
    ("Кузнецова",  "Мария",     "Игоревна",      3, "2200.00",
     "https://images.unsplash.com/photo-1651008376811-b90baee60c1f?auto=format&fit=crop&w=500&q=80"),
    # Педиатры
    ("Захарова",   "Людмила",   "Павловна",     21, "2800.00",
     "https://images.unsplash.com/photo-1638202993928-7267aad84c31?auto=format&fit=crop&w=500&q=80"),
    ("Мельников",  "Евгений",   "Романович",    10, "2500.00",
     "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=500&q=80"),
    ("Степанова",  "Валерия",   "Константиновна",6, "2300.00",
     "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?auto=format&fit=crop&w=500&q=80"),
]

# Специализация → индексы врачей в списке DOCTORS (0-based)
SPEC_DOCTOR_MAP = {
    "Кардиолог":    [0, 1, 2],
    "Хирург":       [3, 4],
    "Невролог":     [5, 6, 7],
    "Офтальмолог":  [8, 9],
    "Эндокринолог": [10, 11],
    "Ортопед":      [12, 13],
    "Дерматолог":   [14, 15, 16],
    "Педиатр":      [17, 18, 19],
}

ALL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WORK_DAYS = ["mon", "tue", "wed", "thu", "fri"]

PATIENTS_DATA = [
    ("patient01", "Иван",      "Иванов",     "Семёнович",  "ivan@mail.ru",      "+7 900 111-11-11", "I+",   "1985-03-12"),
    ("patient02", "Мария",     "Петрова",    "Олеговна",   "maria@mail.ru",     "+7 900 222-22-22", "II+",  "1992-07-24"),
    ("patient03", "Алексей",   "Сидоров",    "Витальевич", "alexey@mail.ru",    "+7 900 333-33-33", "III-", "1978-11-05"),
    ("patient04", "Екатерина", "Смирнова",   "Юрьевна",    "kate@mail.ru",      "+7 900 444-44-44", "IV+",  "1995-01-30"),
    ("patient05", "Николай",   "Кузнецов",   "Павлович",   "nikolay@mail.ru",   "+7 900 555-55-55", "II-",  "1970-06-18"),
    ("patient06", "Анна",      "Попова",     "Сергеевна",  "anna@mail.ru",      "+7 900 666-66-66", "I-",   "2000-09-09"),
    ("patient07", "Дмитрий",   "Васильев",   "Романович",  "dima@mail.ru",      "+7 900 777-77-77", "III+", "1988-12-25"),
    ("patient08", "Светлана",  "Новикова",   "Игоревна",   "sveta@mail.ru",     "+7 900 888-88-88", "IV-",  "1975-04-03"),
    ("patient09", "Андрей",    "Морозов",    "Денисович",  "andrey@mail.ru",    "+7 900 999-99-99", "II+",  "1990-08-14"),
    ("patient10", "Ольга",     "Волкова",    "Борисовна",  "olga@mail.ru",      "+7 901 100-00-00", "I+",   "1983-05-22"),
    ("patient11", "Сергей",    "Лебедев",    "Аркадьевич", "sergey@mail.ru",    "+7 901 200-00-00", "II-",  "1967-02-17"),
    ("patient12", "Наталья",   "Козлова",    "Фёдоровна",  "natasha@mail.ru",   "+7 901 300-00-00", "I+",   "1998-10-07"),
    ("patient13", "Виктор",    "Орлов",      "Николаевич", "viktor@mail.ru",    "+7 901 400-00-00", "III+", "1955-07-31"),
    ("patient14", "Татьяна",   "Зайцева",    "Михайловна", "tatyana@mail.ru",   "+7 901 500-00-00", "IV+",  "2002-03-15"),
    ("patient15", "Павел",     "Белов",      "Евгеньевич", "pavel@mail.ru",     "+7 901 600-00-00", "II+",  "1980-11-28"),
]

COMPLAINTS = [
    "Боли в грудной клетке при нагрузке, одышка",
    "Головные боли, головокружение, повышение давления",
    "Боли в спине, онемение в руках",
    "Снижение остроты зрения, туман перед глазами",
    "Повышенная утомляемость, жажда, частое мочеиспускание",
    "Боли в суставах коленей, ограничение подвижности",
    "Сыпь на коже, зуд, шелушение",
    "Кашель, насморк, температура 37.5°C",
    "Плановый осмотр, профилактика",
    "Боли в животе, тошнота после еды",
    "Нарушение сна, раздражительность, тревога",
    "Боли в пояснице, прострел в ногу",
    "Покраснение глаз, слезотечение, светобоязнь",
    "Резкое снижение веса, потливость, дрожание рук",
    "Отёки ног, варикозное расширение вен",
    "Боли в сердце, перебои в работе сердца",
    "Плановая диспансеризация",
    "Контрольный осмотр после лечения",
]

DIAGNOSES = [
    ("ИБС. Стенокардия напряжения II ФК.",
     "Аспирин 75 мг/сут, Бисопролол 5 мг/сут, Аторвастатин 20 мг/сут. Контроль через 1 месяц."),
    ("Гипертоническая болезнь II стадии, 2 степень.",
     "Лизиноприл 10 мг/сут, Амлодипин 5 мг/сут. Контроль АД дважды в день. Диета с ограничением соли."),
    ("Остеохондроз шейного отдела позвоночника.",
     "Мелоксикам 15 мг 10 дней, физиотерапия 10 сеансов, ЛФК. Ношение воротника Шанца."),
    ("Миопия средней степени обоих глаз.",
     "Очковая коррекция -3.5 Д OD, -3.0 Д OS. Консультация по контактной коррекции."),
    ("Сахарный диабет 2 типа, целевой HbA1c < 7%.",
     "Метформин 1000 мг 2 р/д, диета №9. Самоконтроль гликемии. Консультация диетолога."),
    ("Гонартроз правого колена II стадии.",
     "Диклофенак 75 мг в/м 5 дней, Хондропротектор 3 месяца. ЛФК, ограничение нагрузки."),
    ("Псориаз бляшечный, ограниченный.",
     "Мометазон крем 2 р/д 2 недели, увлажняющий крем. Избегать стрессов и травм кожи."),
    ("ОРВИ. Острый ринофарингит.",
     "Парацетамол 500 мг при Т>38.5°C, промывание носа солевым раствором, обильное питьё."),
    ("Здоров. Плановый осмотр.",
     "Рекомендована диспансеризация через 1 год. Вакцинация согласно графику."),
    ("Хронический гастрит, обострение.",
     "Омепразол 20 мг 2 р/д 4 недели, диета №1. Исключить острое, алкоголь. ФГДС через 1 месяц."),
    ("Тревожно-депрессивное расстройство.",
     "Сертралин 50 мг/сут утром 3 месяца, консультация психотерапевта. Режим труда и отдыха."),
    ("Радикулопатия L5-S1 справа.",
     "Мелоксикам 15 мг/сут, Мидокалм 150 мг 3 р/д, эпидуральная блокада. МРТ позвоночника."),
]

REVIEW_COMMENTS = [
    "Отличный врач, всё подробно объяснил, назначил эффективное лечение.",
    "Очень внимательный специалист. Сразу поставил верный диагноз.",
    "Профессионал своего дела. Приём прошёл чётко и по делу.",
    "Спасибо доктору! Уже через неделю почувствовал себя значительно лучше.",
    "Хороший врач, но приём занял больше времени, чем ожидал.",
    "Доктор очень внимательна, выслушала все жалобы, назначила дополнительные обследования.",
    "Компетентный специалист с большим опытом. Рекомендую.",
    "Вежливый и грамотный доктор. Лечение помогло.",
    "Прекрасный специалист! Буду обращаться только к нему.",
    "Доктор всё понятно объяснил, не торопился, ответил на все вопросы.",
    "Нормальный приём, без лишних назначений.",
    "Очень довольна результатом лечения. Спасибо!",
]


class Command(BaseCommand):
    help = "Заполнить базу данных тестовыми данными"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Очистить все данные перед заполнением",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Очистка базы данных..."))
            DoctorReview.objects.all().delete()
            MedicalRecord.objects.all().delete()
            Appointment.objects.all().delete()
            Schedule.objects.all().delete()
            Doctor.objects.all().delete()
            Specialization.objects.all().delete()
            UserProfile.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS("База данных очищена.\n"))

        self._create_admin()
        specs   = self._create_specializations()
        doctors = self._create_doctors(specs)
        self._create_schedules(doctors)
        patients = self._create_patients()
        appointments = self._create_appointments(patients, doctors)
        self._create_medical_records(appointments)
        self._create_reviews(patients, doctors)

        self.stdout.write(self.style.SUCCESS("\n✅ База данных успешно заполнена!"))
        self.stdout.write(
            f"   Специализаций : {Specialization.objects.count()}\n"
            f"   Врачей        : {Doctor.objects.count()}\n"
            f"   Расписаний    : {Schedule.objects.count()}\n"
            f"   Пациентов     : {UserProfile.objects.filter(is_staff=False, is_superuser=False).count()}\n"
            f"   Записей       : {Appointment.objects.count()}\n"
            f"   Медкарт       : {MedicalRecord.objects.count()}\n"
            f"   Отзывов       : {DoctorReview.objects.count()}\n"
        )

    # ────────────────────────────── helpers ─────────────────────────────────

    def _create_admin(self):
        if not UserProfile.objects.filter(username="admin").exists():
            UserProfile.objects.create_superuser(
                username="admin",
                email="admin@hospital.ru",
                password="admin12345",
                first_name="Администратор",
                last_name="Системы",
            )
            self.stdout.write("  👤 Суперпользователь admin / admin12345 создан")
        else:
            self.stdout.write("  👤 Суперпользователь admin уже существует")

    def _create_specializations(self):
        self.stdout.write("  🏥 Создаю специализации...")
        specs = {}
        for data in SPECIALIZATIONS:
            spec, created = Specialization.objects.get_or_create(
                name=data["name"],
                defaults={"description": data["description"]},
            )
            specs[spec.name] = spec
            mark = "+" if created else "·"
            self.stdout.write(f"    {mark} {spec.name}")
        return specs

    def _create_doctors(self, specs: dict) -> list:
        self.stdout.write("  👨‍⚕️ Создаю врачей...")
        doctors = []
        for spec_name, indices in SPEC_DOCTOR_MAP.items():
            specialization = specs[spec_name]
            for idx in indices:
                last, first, patronymic, exp, price, _photo_url = DOCTORS[idx]
                doctor, created = Doctor.objects.get_or_create(
                    last_name=last,
                    first_name=first,
                    defaults={
                        "patronymic":       patronymic,
                        "experience_years": exp,
                        "price":            price,
                        "specialization":   specialization,
                    },
                )
                doctors.append(doctor)
                mark = "+" if created else "·"
                self.stdout.write(f"    {mark} {doctor.get_full_name()} — {spec_name}")
        return doctors

    def _create_schedules(self, doctors: list):
        self.stdout.write("  📅 Создаю расписания...")
        created_count = 0
        for doctor in doctors:
            # каждый врач работает 4–5 дней в неделю
            num_days   = random.randint(4, 5)
            work_days  = random.sample(WORK_DAYS, num_days)
            for day in work_days:
                # случайное время начала: 8:00 / 9:00 / 10:00
                hour_start = random.choice([8, 9, 10])
                # рабочий день 6–8 часов
                duration   = random.choice([6, 7, 8])
                start      = time(hour_start, 0)
                end        = time(hour_start + duration, 0)
                _, created = Schedule.objects.get_or_create(
                    doctor=doctor,
                    day_of_week=day,
                    defaults={"start_time": start, "end_time": end},
                )
                if created:
                    created_count += 1
        self.stdout.write(f"    + {created_count} слотов создано")

    def _create_patients(self) -> list:
        self.stdout.write("  🧑‍💼 Создаю пациентов...")
        patients = []
        hashed_pw = make_password("patient12345")
        for username, first, last, patronymic, email, phone, blood, birth_str in PATIENTS_DATA:
            user, created = UserProfile.objects.get_or_create(
                username=username,
                defaults={
                    "first_name":   first,
                    "last_name":    last,
                    "email":        email,
                    "password":     hashed_pw,
                    "phone_number": phone,
                    "blood_group":  blood,
                    "birth_date":   date.fromisoformat(birth_str),
                    "address":      f"г. Москва, ул. {last}а, д. {random.randint(1,99)}",
                },
            )
            patients.append(user)
            mark = "+" if created else "·"
            self.stdout.write(f"    {mark} {user.get_full_name()} ({username})")
        return patients

    def _create_appointments(self, patients: list, doctors: list) -> list:
        self.stdout.write("  📋 Создаю записи на приём...")
        now        = timezone.now()
        created_appointments = []

        # Генерируем 40 записей с разными статусами и датами
        appointment_configs = [
            # (статус,       дней_от_сегодня)  — отрицательное = прошлое
            (Appointment.Status.COMPLETED,  -30),
            (Appointment.Status.COMPLETED,  -25),
            (Appointment.Status.COMPLETED,  -20),
            (Appointment.Status.COMPLETED,  -18),
            (Appointment.Status.COMPLETED,  -15),
            (Appointment.Status.COMPLETED,  -14),
            (Appointment.Status.COMPLETED,  -12),
            (Appointment.Status.COMPLETED,  -10),
            (Appointment.Status.COMPLETED,   -9),
            (Appointment.Status.COMPLETED,   -8),
            (Appointment.Status.COMPLETED,   -7),
            (Appointment.Status.COMPLETED,   -6),
            (Appointment.Status.COMPLETED,   -5),
            (Appointment.Status.COMPLETED,   -4),
            (Appointment.Status.COMPLETED,   -3),
            (Appointment.Status.CANCELLED,  -20),
            (Appointment.Status.CANCELLED,  -10),
            (Appointment.Status.CANCELLED,   -5),
            (Appointment.Status.CANCELLED,   -2),
            (Appointment.Status.CONFIRMED,    2),
            (Appointment.Status.CONFIRMED,    3),
            (Appointment.Status.CONFIRMED,    4),
            (Appointment.Status.CONFIRMED,    5),
            (Appointment.Status.CONFIRMED,    6),
            (Appointment.Status.CONFIRMED,    7),
            (Appointment.Status.CONFIRMED,    8),
            (Appointment.Status.CONFIRMED,    9),
            (Appointment.Status.PENDING,     10),
            (Appointment.Status.PENDING,     11),
            (Appointment.Status.PENDING,     12),
            (Appointment.Status.PENDING,     13),
            (Appointment.Status.PENDING,     14),
            (Appointment.Status.PENDING,     15),
            (Appointment.Status.PENDING,     16),
            (Appointment.Status.PENDING,     17),
            (Appointment.Status.PENDING,     20),
            (Appointment.Status.PENDING,     22),
            (Appointment.Status.PENDING,     25),
            (Appointment.Status.PENDING,     28),
            (Appointment.Status.PENDING,     30),
        ]

        used_slots = set()  # (doctor_id, datetime) — защита от дублей

        for status, day_offset in appointment_configs:
            patient = random.choice(patients)
            doctor  = random.choice(doctors)

            # Выбираем уникальный временной слот
            for _ in range(20):  # до 20 попыток найти свободный слот
                hour     = random.choice([9, 10, 11, 12, 14, 15, 16, 17])
                dt       = (now + timedelta(days=day_offset)).replace(
                    hour=hour, minute=0, second=0, microsecond=0
                )
                slot_key = (doctor.pk, dt)
                if slot_key not in used_slots:
                    used_slots.add(slot_key)
                    break
            else:
                continue  # пропустить если не нашли свободный слот

            complaint = random.choice(COMPLAINTS)
            appt = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                date_time=dt,
                complaint=complaint,
                status=status,
            )
            created_appointments.append(appt)

        self.stdout.write(f"    + {len(created_appointments)} записей создано")
        return created_appointments

    def _create_medical_records(self, appointments: list):
        self.stdout.write("  🗂  Создаю медицинские карты...")
        count = 0
        completed = [a for a in appointments if a.status == Appointment.Status.COMPLETED]
        for appt in completed:
            if hasattr(appt, "medical_record"):
                continue
            diag, presc = random.choice(DIAGNOSES)
            MedicalRecord.objects.create(
                appointment=appt,
                diagnosis=diag,
                prescription=presc,
            )
            count += 1
        self.stdout.write(f"    + {count} медкарт создано")

    def _create_reviews(self, patients: list, doctors: list):
        self.stdout.write("  ⭐ Создаю отзывы...")
        count = 0
        # Берём пары пациент-врач из completed записей и добавляем отзывы
        completed_pairs = (
            Appointment.objects.filter(status=Appointment.Status.COMPLETED)
            .values_list("patient_id", "doctor_id")
            .distinct()
        )
        pairs_list = list(completed_pairs)
        random.shuffle(pairs_list)

        seen = set()
        for patient_id, doctor_id in pairs_list:
            if (patient_id, doctor_id) in seen:
                continue
            if DoctorReview.objects.filter(patient_id=patient_id, doctor_id=doctor_id).exists():
                seen.add((patient_id, doctor_id))
                continue

            # ~70% completed-пациентов оставляют отзыв
            if random.random() > 0.70:
                seen.add((patient_id, doctor_id))
                continue

            stars   = random.choices([3, 4, 5], weights=[1, 3, 6])[0]  # склонность к высоким
            comment = random.choice(REVIEW_COMMENTS)
            DoctorReview.objects.create(
                patient_id=patient_id,
                doctor_id=doctor_id,
                stars=stars,
                comment=comment,
            )
            seen.add((patient_id, doctor_id))
            count += 1

        self.stdout.write(f"    + {count} отзывов создано")
