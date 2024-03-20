from django.db import models


class UserRole(models.Model):
    user = models.ForeignKey(
        to="idp_user.User", related_name="user_roles", on_delete=models.CASCADE
    )
    role = models.CharField(max_length=140)
    app_entities_restrictions = models.JSONField(
        null=True,
        help_text="This dictionary contains explicit restrictions about the app entities that the user can access, "
                  "in the form: {<entity_type>: [1, 2]}"
    )
    permission_restrictions = models.JSONField(
        default=dict,
        help_text="This dictionary contains explicit restrictions regarding app permissions, in the form: "
                  "{'perform_operation_1': {'entity_type': [1, 2]}, 'perform_operation_2': false}"
    )
    organization = models.CharField(
        max_length=140,
        null=True,
        help_text="The name of the organization the user role belongs to, if any."
    )

    class Meta:
        unique_together = [("user", "role")]
