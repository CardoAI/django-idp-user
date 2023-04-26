from django.conf import settings

if settings.IDP_USER_APP.get("ASYNC_MODE"):
    from idp_user.services.async_user import UserServiceAsync
else:
    from idp_user.services.user import UserService
