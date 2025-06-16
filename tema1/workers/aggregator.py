import aio_pika
import rstream
from common import (
    AGGREGATION_STREAM,
    AppState,
    PublicationWithData,
    Subscription,
)
from aggregation import Aggregator
import pubsub_pb2


class AggregagtorWorker:
    def __init__(
        self,
        appstate: AppState,
        connection: aio_pika.abc.AbstractConnection,
    ) -> None:
        self.channel = None
        self.aggregator_consumer = rstream.Consumer(
            host=appstate.host,
            username=appstate.username,
            password=appstate.password,
        )
        self.aggregator = Aggregator()
        self.connection = connection

    async def process_aggregation_message(
        self, message: bytes, _: rstream.MessageContext
    ):
        if self.channel is None:
            self.channel = await self.connection.channel()
        parsed = pubsub_pb2.MatchedPublicationWithSubscription()
        parsed.ParseFromString(message)
        publication = PublicationWithData.from_proto(parsed.publication)
        subscription = Subscription.from_proto(parsed.subscription)

        matches: bool = self.aggregator.match(
            publication=publication, subscription=subscription
        )
        if not subscription.return_topic:
            print(
                f"Subscription {subscription.id} has no return topic. Skipping return publication."
            )
            return
        if matches:
            await self.channel.default_exchange.publish(
                aio_pika.Message(body=parsed.SerializeToString()),
                routing_key=subscription.return_topic,
                mandatory=True,
            )
            print(
                f"Sent matched aggregation by publication {publication} for subscription {subscription}"
            )

    async def aggregate_subscriptions(self):
        async with self.aggregator_consumer as consumer:
            await consumer.start()
            await consumer.create_stream(stream=AGGREGATION_STREAM, exists_ok=True)
            await consumer.subscribe(
                stream=AGGREGATION_STREAM,
                callback=self.process_aggregation_message,  # type: ignore
            )
            await consumer.run()


async def start_aggregation_worker(appstate, fields: list[str]) -> None:
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

    state = AggregagtorWorker(appstate, connection)
    print(f"Starting Aggregator Worker with fields: {fields}")
    await state.aggregate_subscriptions()
