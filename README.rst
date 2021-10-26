===============
Django IDP User
===============

Quick start
-----------

1. Add "idp_user" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'idp_user',
    ]

2. Add the settings of the app in settings.py like this::

    APP_ENV = "development"/"staging"/"production"

    AUTH_USER_MODEL = 'idp_user.User'

    IDP_USER_APP = {
        "APP_IDENTIFIER": "str",
        "ROLES": "path.to.roles_choices",
        "FAUST_APP_PATH": "backend.kafka_consumer.app",
        "OPA_DOMAIN": os.getenv("OPA_DOMAIN"),
        "OPA_VERSION": os.getenv("OPA_VERSION"),
        "IDP_URL": os.getenv("IDP_URL"),
        "USE_REDIS_CACHE": True,
        "INJECT_HEADERS_IN_DEV": True
    }

    REST_FRAMEWORK = {
        'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema' / 'idp_user.schema_extensions.AutoSchemaWithRole',
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'idp_user.auth.AuthenticationBackend',
        ),
        'DEFAULT_PERMISSION_CLASSES': (
            'idp_user.auth.OpaCheckPermission',
        ),
    }

    SPECTACULAR_SETTINGS = {
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'idp_user.schema_extensions.BearerTokenScheme',
        ),
        'SERVE_AUTHENTICATION': ()
    }

3. Run ``python manage.py migrate`` to create the models.
