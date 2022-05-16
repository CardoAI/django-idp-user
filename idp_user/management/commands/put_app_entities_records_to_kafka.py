import logging
from datetime import datetime

from django.core.management import BaseCommand

from idp_user.producer import Producer
from idp_user.settings import APP_ENTITIES, APP_ENTITY_RECORD_EVENT_TOPIC, APP_IDENTIFIER
from idp_user.typing import AppEntityRecordEventDict, AppEntityTypeConfig

logger = logging.getLogger()


class Command(BaseCommand):
    help = 'Put the data of the app entities that are used in the scope of authorization in Kafka, ' \
           'so that the IDP is notified.'

    def handle(self, **options):
        logger.info("Putting data of vehicles...")

        producer = Producer()

        for app_entity_type, config in APP_ENTITIES.items():  # type: str, AppEntityTypeConfig
            for record in config['model'].objects.all():
                event: AppEntityRecordEventDict = {
                    'app_identifier': APP_IDENTIFIER,
                    'app_entity_type': app_entity_type,
                    'record_identifier': getattr(record, config['identifier_attr']),
                    'label': getattr(record, config['label_attr']),
                    'deleted': False
                }
                logger.info(f"Sending {event}")
                producer.send_message(
                    topic=APP_ENTITY_RECORD_EVENT_TOPIC,
                    key=str(datetime.now()),
                    data=event
                )
