import json

from aiokafka import AIOKafkaProducer
from django.core.serializers.json import DjangoJSONEncoder
from kafka import KafkaProducer

from idp_user.utils.classes import Singleton
from idp_user.utils.functions import get_kafka_bootstrap_servers


class Producer(metaclass=Singleton):
    __connection = None

    def __init__(self):
        self.__connection = KafkaProducer(
            bootstrap_servers=get_kafka_bootstrap_servers(include_uri_scheme=False),
            value_serializer=lambda v: json.dumps(v, cls=DjangoJSONEncoder).encode(
                "utf-8"
            ),
            api_version=(2, 6, 2),
        )

    def send_message(self, topic: str, key: str, data: dict):
        self.__connection.send(topic=topic, key=key.encode("utf-8"), value=data)
        # Sometimes messages do not get sent.
        # Flushing after each message seems to solve the issue
        self.__connection.flush()


class AioKafkaProducer:
    _producer = None

    async def get_producer(self):
        if self._producer is None:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=get_kafka_bootstrap_servers(include_uri_scheme=False),
                value_serializer=lambda v: json.dumps(v, cls=DjangoJSONEncoder).encode(
                    "utf-8"
                ),
            )
            await self._producer.start()
        return self._producer

    async def send_message(self, topic: str, key: str, data: dict):
        producer = await self.get_producer()
        await producer.send_and_wait(topic=topic, key=key.encode("utf-8"), value=data)

    async def close(self):
        await self._producer.stop()
