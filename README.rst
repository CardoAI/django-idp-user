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
        "INJECT_HEADERS_IN_DEV": False
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

Settings Reference
------------------

* ``APP_IDENTIFIER``

  * The app identifier used in the OPA policy.

* ``ROLES``

  * The path to the roles choices.

* ``FAUST_APP_PATH``

  * The path to the Faust app.

* ``OPA_DOMAIN``

  * The OPA domain.

* ``OPA_VERSION``

  * The OPA version.

* ``IDP_URL``

  * The IDP URL.

* ``USE_REDIS_CACHE``

  * If True, the cache will be used
  * When developing locally, you can leave this as ``False``.

* ``INJECT_HEADERS_IN_DEV``

  * If True, the authentication headers will be injected in the response in development mode.
  * Unless you want to setup an IDP server locally for testing purposes,
    leave this as ``False`` when developing.
