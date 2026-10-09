"""Unit coverage for geocoder outage and stale-cache behavior."""
import asyncio
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import providers.geocoder as geocoder_module
from providers.geocoder import Geocoder, GeocoderFetchError


class FakeCollection:
    def __init__(self, document=None):
        self.document = document
        self.writes = []

    async def find_one(self, _query):
        return self.document

    async def update_one(self, query, update, upsert=False):
        self.writes.append((query, update, upsert))


class FailingClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *_args, **_kwargs):
        raise httpx.ConnectError("offline")


def make_geocoder(document=None):
    instance = Geocoder.__new__(Geocoder)
    instance.col = FakeCollection(document)
    return instance


def test_forward_outage_is_not_cached_as_empty(monkeypatch):
    monkeypatch.setattr(geocoder_module.httpx, "AsyncClient", FailingClient)

    async def no_throttle():
        return None

    monkeypatch.setattr(geocoder_module, "_throttle_rev", no_throttle)
    geocoder = make_geocoder()

    with pytest.raises(GeocoderFetchError):
        asyncio.run(geocoder.forward("Chicago"))

    assert geocoder.col.writes == []


def test_forward_outage_uses_existing_stale_results(monkeypatch):
    monkeypatch.setattr(geocoder_module.httpx, "AsyncClient", FailingClient)

    async def no_throttle():
        return None

    monkeypatch.setattr(geocoder_module, "_throttle_rev", no_throttle)
    stale = [{"display_name": "Chicago, Illinois", "lat": 41.88, "lng": -87.63}]
    geocoder = make_geocoder({"expires_at": "2020-01-01T00:00:00+00:00", "results": stale})

    result = asyncio.run(geocoder.forward("Chicago"))

    assert result == stale
    assert geocoder.col.writes == []
