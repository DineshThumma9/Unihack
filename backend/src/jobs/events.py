from __future__ import annotations

import json
from typing import Any
import redis.asyncio as aioredis
from config import settings

REDIS_URL = settings.REDIS_URL


class JobEventPublisher:
    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or REDIS_URL
        self._redis: aioredis.Redis | None = None

    async def get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def publish(self, job_id: str, event: dict[str, Any]) -> str:
        r = await self.get_redis()
        stream_key = f"job:{job_id}:events"
        # XADD key * data json_string
        event_id = await r.xadd(
            stream_key,
            {"data": json.dumps(event)},
            maxlen=2000,
        )
        return event_id

    async def close(self):
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
