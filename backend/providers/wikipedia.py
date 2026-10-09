"""Wikipedia landmark provider."""
from __future__ import annotations
import asyncio
import logging
from typing import List

import httpx

from models import NearbyItem
from providers import FetchContext, Provider, ProviderFetchError, now_iso, new_id

logger = logging.getLogger("localer.providers.wikipedia")

UA = "Localer/1.0 (https://localer.app; contact@localer.app)"


class WikipediaProvider(Provider):
    name = "wikipedia"
    categories = ("landmark",)

    def __init__(self, limit: int = 12):
        self.limit = limit

    async def fetch(self, ctx: FetchContext) -> List[NearbyItem]:
        radius = min(max(ctx.radius_m, 10), 10000)
        base = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{ctx.lat}|{ctx.lng}",
            "gsradius": radius,
            "gslimit": self.limit,
            "format": "json",
        }
        items: List[NearbyItem] = []
        try:
            async with httpx.AsyncClient(
                timeout=12.0,
                headers={"User-Agent": UA, "Accept": "application/json"},
            ) as hx:
                r = await hx.get(base, params=params)
                r.raise_for_status()
                data = r.json()
                pages = data.get("query", {}).get("geosearch", [])
                if not pages:
                    return []

                async def one(p):
                    try:
                        s = await hx.get(
                            f"https://en.wikipedia.org/api/rest_v1/page/summary/"
                            f"{p['title'].replace(' ', '_')}"
                        )
                        return p, (s.json() if s.status_code == 200 else {})
                    except Exception:
                        return p, {}

                detailed = await asyncio.gather(*[one(p) for p in pages])
                for p, d in detailed:
                    image = (d.get("thumbnail") or {}).get("source")
                    summary = d.get("extract")
                    if not summary:
                        # Skip pages that lack a usable abstract rather than fabricating.
                        continue
                    page_url = (
                        (d.get("content_urls") or {}).get("desktop", {}).get("page")
                        or f"https://en.wikipedia.org/wiki/{p['title'].replace(' ', '_')}"
                    )
                    items.append(NearbyItem(
                        id=new_id(),
                        externalId=f"wikipedia:{p['pageid']}",
                        providerItemId=str(p["pageid"]),
                        provider=self.name,
                        sourceName="Wikipedia",
                        sourceUrl=page_url,
                        canonicalUrl=page_url,
                        sourceType="wiki",
                        category="landmark",
                        title=p["title"],
                        summary=summary[:800],
                        latitude=p["lat"],
                        longitude=p["lon"],
                        locationPrecision="exact",
                        imageUrl=image,
                        imageIsFallback=False,
                        imageAttribution="Wikipedia" if image else None,
                        confidenceScore=0.9,
                        fetchedAt=now_iso(),
                    ))
        except Exception as e:
            logger.warning("wikipedia provider failed: %s", e)
            raise ProviderFetchError("Wikipedia request failed") from e
        return items
