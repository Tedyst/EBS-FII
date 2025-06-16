import asyncio
import rstream
import pubsub_pb2
from common import (
    SUBSCRIPTIONS_STREAM,
    AppState,
    ComparablePonder,
    PublicationWithData,
    Subscription,
    SubscriptionPonders,
)
import aio_pika


PONDERS = SubscriptionPonders(
    stationid=ComparablePonder(
        equality_ponder=0.6121335763499347, existance_ponder=0.7292710042118085
    ),
    city=ComparablePonder(equality_ponder=1, existance_ponder=0.7127223672318329),
    temp=ComparablePonder(
        equality_ponder=0.6018724372232028, existance_ponder=0.7770973878067571
    ),
    rain=ComparablePonder(
        equality_ponder=0.01188073999266237, existance_ponder=0.8010314666467584
    ),
    wind=ComparablePonder(
        equality_ponder=0.7221635296656853, existance_ponder=0.7216120497616565
    ),
    direction=ComparablePonder(equality_ponder=1, existance_ponder=0.7065752163739988),
    date=ComparablePonder(equality_ponder=0.50, existance_ponder=0.71008443873019977),
    rain_agg=ComparablePonder(equality_ponder=0.12, existance_ponder=0.123454),
    wind_agg=ComparablePonder(equality_ponder=0.234, existance_ponder=0.1324324),
    temp_agg=ComparablePonder(equality_ponder=0.324, existance_ponder=0.1),
)


async def create_subscriptions(appstate: AppState, count: int, return_topic: str):
    async with rstream.Producer(
        host=appstate.host,
        username=appstate.username,
        password=appstate.password,
    ) as producer:
        await producer.start()
        await producer.create_stream(stream=SUBSCRIPTIONS_STREAM, exists_ok=True)
        subscriptions = [
            Subscription.random(PONDERS, return_topic) for _ in range(count)
        ]
        print(subscriptions[0].return_topic)
        message = pubsub_pb2.SubscriptionMessage()
        message.subscription_type = pubsub_pb2.SubscriptionType.SUBSCRIBE
        for subscription in subscriptions:
            message.subscriptions.append(subscription.to_proto())
        await producer.send(
            stream=SUBSCRIPTIONS_STREAM,
            message=message.SerializeToString(),
        )
        return subscriptions


async def remove_subscriptions(
    appstate: AppState, subscriptions: list[Subscription]
) -> None:
    async with rstream.Producer(
        host=appstate.host,
        username=appstate.username,
        password=appstate.password,
    ) as producer:
        await producer.start()
        await producer.create_stream(stream=SUBSCRIPTIONS_STREAM, exists_ok=True)
        message = pubsub_pb2.SubscriptionMessage()
        message.subscription_type = pubsub_pb2.SubscriptionType.UNSUBSCRIBE
        for subscription in subscriptions:
            message.subscriptions.append(subscription.to_proto())
        await producer.send(
            stream=SUBSCRIPTIONS_STREAM,
            message=message.SerializeToString(),
        )


count = 0


async def finish_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    global count
    parsed = pubsub_pb2.MatchedPublicationWithSubscription()
    parsed.ParseFromString(message.body)
    count += 1
    publication = PublicationWithData.from_proto(parsed.publication)
    subscription = Subscription.from_proto(parsed.subscription)
    # if parsed.match_type == pubsub_pb2.MatchType.DIRECT:
    #     print(f"Received matched message {publication} for subscription {subscription}")
    # else:
    #     print(
    #         f"Received matched aggregation by publication {publication} for subscription {subscription}"
    #     )
    await message.ack()


async def print_message_count() -> None:
    global count
    while True:
        print(f"Processed {count} messages")
        await asyncio.sleep(10)


async def consumer_loop(appstate: AppState, count: int) -> None:
    async with await aio_pika.connect(
        host=appstate.host,
        login=appstate.username,
        password=appstate.password,
    ) as connection:
        subscriptions = []
        try:
            channel = await connection.channel()
            queue = await channel.declare_queue(
                name=None, durable=False, auto_delete=True
            )
            print(f"Created queue {queue.name} for consumer")
            subscriptions = await create_subscriptions(
                appstate, count=count, return_topic=queue.name
            )
            await queue.consume(finish_message, exclusive=True)
            print(f"Listening for messages on queue {queue.name}")
            asyncio.create_task(print_message_count())
            await asyncio.Future()
        except asyncio.CancelledError:
            print("Consumer loop cancelled, cleaning up...")
        finally:
            await remove_subscriptions(appstate, subscriptions)
