"""Shared Pydantic models for Localer backend.

NearbyItem is intentionally permissive: fields that cannot be verified from a
real source should remain None rather than be fabricated.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal


Category = Literal["landmark", "event", "news", "food", "nature"]
Precision = Literal["exact", "venue", "neighborhood", "city", "region"]
SourceType = Literal[
    "official", "venue", "ticketing", "aggregator", "wiki", "osm", "news",
]


class NearbyItem(BaseModel):
    # Core
    id: str
    externalId: str                               # provider-namespaced, e.g. "ticketmaster:evt123"
    providerItemId: Optional[str] = None          # stable provider ID
    provider: str                                 # "ticketmaster" | "gdelt" | "wikipedia" | "osm"
    sourceName: str                               # publisher / venue / wiki
    sourceUrl: Optional[str] = None               # original item URL — NEVER a search URL
    sourceType: Optional[SourceType] = None
    canonicalUrl: Optional[str] = None

    # Content
    category: Category
    title: str
    titleZh: Optional[str] = None
    summary: Optional[str] = None
    summaryZh: Optional[str] = None

    # Geography (all optional — news often has no exact coordinates)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    locationPrecision: Precision = "city"
    venueName: Optional[str] = None
    address: Optional[str] = None
    locality: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    distanceMeters: Optional[float] = None

    # Media
    imageUrl: Optional[str] = None
    imageIsFallback: bool = False
    imageAttribution: Optional[str] = None

    # Time
    startsAt: Optional[str] = None                # ISO 8601
    endsAt: Optional[str] = None
    publishedAt: Optional[str] = None
    eventStatus: Optional[str] = None             # "scheduled" | "cancelled" | "postponed"

    # Trust & lifecycle
    confidenceScore: Optional[float] = None       # 0..1 (local-relevance / completeness)
    isDemo: bool = False
    stale: bool = False
    fetchedAt: str                                # ISO
    lastVerifiedAt: Optional[str] = None
    expiresAt: Optional[str] = None
