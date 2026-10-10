"""
WSGI config for Hospital project.

Exposes the WSGI callable as a module-level variable named ``application``.
Compatible with Gunicorn, uWSGI and other WSGI servers.

Example Gunicorn command:
    gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
