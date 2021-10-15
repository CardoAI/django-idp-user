from django.db import models


class User(models.Model):
    idp_user_id = models.BigIntegerField(primary_key=True)
    email = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
