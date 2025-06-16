import asyncio
from datetime import datetime
import random
from typing import cast
import aio_pika
from aio_pika.abc import AbstractQueue
from common import AppState, Publication, PublicationWithData
from tqdm.asyncio import tqdm


async def create_publications(appstate: AppState, count: int) -> None:
    connection = await aio_pika.connect(
        host=appstate.host,
        login=appstate.username,
        password=appstate.password,
    )
    queues: dict[str, AbstractQueue] = {}
    async with connection:
        channel = await connection.channel()
        for field in Publication.fields():
            q = await channel.declare_queue(
                name="FILTER_" + field.upper(), durable=True
            )
            queues[field] = q

        publications = [PublicationWithData.random() for _ in range(count)]

        async for index, publication in tqdm(enumerate(publications)):
            if index % 18 == 0:
                await asyncio.sleep(1)
            publication.timestamp = int(datetime.now().timestamp() * 1000)
            publication = cast(PublicationWithData, publication)
            start_field = random.choice(publication.remaining_filter_fields())
            await channel.default_exchange.publish(
                aio_pika.Message(body=publication.to_proto().SerializeToString()),
                routing_key="FILTER_" + start_field.upper(),
            )

        await channel.close()
        await connection.close()
