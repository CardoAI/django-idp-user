from django.db import models


class UserRole(models.Model):
    user = models.ForeignKey(to="idp_user.User", related_name="user_roles", on_delete=models.CASCADE)
    role = models.CharField(max_length=140)
    # This dictionary contains explicit restrictions regarding vehicle related features, in the form:
    # {"ViewDod": {"vehicle_ids": [1,2]}, "synchronizationDoD": False}
    app_config = models.JSONField(null=True)
    permission_restrictions = models.JSONField(default=dict)

    class Meta:
        unique_together = [('user', 'role')]
