import json
import logging
from collections import defaultdict, deque
from typing import Protocol

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class TickPublisher(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def publish(self, tick: dict) -> None: ...


class InMemoryTickPublisher:
    def __init__(self, buffer_size: int = 10000):
        self.counts: dict[str, int] = defaultdict(int)
        self._buffer: deque[dict] = deque(maxlen=buffer_size)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def publish(self, tick: dict) -> None:
        self._buffer.append(tick)
        self.counts[tick.get("symbol", "?")] += 1

    def recent(self, n: int = 10) -> list[dict]:
        return list(self._buffer)[-n:]


class RedisStreamPublisher:
    def __init__(self, redis_url: str, stream_key: str = "synchro:ticks"):
        self._redis_url = redis_url
        self._stream_key = stream_key
        self._redis: Redis | None = None
        self.counts: dict[str, int] = defaultdict(int)

    async def start(self) -> None:
        self._redis = Redis.from_url(self._redis_url, decode_responses=True)
        await self._redis.ping()
        logger.info("Redis publisher ready (stream=%s)", self._stream_key)

    async def stop(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def publish(self, tick: dict) -> None:
        if self._redis is None:
            raise RuntimeError("Publisher not started; call start() first")
        await self._redis.xadd(self._stream_key, {"json": json.dumps(tick)})
        self.counts[tick.get("symbol", "?")] += 1


def get_publisher(settings) -> TickPublisher:
    if settings.publisher_backend == "redis":
        return RedisStreamPublisher(settings.redis_url, settings.tick_stream_key)
    return InMemoryTickPublisher(settings.tick_buffer_size)
