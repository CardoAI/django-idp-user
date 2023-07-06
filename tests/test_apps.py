from os import getenv

from django.apps import AppConfig


class AppTestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tests"
