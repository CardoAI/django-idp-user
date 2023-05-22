import logging
from datetime import datetime
from typing import Any, Type

from django.db import models

from idp_user.producer import Producer
from idp_user.settings import (
    APP_ENTITIES,
    APP_ENTITY_RECORD_EVENT_TOPIC,
    APP_IDENTIFIER,
)
from idp_user.utils.exceptions import UnsupportedAppEntityType
from idp_user.utils.typing import AppEntityRecordEventDict

logger = logging.getLogger(__name__)


class BaseUserService:
    @classmethod
    def send_app_entity_record_event_to_kafka(
        cls, app_entity_type: str, app_entity_record: Any, deleted=False
    ):
        app_entity_type_config = APP_ENTITIES[app_entity_type]

        event: AppEntityRecordEventDict = {
            "app_identifier": APP_IDENTIFIER,
            "app_entity_type": app_entity_type,
            "record_identifier": getattr(
                app_entity_record, app_entity_type_config["identifier_attr"]
            ),
            "label": getattr(app_entity_record, app_entity_type_config["label_attr"]),
            "deleted": deleted,
        }

        logger.info(f"Sending update {event}...")

        Producer().send_message(
            topic=APP_ENTITY_RECORD_EVENT_TOPIC, key=str(datetime.now()), data=event
        )

    @classmethod
    def _get_app_entity_type_from_model(cls, model: Type[models.Model]):
        for (
            app_entity_type,
            config,
        ) in APP_ENTITIES.items():  # type: str, AppEntityTypeConfig
            if config["model"] == model:
                return app_entity_type

        raise UnsupportedAppEntityType(model)

    @classmethod
    def process_app_entity_record_post_save(
        cls, sender: Type[models.Model], instance, **kwargs
    ):
        """
        Whenever an app entity record is saved (created/updated),
        send a message to Kafka to notify the IDP.

        kwargs are required for signal receivers.
        """

        cls.send_app_entity_record_event_to_kafka(
            app_entity_type=cls._get_app_entity_type_from_model(sender),
            app_entity_record=instance,
        )

    @classmethod
    def process_app_entity_record_post_delete(
        cls, sender: Type[models.Model], instance, **kwargs
    ):
        """
        Whenever an app entity record is deleted,
        send a message to Kafka to notify the IDP.

        kwargs are required for signal receivers.
        """

        cls.send_app_entity_record_event_to_kafka(
            app_entity_type=cls._get_app_entity_type_from_model(sender),
            app_entity_record=instance,
            deleted=True,
        )
