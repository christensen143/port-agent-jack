import json
import logging

from confluent_kafka import Consumer, Message
from consumers.kafka_consumer import KafkaConsumer
from core.config import settings
from processors.kafka.kafka_to_webhook_processor import KafkaToWebhookProcessor
from streamers.base_streamer import BaseStreamer

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class KafkaStreamer(BaseStreamer):
    def __init__(self, consumer: Consumer = None) -> None:
        self.kafka_consumer = KafkaConsumer(self.msg_process, consumer)

    def msg_process(self, msg: Message) -> None:
        logger.info("Raw message value: %s", msg.value())
        msg_value = json.loads(msg.value().decode())
        topic = msg.topic()
        invocation_method = self.get_invocation_method(msg_value, topic)

        if not invocation_method.pop("agent", False):
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: not for agent",
                topic,
                msg.partition(),
                msg.offset(),
            )
            return

        # Check environment filtering if configured
        if settings.AGENT_ENVIRONMENTS:
            msg_environments = invocation_method.get("environment", [])
            # Handle both string and list formats
            if isinstance(msg_environments, str):
                msg_environments = [msg_environments]

            # Skip if no environment specified in message
            if not msg_environments:
                logger.info(
                    "Skip process message"
                    " from topic %s, partition %d, offset %d:"
                    " no environment specified and agent has environment filter",
                    topic,
                    msg.partition(),
                    msg.offset(),
                )
                return

            # Skip if message environment doesn't match agent's allowed environments
            if not any(env in settings.AGENT_ENVIRONMENTS for env in msg_environments):
                logger.info(
                    "Skip process message"
                    " from topic %s, partition %d, offset %d:"
                    " message environments %s not in allowed environments %s",
                    topic,
                    msg.partition(),
                    msg.offset(),
                    msg_environments,
                    settings.AGENT_ENVIRONMENTS,
                )
                return

        KafkaToWebhookProcessor.msg_process(msg, invocation_method, topic)

    @staticmethod
    def get_invocation_method(msg_value: dict, topic: str) -> dict:
        if topic == settings.KAFKA_RUNS_TOPIC:
            return (
                msg_value.get("payload", {})
                .get("action", {})
                .get("invocationMethod", {})
            )

        if topic == settings.KAFKA_CHANGE_LOG_TOPIC:
            return msg_value.get("changelogDestination", {})

        return {}

    def stream(self) -> None:
        self.kafka_consumer.start()
