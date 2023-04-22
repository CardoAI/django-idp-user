try:
    import rest_framework  # noqa

    from idp_user.services.user import UserService  # noqa
except ImportError:
    from idp_user.services.async_user import UserServiceAsync  # noqa
