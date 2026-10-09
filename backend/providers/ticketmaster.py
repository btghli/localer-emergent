"""Ticketmaster Discovery API — real event provider.

Spec: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/

If TICKETMASTER_API_KEY is empty/missing, fetch() returns [] and logs a notice.
Nothing is fabricated.
"""
from __future__ import annotations
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import List

import httpx

from models import NearbyItem
from providers import FetchContext, Provider, now_iso, new_id

logger = logging.getLogger("localer.providers.ticketmaster")

UA = "Localer/1.0 (https://localer.app; contact@localer.app)"
BASE = "https://app.ticketmaster.com/discovery/v2/events.json"


class TicketmasterProvider(Provider):
    name = "ticketmaster"
    categories = ("event",)
    enabled_env_var = "TICKETMASTER_API_KEY"

    def __init__(self, window_days: int = 30, size: int = 25):
        self.window_days = window_days
        self.size = size

    async def fetch(self, ctx: FetchContext) -> List[NearbyItem]:
        api_key = os.environ.get("TICKETMASTER_API_KEY", "").strip()
        if not api_key:
            logger.info("ticketmaster: TICKETMASTER_API_KEY not set — returning empty event list")
            return []

        start = datetime.now(timezone.utc)
        end = start + timedelta(days=self.window_days)

        params = {
            "apikey": api_key,
            "latlong": f"{ctx.lat},{ctx.lng}",
            "radius": max(1, min(500, round(ctx.radius_m / 1000))),
            "unit": "km",
            "startDateTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endDateTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "size": self.size,
            "sort": "date,asc",
        }

        items: List[NearbyItem] = []
        try:
            async with httpx.AsyncClient(timeout=12.0, headers={"User-Agent": UA}) as hx:
                r = await hx.get(BASE, params=params)
                if r.status_code == 429:
                    logger.warning("ticketmaster 429 rate-limit")
                    return []
                if r.status_code != 200:
                    logger.warning("ticketmaster HTTP %s", r.status_code)
                    return []
                data = r.json()
                events = ((data or {}).get("_embedded") or {}).get("events") or []
                for ev in events:
                    try:
                        itm = self._parse(ev)
                        if itm:
                            items.append(itm)
                    except Exception as pe:
                        logger.warning("ticketmaster parse error: %s", pe)
                        continue
        except Exception as e:
            logger.warning("ticketmaster fetch failed: %s", e)
        return items

    def _parse(self, ev: dict) -> NearbyItem | None:
        pid = ev.get("id")
        name = ev.get("name")
        url = ev.get("url")
        if not pid or not name or not url:
            return None
        if (ev.get("test") is True) or (ev.get("dates", {}).get("status", {}).get("code") == "cancelled" and ev.get("dates", {}).get("status", {}).get("code") == "test"):
            return None
        status_code = (ev.get("dates", {}).get("status", {}) or {}).get("code")
        if status_code in {"cancelled"}:
            # Still include but mark as cancelled — frontend decides to show or hide.
            event_status = "cancelled"
        elif status_code in {"postponed", "rescheduled"}:
            event_status = "postponed"
        else:
            event_status = "scheduled"

        dates = ev.get("dates", {}) or {}
        start_obj = (dates.get("start") or {})
        starts_at = start_obj.get("dateTime")
        if not starts_at:
            local_date = start_obj.get("localDate")
            local_time = start_obj.get("localTime")
            if local_date:
                starts_at = f"{local_date}T{local_time or '00:00:00'}"
        end_obj = (dates.get("end") or {})
        ends_at = end_obj.get("dateTime")
        tz = (dates.get("timezone") or None)

        if not starts_at:
            return None
        # Discard clearly-past events (end if available, else start)
        try:
            compare = datetime.fromisoformat((ends_at or starts_at).replace("Z", "+00:00"))
            if compare.tzinfo is None:
                compare = compare.replace(tzinfo=timezone.utc)
            if compare < datetime.now(timezone.utc) - timedelta(hours=6):
                return None
        except Exception:
            pass

        venues = ((ev.get("_embedded") or {}).get("venues") or [])
        venue = venues[0] if venues else {}
        lat_s = ((venue.get("location") or {}).get("latitude"))
        lng_s = ((venue.get("location") or {}).get("longitude"))
        latitude = float(lat_s) if lat_s not in (None, "") else None
        longitude = float(lng_s) if lng_s not in (None, "") else None
        venue_name = venue.get("name")
        address = ((venue.get("address") or {}).get("line1"))
        city = (venue.get("city") or {}).get("name")
        state = (venue.get("state") or {}).get("name")
        country = (venue.get("country") or {}).get("name")
        location_precision = "venue" if (latitude and longitude) else ("city" if city else "region")

        images = ev.get("images") or []
        # Pick largest 16:9 if available
        img = None
        if images:
            try:
                img = sorted(images, key=lambda i: (i.get("ratio") == "16_9", i.get("width", 0)), reverse=True)[0].get("url")
            except Exception:
                img = (images[0] or {}).get("url")

        info = ev.get("info") or ev.get("pleaseNote") or ""

        return NearbyItem(
            id=new_id(),
            externalId=f"ticketmaster:{pid}",
            providerItemId=str(pid),
            provider=self.name,
            sourceName="Ticketmaster",
            sourceUrl=url,
            canonicalUrl=url,
            sourceType="ticketing",
            category="event",
            title=name,
            summary=info[:500] if info else None,
            latitude=latitude,
            longitude=longitude,
            locationPrecision=location_precision,
            venueName=venue_name,
            address=address,
            locality=city,
            country=country,
            timezone=tz,
            imageUrl=img,
            imageIsFallback=False,
            imageAttribution=None,
            startsAt=starts_at,
            endsAt=ends_at,
            eventStatus=event_status,
            confidenceScore=0.85 if (latitude and longitude) else 0.6,
            fetchedAt=now_iso(),
        )
