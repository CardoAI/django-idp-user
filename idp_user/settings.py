from django.conf import settings
from django.utils.module_loading import import_string

ASYNC_MODE = settings.IDP_USER_APP.get("ASYNC_MODE", False)
APP_IDENTIFIER = settings.IDP_USER_APP["APP_IDENTIFIER"]
IN_DEV = settings.APP_ENV == "development"
ROLES = import_string(settings.IDP_USER_APP.get("ROLES"))
APP_ENTITIES = settings.IDP_USER_APP.get("APP_ENTITIES") or {}
TENANTS = settings.IDP_USER_APP.get("TENANTS") or list(settings.DATABASES.keys())
CONSUMER_APP_ENV = settings.IDP_USER_APP.get("CONSUMER_APP_ENV") or settings.APP_ENV

if APP_ENTITIES:
    for _, config_dict in APP_ENTITIES.items():
        config_dict["model"] = import_string(config_dict["model"])


APP_ENTITY_RECORD_EVENT_TOPIC = f"{CONSUMER_APP_ENV}_app_entity_record_events"

AWS_S3_REGION_NAME = getattr(settings, "AWS_S3_REGION_NAME", None) or "eu-central-1"
