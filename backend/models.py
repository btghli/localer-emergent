"""Shared Pydantic models for Localer backend.

NearbyItem is intentionally permissive: fields that cannot be verified from a
real source should remain None rather than be fabricated.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from urllib.parse import urlsplit


Category = Literal["landmark", "event", "news", "food", "nature"]
Precision = Literal["exact", "venue", "neighborhood", "city", "region"]
SourceType = Literal[
    "official", "venue", "ticketing", "aggregator", "wiki", "osm", "news",
]


class NearbyItem(BaseModel):
    # Core
    id: str = Field(min_length=1, max_length=200)
    externalId: str = Field(min_length=1, max_length=4096)  # provider-namespaced
    providerItemId: Optional[str] = Field(default=None, max_length=4096)
    provider: str = Field(min_length=1, max_length=80)
    sourceName: str = Field(min_length=1, max_length=300)
    sourceUrl: Optional[str] = Field(default=None, max_length=4096)
    sourceType: Optional[SourceType] = None
    canonicalUrl: Optional[str] = Field(default=None, max_length=4096)

    # Content
    category: Category
    title: str = Field(min_length=1, max_length=500)
    titleZh: Optional[str] = Field(default=None, max_length=500)
    summary: Optional[str] = Field(default=None, max_length=5000)
    summaryZh: Optional[str] = Field(default=None, max_length=5000)

    # Geography (all optional — news often has no exact coordinates)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    locationPrecision: Precision = "city"
    venueName: Optional[str] = Field(default=None, max_length=500)
    address: Optional[str] = Field(default=None, max_length=1000)
    locality: Optional[str] = Field(default=None, max_length=300)
    country: Optional[str] = Field(default=None, max_length=200)
    timezone: Optional[str] = Field(default=None, max_length=100)
    distanceMeters: Optional[float] = Field(default=None, ge=0)

    # Media
    imageUrl: Optional[str] = Field(default=None, max_length=4096)
    imageIsFallback: bool = False
    imageAttribution: Optional[str] = Field(default=None, max_length=500)

    # Time
    startsAt: Optional[str] = Field(default=None, max_length=100)
    endsAt: Optional[str] = Field(default=None, max_length=100)
    publishedAt: Optional[str] = Field(default=None, max_length=100)
    eventStatus: Optional[str] = Field(default=None, max_length=40)

    # Trust & lifecycle
    confidenceScore: Optional[float] = Field(default=None, ge=0, le=1)
    isDemo: bool = False
    stale: bool = False
    fetchedAt: str = Field(min_length=1, max_length=100)
    lastVerifiedAt: Optional[str] = Field(default=None, max_length=100)
    expiresAt: Optional[str] = Field(default=None, max_length=100)

    @field_validator("sourceUrl", "canonicalUrl", "imageUrl")
    @classmethod
    def require_web_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("URL must use http or https")
        return value
