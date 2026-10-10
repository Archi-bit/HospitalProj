"""
Кастомный класс пагинации для Hospital REST API.

Расширяет стандартный PageNumberPagination:
  - Поддерживает GET-параметр ?page_size= для управления размером страницы.
  - Ограничивает максимальный размер (max_page_size) для защиты от злоупотреблений.
  - Возвращает count, next, previous и results — стандартный формат DRF.
"""
from rest_framework.pagination import PageNumberPagination


class FlexiblePageNumberPagination(PageNumberPagination):
    """
    Пагинация с поддержкой динамического page_size.

    Примеры запросов:
      GET /api/doctors/?page=2               — страница 2, размер из settings (10)
      GET /api/doctors/?page=1&page_size=5   — страница 1, по 5 элементов
      GET /api/specializations/?page_size=100 — все специализации одним запросом
    """

    # Имя GET-параметра для номера страницы
    page_query_param = "page"

    # Имя GET-параметра для переопределения размера страницы
    page_size_query_param = "page_size"

    # Максимальный разрешённый page_size (защита от слишком больших запросов)
    max_page_size = 200
