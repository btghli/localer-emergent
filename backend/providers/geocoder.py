"""Geocoding utilities.

- forward(q): Photon primary, Nominatim fallback.
- reverse(lat, lng): Nominatim reverse (locality/region/country/cc).

Both are cached in Mongo via the geocode_cache collection.
"""
from __future__ import annotations
import asyncio
import hashlib
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("localer.providers.geocoder")

UA = "Localer/1.0 (https://localer.app; contact@localer.app)"
_REV_LOCK = asyncio.Lock()
_REV_LAST: float = 0.0


class GeocoderFetchError(RuntimeError):
    """No geocoding source produced an authoritative response."""


async def _throttle_rev():
    global _REV_LAST
    async with _REV_LOCK:
        gap = time.monotonic() - _REV_LAST
        if gap < 1.1:
            await asyncio.sleep(1.1 - gap)
        _REV_LAST = time.monotonic()


class Geocoder:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["geocode_cache"]

    async def forward(self, q: str) -> list:
        q = (q or "").strip()
        if not q:
            return []
        key = hashlib.sha256(f"fwd:{q.lower()}".encode()).hexdigest()
        doc = await self.col.find_one({"_id": key})
        if doc and doc.get("expires_at", "") > datetime.now(timezone.utc).isoformat():
            return doc["results"]

        results = []
        successful_response = False
        try:
            async with httpx.AsyncClient(
                timeout=10.0, headers={"User-Agent": UA, "Accept": "application/json"},
            ) as hx:
                r = await hx.get("https://photon.komoot.io/api", params={"q": q, "limit": 7})
                if r.status_code != 200:
                    raise GeocoderFetchError(f"Photon HTTP {r.status_code}")
                data = r.json()
                successful_response = True
                for f in data.get("features", []):
                    try:
                        coords = f["geometry"]["coordinates"]
                        props = f.get("properties", {})
                        bits = [props.get("name") or ""]
                        for k in ("city", "state", "country"):
                            v = props.get(k)
                            if v and v not in bits:
                                bits.append(v)
                        results.append({
                            "display_name": ", ".join([b for b in bits if b]).strip(", "),
                            "lat": float(coords[1]),
                            "lng": float(coords[0]),
                            "type": props.get("osm_value") or props.get("type"),
                        })
                    except Exception:
                        continue
        except Exception as e:
            logger.warning("photon forward failed: %s", e)

        if not results:
            try:
                async with httpx.AsyncClient(
                    timeout=10.0, headers={"User-Agent": UA, "Accept": "application/json"},
                ) as hx:
                    await _throttle_rev()
                    r = await hx.get(
                        "https://nominatim.openstreetmap.org/search",
                        params={"q": q, "format": "json", "limit": 6, "addressdetails": 1},
                    )
                    if r.status_code != 200:
                        raise GeocoderFetchError(f"Nominatim HTTP {r.status_code}")
                    data = r.json()
                    successful_response = True
                    for d in (data if isinstance(data, list) else []):
                        try:
                            results.append({
                                "display_name": d.get("display_name", ""),
                                "lat": float(d["lat"]),
                                "lng": float(d["lon"]),
                                "type": d.get("type"),
                            })
                        except Exception:
                            continue
            except Exception as e:
                logger.warning("nominatim forward failed: %s", e)

        if not successful_response:
            if doc and doc.get("results"):
                logger.info("geocode forward failed; returning stale cache for %r", q)
                return doc["results"]
            raise GeocoderFetchError("Place search providers are unavailable")

        try:
            await self.col.update_one(
                {"_id": key},
                {"$set": {
                    "_id": key,
                    "q": q,
                    "results": results,
                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
                }},
                upsert=True,
            )
        except Exception:
            pass
        return results

    async def reverse(self, lat: float, lng: float) -> dict:
        key = hashlib.sha256(f"rev:{round(lat, 2)}:{round(lng, 2)}".encode()).hexdigest()
        doc = await self.col.find_one({"_id": key})
        if doc and doc.get("expires_at", "") > datetime.now(timezone.utc).isoformat():
            return doc.get("result", {})

        result = {"locality": None, "region": None, "country": None, "country_code": None}
        successful_response = False
        try:
            await _throttle_rev()
            async with httpx.AsyncClient(
                timeout=10.0, headers={"User-Agent": UA, "Accept": "application/json"},
            ) as hx:
                r = await hx.get(
                    "https://nominatim.openstreetmap.org/reverse",
                    params={"lat": lat, "lon": lng, "format": "json", "zoom": 10, "addressdetails": 1},
                )
                if r.status_code != 200:
                    raise GeocoderFetchError(f"Nominatim HTTP {r.status_code}")
                data = r.json()
                successful_response = True
                addr = data.get("address") or {}
                result = {
                    "locality": addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county"),
                    "region": addr.get("state") or addr.get("region"),
                    "country": addr.get("country"),
                    "country_code": (addr.get("country_code") or "").lower() or None,
                }
        except Exception as e:
            logger.warning("nominatim reverse failed: %s", e)
        if not successful_response:
            if doc and doc.get("result"):
                logger.info("reverse geocode failed; returning stale cache for %s,%s", lat, lng)
                return doc["result"]
            return result
        try:
            await self.col.update_one(
                {"_id": key},
                {"$set": {
                    "_id": key,
                    "lat": lat, "lng": lng,
                    "result": result,
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                }},
                upsert=True,
            )
        except Exception:
            pass
        return result
