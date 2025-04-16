# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
from contextlib import asynccontextmanager

import aio_pika
import structlog
from aio_pika.abc import AbstractIncomingMessage

from sdtoolplus.config import AMQPSettings

logger = structlog.stdlib.get_logger()


class SDAMQP:
    def __init__(self, settings: AMQPSettings) -> None:
        self.settings = settings

    @asynccontextmanager
    async def lifespan(self):
        logger.info("Connecting to SD AMQP")
        try:
            connection = await aio_pika.connect_robust(
                url=self.settings.url,
                # ssl=True,
                # ssl_options=SSLOptions(
                #     cafile="cacert.pem",
                #     certfile="cert.pem",
                #     keyfile="key.pem",
                #     no_verify_ssl=ssl.CERT_REQUIRED,
                # ),
            )
        except Exception as e:
            raise ConnectionError("Failed to connect to SD AMQP") from e

        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        # Queue
        queue = await channel.get_queue("test_queue")


        print(1)
        await queue.consume(self.process_message, timeout=5)
        print(2)

        try:
            # Wait until terminate
            print(3)
            yield
        except BaseException as e:
            logger.exception("BASE")
            raise
        finally:
            print(4)
            await connection.close()

    async def process_message(self, message: AbstractIncomingMessage) -> None:
        print("process")
        # Requeue messages on exception so they can be retried
        async with message.process(requeue=True):
            try:
                print("process2")
                print(message.body)
                raise KeyError()
            except Exception as e:
                logger.exception("EPIC FAIL")
                await asyncio.sleep(5)
                raise
