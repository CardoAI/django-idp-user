from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def check_idp_user_settings(*args, **kwargs):
    def verify_idp_user_app_attr_exists(_attr, error=False):
        if _attr not in settings.IDP_USER_APP:
            issue_kwargs = {
                "msg": f"Missing {_attr} in IDP_USER_APP.",
                "hint": f"You must declare the attribute {_attr} in the dict IDP_USER_APP in settings.py.",
                "obj": settings,
                "id": f"idp_user.{_attr}",
            }
            if error:
                issues.append(Error(**issue_kwargs))
            else:
                issues.append(Warning(**issue_kwargs))

    issues = []

    try:
        auth_user_model = settings.AUTH_USER_MODEL
        if auth_user_model != "idp_user.User":
            issues.append(
                Warning(
                    "Wrong AUTH_USER_MODEL.",
                    hint="You must set AUTH_USER_MODEL = 'idp_user.User' in settings.py.",
                    obj=settings,
                    id="idp_user.E002",
                )
            )

    except AttributeError:
        issues.append(
            Warning(
                "Missing AUTH_USER_MODEL",
                hint="You must set AUTH_USER_MODEL = 'idp_user.user' in settings.py.",
                obj=settings,
                id="idp_user.E003",
            )
        )

    try:
        for attr in ["IDP_ENVIRONMENT", "APP_IDENTIFIER", "FAUST_APP_PATH"]:
            verify_idp_user_app_attr_exists(attr, error=True)

        for attr in ["ROLES"]:
            verify_idp_user_app_attr_exists(attr, error=False)

    except AttributeError:
        issues.append(
            Error(
                "Missing IDP_USER_APP.",
                hint="You must declare the idp_user settings in the variable IDP_USER_APP in settings.py.",
                obj=settings,
                id="idp_user.E004",
            )
        )

    return issues
