# Django IDP User

[![pypi-badge]][pypi]
[![build-status-image]][build-status]
[![package-status]][repo]
[![github-last-commit]][repo]

---

## Installation

1. Install the package:
    ```
    pip install django-idp-user
    ```

    If you want to use the async version of the package, you can install it with the `async` extra:
    ```
    pip install django-idp-user[async]
    ```

2. Add `idp_user` to your `INSTALLED_APPS`:
    ```python
    INSTALLED_APPS = [
        # ...
        'idp_user',
    ]
    ```

3. Add the settings of the app in `settings.py` like this:
    ```python
    APP_ENV = "development" or "staging" or "production" or "demo"

    AUTH_USER_MODEL = 'idp_user.User'

    IDP_USER_APP = {
        "APP_IDENTIFIER": "str",
        "ROLES": "path.to.roles_choices",
        "FAUST_APP_PATH": "backend.kafka_consumer.app",
        "USE_REDIS_CACHE": True,
        "IDP_URL": "idp_url",  # Optional
        "APP_ENTITIES": {
            "<entity_type>": {
                "model": "<path.to.entity_type.model>",
                "identifier_attr": "<field_name>",
                "label_attr": "<field_name>",
            }
        },
        "CONSUMER_APP_ENV": "staging" or "production", # Optional
    }

    REST_FRAMEWORK = {
        'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema' or 'idp_user.schema_extensions.AutoSchemaWithRole',
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
    KAFKA_ARN = "<aws_kafka_arn>"  # Encoded in base64
    KAFKA_AWS_ACCESS_KEY_ID = "<access_key_id>"
    KAFKA_AWS_SECRET_ACCESS_KEY = "<secret_access_key_id>"  # Encoded in base64
    AWS_S3_REGION_NAME = "<region_name>"
   ```

4. Create the database tables for the app by running the following command:
    ```
    python manage.py migrate
    ```


## Async Support

Django version 4.1.1 is required for async support.

To use the async version of the package, you need to add the `async` extra when installing the package:
```
pip install django-idp-user[async]
```

If you are using Channels for websockets, you can use the `IDPChannelsAuthenticationMiddleware` like so:
```python
from channels.routing import ProtocolTypeRouter, URLRouter
from idp_user.auth import IDPChannelsAuthenticationMiddleware

application = ProtocolTypeRouter({
    "websocket": IDPChannelsAuthenticationMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                # ...
            )
        )
    ),
})
```


## Settings Reference

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


* ``APP_ENTITIES``


  * This dict links the AppEntityTypes declared on the IDP for this app to their actual models,
    so that they can be used for authorization purposes. In the value dicts, the attributes that will be
    used as the identifier and label are declared as well.


* ``CONSUMER_APP_ENV``

  * The environment of the Faust Kafka Consumer app.
  * If not set, the value of ``APP_ENV`` will be used.


[repo]: https://github.com/CardoAI/django-idp-user
[package-status]: https://img.shields.io/badge/package--status-production-green
[pypi]: https://pypi.org/project/django-idp-user/
[pypi-badge]: https://img.shields.io/badge/version-2.3.0
[github-last-commit]: https://img.shields.io/github/last-commit/CardoAI/django-idp-user
[build-status-image]: https://github.com/CardoAI/django-idp-user/actions/workflows/workflow.yml/badge.svg
[build-status]: https://github.com/CardoAI/django-idp-user/actions/workflows/workflow.yml