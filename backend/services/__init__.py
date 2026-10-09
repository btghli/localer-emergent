"""Mongo-backed provider cache + geographic cell key helpers."""
from __future__ import annotations
import math
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, List

from motor.motor_asyncio import AsyncIOMotorDatabase


def round_cell(lat: float, lng: float, digits: int = 2) -> tuple:
    """Round coordinates to a cell for cache-key purposes.

    digits=2 ≈ 1.1 km cell at the equator — good for landmark/food/nature.
    For news (city-level) we round to digits=1 (~11 km).
    """
    f = 10 ** digits
    return (round(lat * f) / f, round(lng * f) / f)


def _radius_bucket(radius_m: int) -> int:
    for b in (500, 1500, 3000, 7000, 15000, 30000):
        if radius_m <= b:
            return b
    return 60000


def make_key(provider: str, category: str, lat: float, lng: float, radius_m: int, digits: int = 2) -> str:
    cl, cg = round_cell(lat, lng, digits)
    return f"{provider}:{category}:{cl}:{cg}:{_radius_bucket(radius_m)}"


class ProviderCache:
    """Mongo cache. Each document is a {key, items, fetched_at, expires_at}."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["provider_cache"]

    async def get(self, key: str, allow_stale: bool = True) -> Optional[dict]:
        doc = await self.col.find_one({"_id": key})
        if not doc:
            return None
        now = datetime.now(timezone.utc)
        try:
            exp = datetime.fromisoformat(doc["expires_at"])
        except Exception:
            return None
        if exp > now:
            doc["stale"] = False
            return doc
        if allow_stale:
            doc["stale"] = True
            return doc
        return None

    async def set(self, key: str, items: List[dict], ttl_seconds: int) -> None:
        now = datetime.now(timezone.utc)
        await self.col.update_one(
            {"_id": key},
            {"$set": {
                "_id": key,
                "items": items,
                "fetched_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
            }},
            upsert=True,
        )
