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

    IDP_USER_APP = {
        "APP_IDENTIFIER": "str",
        "ROLES": "path.to.roles_choices",
        "USE_LOCAL_IDP_IN_DEV": True,
        "USER_UPDATES_TOPIC_NAME": f"{APP_ENV}_user_updates",
        "FAUST_APP_PATH": "backend.kafka_consumer.app",
        "REGO_FILE_PATH": "path.to.rego.file",
        "OPA_DOMAIN": os.getenv("OPA_DOMAIN"),
        "OPA_VERSION": os.getenv("OPA_VERSION"),
        "IDP_URL": os.getenv("IDP_URL"),
        "USE_REDIS_CACHE": True,
        "ALLOWED_PATHS": ["/", "..."],
    }

3. Run ``python manage.py migrate`` to create the models.
