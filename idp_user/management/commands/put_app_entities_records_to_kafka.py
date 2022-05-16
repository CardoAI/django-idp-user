import logging

from django.core.management import BaseCommand

from idp_user.services import UserService
from idp_user.settings import APP_ENTITIES
from idp_user.typing import AppEntityTypeConfig

logger = logging.getLogger()


class Command(BaseCommand):
    help = 'Put the data of the app entities that are used in the scope of authorization in Kafka, ' \
           'so that the IDP is notified.'

    def handle(self, **options):
        logger.info("Putting data of vehicles...")

        for app_entity_type, config in APP_ENTITIES.items():  # type: str, AppEntityTypeConfig
            for record in config['model'].objects.all():
                UserService.send_app_entity_record_event_to_kafka(
                    app_entity_type=app_entity_type,
                    app_entity_record=record
                )
