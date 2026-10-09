"""OpenStreetMap / Nominatim provider for Food and Nature.

Nominatim's public endpoint is NOT a high-frequency POI API; see
https://operations.osmfoundation.org/policies/nominatim/. This provider
therefore:

- Issues at most one request per sub-category, SERIALIZED with a global lock
  and 1-request-per-second throttle.
- Caches results in Mongo (handled by the service layer).
- Preserves "© OpenStreetMap contributors" attribution on every item.

For higher traffic, migrate to a self-hosted Overpass instance or a licensed
POI API. See README > Production Notes.
"""
from __future__ import annotations
import asyncio
import logging
import math
import time
from typing import List

import httpx

from models import NearbyItem
from providers import FetchContext, Provider, ProviderFetchError, now_iso, new_id

logger = logging.getLogger("localer.providers.osm")

UA = "Localer/1.0 (https://localer.app; contact@localer.app)"
BASE = "https://nominatim.openstreetmap.org/search"

_LOCK = asyncio.Lock()
_LAST_CALL: float = 0.0
_MIN_INTERVAL = 1.1  # seconds — honours Nominatim's 1 req/sec policy


async def _throttled_get(hx: httpx.AsyncClient, url: str, params: dict) -> dict:
    global _LAST_CALL
    async with _LOCK:
        gap = time.monotonic() - _LAST_CALL
        if gap < _MIN_INTERVAL:
            await asyncio.sleep(_MIN_INTERVAL - gap)
        _LAST_CALL = time.monotonic()
    r = await hx.get(url, params=params)
    if r.status_code == 429:
        logger.warning("nominatim 429 rate-limit")
        return {"__rate_limited": True}
    if r.status_code != 200:
        return {"__error": r.status_code}
    try:
        return {"__data": r.json()}
    except Exception:
        return {"__error": "parse"}


class OsmPoiProvider(Provider):
    """Food + Nature POI discovery via Nominatim named-query search."""
    name = "osm"
    categories = ("food", "nature")

    def __init__(self):
        # (query, category, locationPrecision)
        self.queries = [
            ("restaurant", "food", "venue"),
            ("cafe", "food", "venue"),
            ("park", "nature", "venue"),
        ]

    async def fetch(self, ctx: FetchContext) -> List[NearbyItem]:
        dlat = ctx.radius_m / 111000.0
        dlng = ctx.radius_m / (111000.0 * max(math.cos(math.radians(ctx.lat)), 0.1))
        viewbox = f"{ctx.lng - dlng},{ctx.lat + dlat},{ctx.lng + dlng},{ctx.lat - dlat}"

        out: List[NearbyItem] = []
        seen = set()
        successful_queries = 0
        try:
            async with httpx.AsyncClient(
                timeout=12.0,
                headers={"User-Agent": UA, "Accept": "application/json"},
            ) as hx:
                for q, cat, prec in self.queries:
                    r = await _throttled_get(hx, BASE, {
                        "q": q,
                        "format": "json",
                        "limit": 8,
                        "bounded": 1,
                        "viewbox": viewbox,
                        "addressdetails": 1,
                    })
                    if "__data" not in r:
                        continue
                    successful_queries += 1
                    for d in (r["__data"] or [])[:8]:
                        try:
                            osm_id = d.get("osm_id")
                            osm_type = d.get("osm_type", "node")
                            key = f"osm:{osm_type}:{osm_id}"
                            if key in seen:
                                continue
                            seen.add(key)
                            display = d.get("display_name", "") or ""
                            name = display.split(",")[0].strip() or q.title()
                            addr = d.get("address") if isinstance(d.get("address"), dict) else {}
                            locality = (addr or {}).get("city") or (addr or {}).get("town") or (addr or {}).get("village")
                            summary = f"{q.title()} — {display}" if display else name
                            out.append(NearbyItem(
                                id=new_id(),
                                externalId=key,
                                providerItemId=f"{osm_type}/{osm_id}",
                                provider=self.name,
                                sourceName="OpenStreetMap",
                                sourceUrl=f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                                canonicalUrl=f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                                sourceType="osm",
                                category=cat,
                                title=name,
                                summary=summary[:400],
                                latitude=float(d["lat"]),
                                longitude=float(d["lon"]),
                                locationPrecision=prec,
                                address=(addr or {}).get("road"),
                                locality=locality,
                                country=(addr or {}).get("country"),
                                imageUrl=None,
                                imageIsFallback=False,
                                imageAttribution="© OpenStreetMap contributors",
                                confidenceScore=0.75,
                                fetchedAt=now_iso(),
                            ))
                        except Exception:
                            continue
        except Exception as e:
            logger.warning("osm provider failed: %s", e)
            raise ProviderFetchError("OpenStreetMap request failed") from e
        if successful_queries == 0:
            raise ProviderFetchError("OpenStreetMap returned no successful responses")
        return out
