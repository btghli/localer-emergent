"""Focused tests for /api/geocode (Photon primary + Nominatim fallback + Mongo cache)
and smoke regression on /api/ and /api/nearby.
"""
import os
import time
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("/app/frontend/.env"))
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _get_geocode(session, q, retries=1, timeout=20):
    url = f"{BASE_URL}/api/geocode"
    last = None
    for attempt in range(retries + 1):
        r = session.get(url, params={"q": q} if q is not None else {}, timeout=timeout)
        last = r
        if r.status_code == 200 and (q == "" or len(r.json()) > 0):
            return r
        time.sleep(1.5)
    return last


def _assert_item_shape(item):
    assert "display_name" in item and isinstance(item["display_name"], str) and item["display_name"]
    assert "lat" in item and "lng" in item
    assert isinstance(item["lat"], (int, float))
    assert isinstance(item["lng"], (int, float))


# ---------- Regression smoke ----------
def test_root_ok(session):
    r = session.get(f"{BASE_URL}/api/", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("service") == "localer"


def test_nearby_paris_smoke(session):
    url = f"{BASE_URL}/api/nearby?lat=48.8566&lng=2.3522&radius=3000"
    r = session.get(url, timeout=45)
    if r.status_code == 200 and len(r.json()) < 5:
        time.sleep(2)
        r = session.get(url, timeout=45)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    assert len(items) >= 5, f"expected total count >= 5, got {len(items)}"
    cats = {it["category"] for it in items}
    assert cats & {"landmark", "event", "news"}, f"expected one of landmark/event/news in {cats}"


# ---------- Geocode: queries ----------
@pytest.mark.parametrize("q,min_items", [
    ("paris", 3),
    ("shanghai", 3),
    ("tokyo tower", 1),
])
def test_geocode_queries(session, q, min_items):
    r = _get_geocode(session, q, retries=1, timeout=25)
    assert r.status_code == 200, f"q={q!r} -> {r.status_code} {r.text}"
    data = r.json()
    assert isinstance(data, list), f"q={q!r} -> not a list: {data}"
    assert len(data) >= min_items, f"q={q!r} returned {len(data)} items, expected >= {min_items}"
    for item in data[:min_items]:
        _assert_item_shape(item)


def test_geocode_empty_query(session):
    r = session.get(f"{BASE_URL}/api/geocode", params={"q": ""}, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    assert data == [], f"expected [] for empty q, got {data}"


# ---------- Geocode: caching ----------
def test_geocode_cache_consistency_and_speed(session):
    # Warm-up: ensure the first call succeeds (may be slow if cold)
    r1 = _get_geocode(session, "paris", retries=1, timeout=25)
    assert r1.status_code == 200
    first = r1.json()
    assert isinstance(first, list) and len(first) >= 3

    # Second call — should be served from Mongo cache: same results, fast
    t0 = time.time()
    r2 = session.get(f"{BASE_URL}/api/geocode", params={"q": "paris"}, timeout=15)
    elapsed = time.time() - t0
    assert r2.status_code == 200
    second = r2.json()
    assert second == first, "cached response differs from original"
    # Soft threshold — network RTT to the preview URL dominates. Give generous margin.
    assert elapsed < 3.0, f"cached call too slow: {elapsed:.2f}s"
    print(f"Cached /api/geocode?q=paris elapsed={elapsed:.3f}s items={len(second)}")
