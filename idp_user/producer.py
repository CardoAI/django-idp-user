import json

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from kafka import KafkaProducer

from idp_user.utils.classes import Singleton
from idp_user.utils.functions import get_kafka_bootstrap_servers


class Producer(metaclass=Singleton):
    __connection = None

    def __init__(self):
        self.__connection = KafkaProducer(
            bootstrap_servers=get_kafka_bootstrap_servers(include_uri_scheme=False),
            value_serializer=lambda v: json.dumps(v, cls=DjangoJSONEncoder).encode('utf-8'),
            api_version=(1, 0, 0)
        )

    def send_message(self, topic: str, key: str, data: dict):
        self.__connection.send(
            topic=f"{settings.APP_ENV}_{topic}",
            key=key.encode('utf-8'),
            value=data
        )
