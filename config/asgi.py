"""
ASGI config for Hospital project.

Exposes the ASGI callable as a module-level variable named ``application``.
Compatible with Daphne, Uvicorn and other ASGI servers.

Example Uvicorn command:
    uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --workers 4
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
