from django.conf import settings

from .admin_authentication import IDPAuthBackend

if settings.IDP_USER_APP.get("ASYNC_MODE"):
    from .async_authentication import IDPChannelsAuthenticationMiddleware
else:
    from .authentication import AuthenticationBackend
