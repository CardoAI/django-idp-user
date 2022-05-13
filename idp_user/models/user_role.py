from django.db import models


class UserRole(models.Model):
    user = models.ForeignKey(to="idp_user.User", related_name="user_roles", on_delete=models.CASCADE)
    role = models.CharField(max_length=140)
    # This dictionary contains explicit restrictions about the app entities that the user can access, in the form:
    # {<entity_type>: [1, 2]}
    app_entities_restrictions = models.JSONField(null=True)
    # This dictionary contains explicit restrictions regarding app permissions, in the form:
    # {"perform_operation_1": {<entity_type>: [1, 2]}, "perform_operation_2": false}
    permission_restrictions = models.JSONField(default=dict)

    class Meta:
        unique_together = [('user', 'role')]
