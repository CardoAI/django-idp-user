from django.apps import AppConfig
from django.conf import settings


from django.db.models.signals import post_delete, post_save


class IDPUserConfig(AppConfig):
    name = "idp_user"

    def ready(self):
        # If Kafka is not configured, do not register signals
        is_kafka_configured = getattr(settings, "KAFKA_ARN", None) or getattr(
            settings, "KAFKA_BROKER", None
        )
        if not is_kafka_configured:
            return

        from idp_user.services.base_user import BaseUserService
        from idp_user.settings import APP_ENTITIES

        for (
            _app_entity_type,
            config,
        ) in APP_ENTITIES.items():
            model = config["model"]
            post_save.connect(
                receiver=BaseUserService.process_app_entity_record_post_save,
                sender=model,
            )
            post_delete.connect(
                receiver=BaseUserService.process_app_entity_record_post_delete,
                sender=model,
            )
