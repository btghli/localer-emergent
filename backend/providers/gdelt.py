"""GDELT 2.1 DOC API — real news provider (no API key required).

API: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
Policy: ≤ 1 request / 5 seconds per client — enforced by an in-process
asyncio throttle. Combined with the Mongo cache, each (locality, time
window) is fetched at most once per TTL.

Local relevance is established by:
  1. Reverse-geocoding (lat, lng) → locality/country.
  2. Querying GDELT with the locality name AND sourcecountry filter.
  3. Scoring each article: title/body contains locality (+0.5), country
     matches (+0.2), fresh (+0.2), English language (+0.1).
  4. Dropping anything below confidenceScore 0.3 so we do not show
     weak hits as "local news".

Fabrication rules:
  - If locality cannot be resolved, return [].
  - If GDELT fails, return [].
  - No fake dates, no fake coordinates, no fake sources.
"""
from __future__ import annotations
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from models import NearbyItem
from providers import FetchContext, Provider, now_iso, new_id

logger = logging.getLogger("localer.providers.gdelt")

UA = "Mozilla/5.0 (compatible; LocalerBot/1.0; +https://localer.app)"
BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

_LOCK = asyncio.Lock()
_LAST: float = 0.0
_MIN_INTERVAL = 5.2  # seconds


async def _throttle():
    global _LAST
    async with _LOCK:
        gap = time.monotonic() - _LAST
        if gap < _MIN_INTERVAL:
            await asyncio.sleep(_MIN_INTERVAL - gap)
        _LAST = time.monotonic()


def _parse_seendate(s: str) -> Optional[str]:
    """GDELT seendate format: 20260109T143000Z → ISO 8601."""
    if not s or len(s) < 15:
        return None
    try:
        dt = datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return None


class GdeltNewsProvider(Provider):
    name = "gdelt"
    categories = ("news",)

    def __init__(self, max_records: int = 20, timespan: str = "2d"):
        self.max_records = max_records
        self.timespan = timespan  # e.g. "1d" "2d" "7d"

    async def fetch(self, ctx: FetchContext) -> List[NearbyItem]:
        if not ctx.locality:
            logger.info("gdelt: no locality resolved for %s,%s — skipping", ctx.lat, ctx.lng)
            return []

        locality = ctx.locality
        q_parts = [f'"{locality}"', "sourcelang:english"]
        if ctx.country_code and len(ctx.country_code) == 2:
            # GDELT uses lowercase 2-letter country codes
            q_parts.append(f"sourcecountry:{ctx.country_code}")
        query = " ".join(q_parts)

        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": self.max_records,
            "timespan": self.timespan,
            "sort": "DateDesc",
        }
        items: List[NearbyItem] = []
        await _throttle()
        try:
            async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": UA}) as hx:
                r = await hx.get(BASE, params=params)
                if r.status_code == 429:
                    logger.warning("gdelt 429 rate-limit")
                    return []
                if r.status_code != 200:
                    logger.warning("gdelt HTTP %s", r.status_code)
                    return []
                try:
                    data = r.json()
                except Exception:
                    logger.warning("gdelt returned non-JSON (possibly rate-limited)")
                    return []
                articles = (data or {}).get("articles") or []
                for a in articles:
                    itm = self._parse(a, ctx)
                    if itm:
                        items.append(itm)
        except Exception as e:
            logger.warning("gdelt fetch failed: %s", e)
        return items

    def _parse(self, a: dict, ctx: FetchContext) -> Optional[NearbyItem]:
        url = a.get("url") or a.get("url_mobile")
        title = a.get("title")
        if not url or not title:
            return None
        published = _parse_seendate(a.get("seendate", ""))
        if not published:
            return None
        domain = a.get("domain") or ""
        image = a.get("socialimage") or None
        lang = a.get("language", "") or ""
        sourcecc = (a.get("sourcecountry") or "").lower()

        # Local-relevance scoring
        text = (title or "").lower()
        score = 0.0
        if ctx.locality and ctx.locality.lower() in text:
            score += 0.5
        if ctx.region and ctx.region.lower() in text:
            score += 0.1
        if ctx.country and ctx.country.lower() in text:
            score += 0.1
        if ctx.country_code and sourcecc and ctx.country_code[:2].lower() == sourcecc[:2].lower():
            score += 0.2
        if lang.lower().startswith("eng"):
            score += 0.1
        # Freshness up to 0.1
        try:
            age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(published)).total_seconds() / 3600
            score += max(0.0, 0.1 * (1 - min(age_h, 48) / 48))
        except Exception:
            pass

        if score < 0.3:
            return None

        # News: coordinates only known at the city level
        lat = ctx.lat if ctx.locality else None
        lng = ctx.lng if ctx.locality else None

        return NearbyItem(
            id=new_id(),
            externalId=f"gdelt:{url}",
            providerItemId=url,
            provider=self.name,
            sourceName=domain or "Online publisher",
            sourceUrl=url,
            canonicalUrl=url,
            sourceType="news",
            category="news",
            title=title.strip(),
            summary=None,  # GDELT ArtList does not provide a trustworthy body excerpt
            latitude=lat,
            longitude=lng,
            locationPrecision="city",
            locality=ctx.locality,
            country=ctx.country,
            imageUrl=image,
            imageIsFallback=False,
            imageAttribution=domain if image else None,
            publishedAt=published,
            confidenceScore=min(1.0, round(score, 2)),
            fetchedAt=now_iso(),
        )
