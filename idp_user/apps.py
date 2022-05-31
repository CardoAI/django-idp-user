from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_save, post_delete


class IDPUserConfig(AppConfig):
    name = "idp_user"

    def ready(self):
        # If Kafka is not configured, do not register signals
        is_kafka_configured = settings.KAFKA_ARN or settings.KAFKA_BROKER
        if not is_kafka_configured:
            return

        from idp_user.services import UserService
        from idp_user.settings import APP_ENTITIES
        from idp_user.typing import AppEntityTypeConfig

        for app_entity_type, config in APP_ENTITIES.items():  # type: str, AppEntityTypeConfig
            model = config['model']
            post_save.connect(
                receiver=UserService.process_app_entity_record_post_save,
                sender=model,
            )
            post_delete.connect(
                receiver=UserService.process_app_entity_record_post_delete,
                sender=model,
            )
