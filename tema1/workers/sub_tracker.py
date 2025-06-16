import asyncio
from typing import Mapping, Optional


import aio_pika
import rstream
import pubsub_pb2
from common import (
    SUBSCRIPTIONS_STREAM,
    AppState,
    Subscription,
)
from matching import BaseFilter


class SubscriptionTracker:
    def __init__(
        self,
        appstate: AppState,
        connection: aio_pika.abc.AbstractConnection,
        default_filters: Optional[Mapping[str, BaseFilter]] = None,
    ) -> None:
        self.default_filters: Mapping[str, BaseFilter] = default_filters or {}

        self.subscriptions: dict[int, Subscription] = {}
        self.subscriptions_lock = asyncio.Lock()

        self.subscription_tracker_consumer = rstream.Consumer(
            host=appstate.host,
            username=appstate.username,
            password=appstate.password,
        )

        self.topic_checker = connection
        self.topic_checker_channel = None

    async def add_subscription(self, subscription: Subscription) -> None:
        print(f"Adding subscription {subscription.id}")
        async with self.subscriptions_lock:
            self.subscriptions[subscription.id] = subscription
            for filter in self.default_filters.values():
                filter.add_subscription(subscription)

    async def remove_subscription(self, subscription: Subscription) -> None:
        print(f"Removing subscription {subscription.id}")
        async with self.subscriptions_lock:
            if subscription.id not in self.subscriptions:
                return
            del self.subscriptions[subscription.id]
            for filter in self.default_filters.values():
                filter.remove_subscription(subscription)

    async def filter_existant_topics(self, subscriptions: list[Subscription]):
        check_topics = set([s.return_topic for s in subscriptions if s.return_topic])
        if not check_topics:
            return []

        existant = set()
        for topic in check_topics:
            if (
                self.topic_checker_channel is None
                or self.topic_checker_channel.is_closed
            ):
                self.topic_checker_channel = await self.topic_checker.channel()

            try:
                await self.topic_checker_channel.declare_queue(
                    name=topic,
                    passive=True,
                )
                existant.add(topic)
            except aio_pika.exceptions.ChannelClosed as e:
                print(f"Queue {topic} does not exist, skipping")

        return [s for s in subscriptions if s.return_topic in existant]

    async def subscription_message_handler(
        self, message: bytes, _: rstream.MessageContext
    ):
        parsed = pubsub_pb2.SubscriptionMessage()
        parsed.ParseFromString(message)

        subs = [Subscription.from_proto(s) for s in parsed.subscriptions]
        subs = await self.filter_existant_topics(subs)
        if not subs:
            print("No valid subscriptions found, skipping")
            return
        if parsed.subscription_type == pubsub_pb2.SubscriptionType.SUBSCRIBE:
            print(f"Received {len(subs)} subscriptions to add")
            for s in subs:
                await self.add_subscription(s)
        else:
            print(f"Received {len(subs)} subscriptions to remove")
            for s in subs:
                await self.remove_subscription(s)

    async def track_subscriptions(self):
        async with self.subscription_tracker_consumer as consumer:
            await consumer.start()
            await consumer.create_stream(stream=SUBSCRIPTIONS_STREAM, exists_ok=True)
            await consumer.subscribe(
                stream=SUBSCRIPTIONS_STREAM,
                callback=self.subscription_message_handler,  # type: ignore
            )
            await consumer.run()
