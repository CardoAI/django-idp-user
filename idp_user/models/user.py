from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class User(AbstractUser):
    is_demo = models.BooleanField(
        default=False, null=False, help_text="Whether this user is a demo user."
    )
    groups = models.ManyToManyField(
        Group,
        verbose_name="groups",
        blank=True,
        help_text=(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_name="idp_user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name="user permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="idp_user_set",
        related_query_name="user",
    )
