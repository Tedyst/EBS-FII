import aio_pika
import rstream
from common import (
    AGGREGATION_STREAM,
    SUBSCRIPTIONS_STREAM,
    AppState,
    Publication,
)


async def clear_streams(appstate: AppState) -> None:
    async with rstream.Consumer(
        host=appstate.host,
        username=appstate.username,
        password=appstate.password,
    ) as consumer:
        await consumer.start()
        await consumer.delete_stream(stream=AGGREGATION_STREAM, missing_ok=True)
        await consumer.delete_stream(stream=SUBSCRIPTIONS_STREAM, missing_ok=True)


async def clear_queues(appstate: AppState) -> None:
    connection = await aio_pika.connect_robust(
        host=appstate.host,
        login=appstate.username,
        password=appstate.password,
        timeout=5,
    )

    async with connection:
        channel = await connection.channel()
        for field in Publication.fields():
            await channel.queue_delete("FILTER_" + field.upper())


async def clear_all(appstate: AppState) -> None:
    await clear_streams(appstate)
    await clear_queues(appstate)
    print("Cleared all streams and queues")
