"""Provider interface and shared helpers.

Each provider implements `fetch(ctx)` → list[NearbyItem]. Providers must:
- Never raise on third-party failure. Return [] and log a warning.
- Never fabricate titles, descriptions, dates, or coordinates.
- Namespace externalId as "<provider>:<providerItemId>".
"""
from __future__ import annotations
import abc
import logging
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from models import NearbyItem

logger = logging.getLogger("localer.providers")


@dataclass
class FetchContext:
    lat: float
    lng: float
    radius_m: int
    time_window_hours: int = 24 * 7  # 7 days
    locality: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None  # ISO-2 lowercase
    language: str = "en"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def new_id() -> str:
    return str(uuid.uuid4())


class Provider(abc.ABC):
    """Abstract provider — one external data source."""
    name: str = "base"
    categories: tuple = ()
    enabled_env_var: Optional[str] = None  # if set and env missing/empty, provider is disabled

    def is_enabled(self) -> bool:
        if not self.enabled_env_var:
            return True
        import os
        return bool(os.environ.get(self.enabled_env_var, "").strip())

    @abc.abstractmethod
    async def fetch(self, ctx: FetchContext) -> List[NearbyItem]:
        ...
