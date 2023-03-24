import json
from django.core.serializers.json import DjangoJSONEncoder
from kafka import KafkaProducer
from aiokafka import AIOKafkaProducer
from django.conf import settings
from idp_user.utils.classes import Singleton
from idp_user.utils.functions import get_kafka_bootstrap_servers


class Producer(metaclass=Singleton):
    __connection = None

    def __init__(self):
        self.__connection = KafkaProducer(
            bootstrap_servers=get_kafka_bootstrap_servers(include_uri_scheme=False),
            value_serializer=lambda v: json.dumps(v, cls=DjangoJSONEncoder).encode('utf-8'),
            api_version=(2, 6, 2),
        )

    def send_message(self, topic: str, key: str, data: dict):
        self.__connection.send(
            topic=f"{settings.APP_ENV}_{topic}",
            key=key.encode('utf-8'),
            value=data
        )
        # Sometimes messages do not get sent.
        # Flushing after each message seems to solve the issue
        self.__connection.flush()


class AioKafkaProducer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def __aenter__(self):
        self._connection = AIOKafkaProducer(
            bootstrap_servers=get_kafka_bootstrap_servers(include_uri_scheme=False),
            value_serializer=lambda v: json.dumps(v, cls=DjangoJSONEncoder).encode('utf-8'),
            api_version=str((2, 6, 2)),
        )
        await self._connection.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._connection.stop()

    async def send_message(self, topic: str, key: str, data: dict):
        await self._connection.send_and_wait(
            topic=f"{settings.APP_ENV}_{topic}",
            key=key.encode('utf-8'),
            value=data
        )
