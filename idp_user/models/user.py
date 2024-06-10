from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    is_demo = models.BooleanField(default=False, null=False, help_text='Whether this user is a demo user.')
