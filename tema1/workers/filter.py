import asyncio
import datetime
import random

from aio_pika.abc import AbstractConnection
import aio_pika
import rstream
import pubsub_pb2
from common import (
    AGGREGATION_STREAM,
    AppState,
    PublicationWithData,
    Subscription,
)
from matching import AllComparableFilter
from .sub_tracker import SubscriptionTracker


class FilterWorker(SubscriptionTracker):
    def __init__(
        self,
        appstate: AppState,
        default_filters: dict[str, AllComparableFilter],
        connection: AbstractConnection,
    ) -> None:
        super().__init__(appstate, connection, default_filters)
        self.filter_connection = connection
        self.channel = None
        self.aggregation_producer = rstream.Producer(
            host=appstate.host,
            username=appstate.username,
            password=appstate.password,
        )

        self.message_count = 0
        self.message_delay_total = 0

    async def start_finish_producer(self):
        await self.aggregation_producer.start()
        await self.aggregation_producer.create_stream(
            stream=AGGREGATION_STREAM, exists_ok=True
        )

    async def print_message_count(self):
        while True:
            print(
                f"Processed {self.message_count} messages. Average delay: "
                f"{self.message_delay_total / self.message_count if self.message_count > 0 else 0:.2f} ms"
            )
            await asyncio.sleep(10)

    async def finish_matching(self, publication: PublicationWithData):
        if self.channel is None:
            self.channel = await self.filter_connection.channel(publisher_confirms=True)
        for sub in publication.remaining_subscriptions:
            subscription = self.subscriptions.get(sub)
            if subscription is None:
                print(f"Subscription {sub} not found in state")
                continue

            if not subscription.return_topic:
                print(
                    f"Subscription {subscription.id} has no return topic. Skipping return publication."
                )
                continue

            self.message_count += 1
            self.message_delay_total += (
                datetime.datetime.now().timestamp() * 1000 - publication.timestamp
            )

            if not subscription.enabled_aggregation_fields():
                await self.channel.default_exchange.publish(
                    aio_pika.Message(
                        body=pubsub_pb2.MatchedPublicationWithSubscription(
                            publication=publication.to_proto(without_metadata=True),
                            subscription=subscription.to_proto(),
                            match_type=pubsub_pb2.MatchType.DIRECT,
                        ).SerializeToString()
                    ),
                    routing_key=subscription.return_topic,
                    mandatory=True,
                )
                # print(
                #     f"Sent publication {publication} to subscription {subscription} on topic {subscription.return_topic}"
                # )
            else:
                await self.aggregation_producer.send(
                    AGGREGATION_STREAM,
                    pubsub_pb2.MatchedPublicationWithSubscription(
                        publication=publication.to_proto(without_metadata=True),
                        subscription=subscription.to_proto(),
                        match_type=pubsub_pb2.MatchType.AGGREGATION,
                    ).SerializeToString(),
                )
                # print(
                #     f"Sent publication {publication} to subscription {subscription} for aggregation"
                # )

    async def send_to_further_processing(
        self, publication: PublicationWithData, field: str
    ):
        if self.channel is None:
            self.channel = await self.filter_connection.channel(publisher_confirms=True)
        await self.channel.default_exchange.publish(
            aio_pika.Message(body=publication.to_proto().SerializeToString()),
            routing_key="FILTER_" + field.upper(),
            mandatory=True,
        )

    async def process_publication(self, field: str, message: bytes):
        parsed = pubsub_pb2.Publication()
        parsed.ParseFromString(message)
        publication = PublicationWithData.from_proto(parsed)
        filters = None
        if getattr(publication, field) is None or field not in self.default_filters:
            random_field = random.choice(publication.remaining_filter_fields())
            print(
                f"Field {field} not found in publication. Sending to {random_field} instead."
            )
            return await self.send_to_further_processing(publication, random_field)
        if publication.all_subscriptions:
            async with self.subscriptions_lock:
                filters = self.default_filters[field]
        else:
            filters = AllComparableFilter(field)
            for sub_id in publication.remaining_subscriptions:
                if sub_id in self.subscriptions:
                    filters.add_subscription(self.subscriptions[sub_id])
                else:
                    print(f"Subscription {sub_id} not found in state")
                    return

        remaining_subs = filters.match(publication)

        publication.parsed_fields.append(field)
        remaining_fields = publication.remaining_filter_fields()

        if not remaining_fields:
            return await self.finish_matching(publication)
        random_field = remaining_fields.pop()
        publication.all_subscriptions = False
        publication.remaining_subscriptions = [
            sub.id for sub in remaining_subs if sub.id in self.subscriptions
        ]
        if len(publication.remaining_subscriptions) == 0:
            return

        await self.send_to_further_processing(publication, random_field)

    async def receive_publications_field(self, field: str):
        channel = await self.filter_connection.channel(publisher_confirms=False)
        queue = await channel.declare_queue("FILTER_" + field.upper(), durable=True)
        async with channel:
            async for message in queue.iterator():
                async with message.process():
                    await self.process_publication(field, message.body)

    async def receive_publications(self):
        print("Waiting for RabbitMQ to sync subscriptions...")
        await asyncio.sleep(5)

        async with self.filter_connection:
            tasks = [
                asyncio.create_task(self.receive_publications_field(field))
                for field in self.default_filters.keys()
            ]
            await asyncio.gather(*tasks)
            await self.filter_connection.close()


async def start_filter_worker(appstate, fields: list[str]) -> None:
    if "all" in fields and len(fields) == 1:
        fields = Subscription.fields()
    for field in fields:
        if field not in Subscription.fields():
            raise ValueError(f"Field {field} is not a valid field")

    connection = await aio_pika.connect_robust(
        host=appstate.host,
        login=appstate.username,
        password=appstate.password,
        timeout=5,
    )

    state = FilterWorker(
        appstate,
        default_filters={field: AllComparableFilter(field) for field in fields},
        connection=connection,
    )
    print(f"Starting filter worker with fields: {fields}")
    await asyncio.gather(
        state.print_message_count(),
        state.start_finish_producer(),
        state.track_subscriptions(),
        state.receive_publications(),
    )
