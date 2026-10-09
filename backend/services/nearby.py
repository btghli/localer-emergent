"""Nearby orchestrator — validation, deduplication, ranking, caching."""
from __future__ import annotations
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase

from models import NearbyItem
from providers import FetchContext, Provider, distance_m
from providers.geocoder import Geocoder
from services import ProviderCache, make_key

logger = logging.getLogger("localer.services.nearby")

# Per-category TTL seconds
CATEGORY_TTL = {
    "news": 25 * 60,          # 25 min
    "event": 60 * 60,         # 1 h
    "landmark": 7 * 24 * 3600,  # 7 days
    "food": 24 * 3600,        # 1 day
    "nature": 24 * 3600,
}

# Cache cell precision (digits of lat/lng rounding)
CATEGORY_CELL = {
    "news": 1,       # ~11 km — city-level
    # Precise/venue content needs a finer cell. The UI offers a new search
    # after roughly 0.004 degrees of movement; 3 digits (~110 m latitude)
    # guarantees that such a move cannot silently reuse the previous area's
    # venue cache entry.
    "event": 3,
    "landmark": 3,
    "food": 3,
    "nature": 3,
}

AUTHORITY_WEIGHT = {
    "official": 1.0,
    "venue": 0.9,
    "ticketing": 0.85,
    "news": 0.75,
    "wiki": 0.8,
    "aggregator": 0.6,
    "osm": 0.7,
}


class NearbyService:
    def __init__(self, db: AsyncIOMotorDatabase, providers: List[Provider]):
        self.db = db
        self.cache = ProviderCache(db)
        self.geocoder = Geocoder(db)
        self.providers = providers

    async def nearby(
        self,
        lat: float,
        lng: float,
        radius_m: int = 3000,
        categories: Optional[Iterable[str]] = None,
    ) -> List[NearbyItem]:
        want: set = set(categories or ["landmark", "event", "news", "food", "nature"])

        # Resolve locality once per request (geocode layer caches 30d).
        rev = await self.geocoder.reverse(lat, lng)
        ctx = FetchContext(
            lat=lat, lng=lng, radius_m=radius_m,
            locality=rev.get("locality"),
            region=rev.get("region"),
            country=rev.get("country"),
            country_code=rev.get("country_code"),
        )

        # Figure out which providers to call.
        tasks = []
        provider_map: List[Tuple[Provider, List[str]]] = []
        for p in self.providers:
            overlap = [c for c in p.categories if c in want]
            if not overlap:
                continue
            provider_map.append((p, overlap))
            tasks.append(self._fetch_provider(p, ctx, overlap))

        all_results: List[NearbyItem] = []
        for res in await asyncio.gather(*tasks, return_exceptions=True):
            if isinstance(res, Exception):
                logger.warning("provider task raised: %s", res)
                continue
            all_results.extend(res)

        # Compute distance / finalize
        for it in all_results:
            if it.latitude is not None and it.longitude is not None:
                it.distanceMeters = distance_m(lat, lng, it.latitude, it.longitude)

        # Cached provider payloads are shared within a geographic cell. Apply
        # the exact request radius again after recomputing distance so a cache
        # hit cannot return precise venues that belong to the previous center.
        # City/region-level news coordinates are representative rather than
        # exact, so radius filtering them would incorrectly discard local news.
        all_results = [
            it for it in all_results
            if it.distanceMeters is None
            or it.locationPrecision in {"city", "region", "neighborhood"}
            or it.distanceMeters <= radius_m
        ]

        # Validation (category-specific)
        validated = [it for it in all_results if self._validate(it)]
        deduped = self._dedupe(validated)
        ranked = self._rank(deduped)
        return ranked[:60]

    async def _fetch_provider(self, provider: Provider, ctx: FetchContext, cats: List[str]) -> List[NearbyItem]:
        if not provider.is_enabled():
            logger.info("%s: disabled (missing %s)", provider.name, provider.enabled_env_var)
            return []

        # Cache per (provider, category-group). Many providers return multiple
        # categories; we key on the primary provider+category group.
        primary = cats[0]
        digits = CATEGORY_CELL.get(primary, 2)
        key = make_key(provider.name, "+".join(sorted(cats)), ctx.lat, ctx.lng, ctx.radius_m, digits)
        ttl = CATEGORY_TTL.get(primary, 1800)

        cached = await self.cache.get(key, allow_stale=True)
        if cached and not cached.get("stale"):
            return [NearbyItem(**d) for d in cached.get("items", [])]

        # Need a live fetch
        try:
            items = await provider.fetch(ctx)
        except Exception as e:
            logger.warning("%s fetch raised: %s", provider.name, e)
            items = []

        if items:
            await self.cache.set(key, [i.model_dump() for i in items], ttl)
            return items

        # Fallback to stale cache, marked
        if cached and cached.get("items"):
            logger.info("%s: live fetch empty, returning stale cache", provider.name)
            out = []
            for d in cached["items"]:
                try:
                    item = NearbyItem(**d)
                    item.stale = True
                    out.append(item)
                except Exception:
                    continue
            return out
        return []

    # ---- validation -------------------------------------------------
    @staticmethod
    def _validate(it: NearbyItem) -> bool:
        if not it.title or not it.sourceUrl or not it.externalId:
            return False
        # No fabricated search-engine URLs: external pages only.
        bad_hosts = ("google.com/search", "news.google.com/search", "www.google.com/search")
        if any(h in (it.sourceUrl or "") for h in bad_hosts):
            return False
        if it.category == "event":
            if not it.startsAt:
                return False
            if it.eventStatus == "cancelled":
                return False
            # Already-ended events (end + 6h grace)
            try:
                end = datetime.fromisoformat((it.endsAt or it.startsAt).replace("Z", "+00:00"))
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - end).total_seconds() > 6 * 3600:
                    return False
            except Exception:
                pass
        if it.category == "news":
            if not it.publishedAt:
                return False
            if (it.confidenceScore or 0) < 0.3:
                return False
        return True

    # ---- dedup ------------------------------------------------------
    @staticmethod
    def _normalize_title(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").strip().lower())

    def _dedupe(self, items: List[NearbyItem]) -> List[NearbyItem]:
        seen_ext = set()
        seen_canon = set()
        by_sig: Dict[str, NearbyItem] = {}
        out: List[NearbyItem] = []
        for it in items:
            if it.externalId in seen_ext:
                continue
            seen_ext.add(it.externalId)
            canon = it.canonicalUrl or it.sourceUrl
            if canon and canon in seen_canon:
                continue
            if canon:
                seen_canon.add(canon)
            sig_bits = [
                it.category,
                self._normalize_title(it.title),
                (it.venueName or "").lower(),
                (it.startsAt or "")[:10],
            ]
            sig = "|".join(sig_bits)
            if sig in by_sig:
                # Keep the higher-authority item
                incumbent = by_sig[sig]
                if AUTHORITY_WEIGHT.get(it.sourceType or "", 0) > AUTHORITY_WEIGHT.get(incumbent.sourceType or "", 0):
                    out = [x for x in out if x is not incumbent]
                    by_sig[sig] = it
                    out.append(it)
                continue
            by_sig[sig] = it
            out.append(it)
        return out

    # ---- ranking ----------------------------------------------------
    def _rank(self, items: List[NearbyItem]) -> List[NearbyItem]:
        def score(it: NearbyItem) -> float:
            s = 0.0
            # Distance (closer is better) — up to 40 points
            if it.distanceMeters is not None:
                s += 40 * max(0.0, 1 - min(it.distanceMeters, 15000) / 15000)
            else:
                s += 15
            # Confidence — up to 20
            s += 20 * (it.confidenceScore or 0.6)
            # Authority — up to 10
            s += 10 * AUTHORITY_WEIGHT.get(it.sourceType or "", 0.5)
            # Freshness / soon-ness — up to 20
            now = datetime.now(timezone.utc)
            if it.category == "event" and it.startsAt:
                try:
                    starts = datetime.fromisoformat(it.startsAt.replace("Z", "+00:00"))
                    if starts.tzinfo is None:
                        starts = starts.replace(tzinfo=timezone.utc)
                    hrs = (starts - now).total_seconds() / 3600
                    if 0 <= hrs <= 24 * 14:
                        s += 20 * (1 - hrs / (24 * 14))
                except Exception:
                    pass
            elif it.category == "news" and it.publishedAt:
                try:
                    pub = datetime.fromisoformat(it.publishedAt.replace("Z", "+00:00"))
                    if pub.tzinfo is None:
                        pub = pub.replace(tzinfo=timezone.utc)
                    age_h = (now - pub).total_seconds() / 3600
                    if age_h <= 48:
                        s += 20 * (1 - age_h / 48)
                except Exception:
                    pass
            # Penalties
            if it.stale:
                s -= 5
            if it.eventStatus == "postponed":
                s -= 3
            return s

        return sorted(items, key=score, reverse=True)
