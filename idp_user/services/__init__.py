import contextlib

with contextlib.suppress(ImportError):
    import rest_framework  # noqa
    from idp_user.services.user import UserService  # noqa
from idp_user.services.async_user import UserServiceAsync  # noqa
