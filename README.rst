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
        "USE_REDIS_CACHE": True,
        "IDP_URL": "idp_url",  # Optional
        "INJECT_HEADERS_IN_DEV": False,
        "APP_ENTITIES": {
            "<entity_type>": {
                "model_path": "<path.to.entity_type.model>",
                "identifier_attr": "<field_name>",
                "label_attr": "<field_name>",
            }
        },
    }

    REST_FRAMEWORK = {
        'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema' / 'idp_user.schema_extensions.AutoSchemaWithRole',
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'idp_user.auth.AuthenticationBackend',
        ),
    }

    SPECTACULAR_SETTINGS = {
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'idp_user.schema_extensions.BearerTokenScheme',
        ),
        'SERVE_AUTHENTICATION': ()
    }

    # Kafka Related
    KAFKA_ARN = "<aws_kafka_arn>"
    KAFKA_AWS_ACCESS_KEY_ID = "<access_key_id>"
    KAFKA_AWS_SECRET_ACCESS_KEY = "<secret_access_key_id>"
    AWS_S3_REGION_NAME = "<region_name>"

3. Run ``python manage.py migrate`` to create the models.

Settings Reference
------------------

* ``APP_IDENTIFIER``

  * The app identifier, as defined in the IDP.

* ``ROLES``

  * The path to the roles choices.

* ``FAUST_APP_PATH``

  * The path to the Faust app.

* ``IDP_URL``

  * The URL of the IDP, used for local development, or when using the IDP as an Authentication Backend.

* ``USE_REDIS_CACHE``

  * If True, the cache will be used
  * When developing locally, you can leave this as ``False``.

* ``INJECT_HEADERS_IN_DEV``

  * If True, the authentication headers will be injected in the response in development mode.
  * Unless you want to setup an IDP server locally for testing purposes,
    leave this as ``False`` when developing.

* ``APP_ENTITIES``

  * This dict links the AppEntityTypes declared on the IDP for this app to their actual models,
    so that they can be used for authorization purposes. In the value dicts, the attributes that will be
    used as the identifier and label are declared as well.
