from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    idp_user_id = models.BigIntegerField(primary_key=True)
