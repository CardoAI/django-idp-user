from django.conf import settings
from django.db import models

from django.utils.module_loading import import_string

ROLES = import_string(settings.IDP_USER_APP.get('ROLES'))


class UserRole(models.Model):
    user = models.ForeignKey(to="idp_user.User", related_name="user_roles", on_delete=models.CASCADE)
    role = models.CharField(choices=ROLES.as_list(), max_length=125)
    # This dictionary contains explicit restrictions regarding vehicle related features, in the form:
    # {"ViewDod": {"vehicle_ids": [1,2]}, "synchronizationDoD": False}
    app_config = models.JSONField(null=True)
    permission_restrictions = models.JSONField(default=dict)

    class Meta:
        unique_together = [('user', 'role')]
