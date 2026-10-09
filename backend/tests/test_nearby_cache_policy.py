"""Unit coverage for the distinction between empty data and provider failure."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import NearbyItem
from providers import FetchContext, ProviderFetchError
from services.nearby import NearbyService


class FakeProvider:
    name = "fake"
    categories = ("landmark",)
    enabled_env_var = None

    def __init__(self, result=None, error=None):
        self.result = result if result is not None else []
        self.error = error

    def is_enabled(self):
        return True

    async def fetch(self, _ctx):
        if self.error:
            raise self.error
        return self.result


class FakeCache:
    def __init__(self, cached=None):
        self.cached = cached
        self.writes = []

    async def get(self, _key, allow_stale=True):
        return self.cached

    async def set(self, key, items, ttl):
        self.writes.append((key, items, ttl))


def context():
    return FetchContext(lat=41.88, lng=-87.63, radius_m=3000)


def stale_item():
    return NearbyItem(
        id="cached",
        externalId="fake:cached",
        provider="fake",
        sourceName="Cached source",
        sourceUrl="https://example.com/cached",
        category="landmark",
        title="Cached landmark",
        latitude=41.88,
        longitude=-87.63,
        locationPrecision="exact",
        fetchedAt="2026-01-01T00:00:00+00:00",
    )


def service(provider, cache):
    instance = NearbyService.__new__(NearbyService)
    instance.cache = cache
    return instance


def test_successful_empty_response_is_cached_and_does_not_revive_stale_items():
    cached = {"stale": True, "items": [stale_item().model_dump()]}
    cache = FakeCache(cached)
    provider = FakeProvider(result=[])

    result = asyncio.run(service(provider, cache)._fetch_provider(provider, context(), ["landmark"]))

    assert result == []
    assert len(cache.writes) == 1
    assert cache.writes[0][1] == []


def test_provider_failure_returns_stale_items_with_explicit_marker():
    cached = {"stale": True, "items": [stale_item().model_dump()]}
    cache = FakeCache(cached)
    provider = FakeProvider(error=ProviderFetchError("upstream unavailable"))

    result = asyncio.run(service(provider, cache)._fetch_provider(provider, context(), ["landmark"]))

    assert len(result) == 1
    assert result[0].externalId == "fake:cached"
    assert result[0].stale is True
    assert cache.writes == []
