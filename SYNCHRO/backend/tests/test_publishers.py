import asyncio

from synchro.core.config import get_settings
from synchro.services.data_ingestion.publishers import (
    InMemoryTickPublisher,
    RedisStreamPublisher,
    get_publisher,
)


def test_in_memory_ring_buffer_respects_maxlen():
    publisher = InMemoryTickPublisher(buffer_size=3)

    async def feed():
        for i in range(5):
            await publisher.publish({"symbol": "R_75", "quote": i})

    asyncio.run(feed())
    assert len(publisher.recent()) == 3
    assert [t["quote"] for t in publisher.recent()] == [2, 3, 4]


def test_counts_per_symbol():
    publisher = InMemoryTickPublisher()

    async def feed():
        for _ in range(3):
            await publisher.publish({"symbol": "R_75"})
        for _ in range(2):
            await publisher.publish({"symbol": "frxEURUSD"})

    asyncio.run(feed())
    assert publisher.counts["R_75"] == 3
    assert publisher.counts["frxEURUSD"] == 2


def test_factory_defaults_to_memory():
    settings = get_settings()
    assert isinstance(get_publisher(settings), InMemoryTickPublisher)


def test_factory_redis_backend():
    settings = get_settings()
    settings.publisher_backend = "redis"
    assert type(get_publisher(settings)) is RedisStreamPublisher
