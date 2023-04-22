try:
    import rest_framework

    from .authentication import AuthenticationBackend, IDPAuthBackend
except ImportError:
    from .async_authentication import IDPChannelsAuthenticationMiddleware
