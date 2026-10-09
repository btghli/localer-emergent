"""Iteration 3: verify multi-provider refactor eliminates fabricated content.

Covers:
- /api/providers shape and enable state
- /api/nearby regression (no demo events / search URLs)
- Provider-correct schema on every item
- Empty event category when Ticketmaster disabled
- Wikipedia landmarks for Paris
- ProviderCache (second call fast + identical)
- Isolation when provider returns empty (ocean coords)
- Geocode regression
- Auth register/login/me regression
- Favorites CRUD regression
- AI /ask regression
"""
import os
import time
import uuid
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path("/app/frontend/.env"))
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

PARIS = {"lat": 48.8566, "lng": 2.3522, "radius": 3000}
FABRICATED_TITLES = {
    "Weekend Open-Air Market",
    "Sunset Jazz in the Park",
    "Community Film Night",
    "New Pedestrian Street Opens Downtown",
    "Local Library Launches Weekend Workshops",
}
VALID_PROVIDERS = {"wikipedia", "osm", "ticketmaster", "gdelt"}
BAD_HOST_SNIPS = ("google.com/search", "news.google.com/search")


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth(session):
    nonce = uuid.uuid4().hex[:8]
    email = f"tester+provider+{nonce}@example.com"
    pw = "localer-test-123"
    r = session.post(f"{API}/auth/register", json={"email": email, "password": pw, "name": "Tester"})
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and data["user"]["email"] == email
    return {"email": email, "password": pw, "token": data["token"], "user": data["user"]}


# ------- /api/providers -------
def test_providers_shape(session):
    r = session.get(f"{API}/providers")
    assert r.status_code == 200
    arr = r.json()
    assert isinstance(arr, list) and len(arr) == 4
    by_name = {p["name"]: p for p in arr}
    assert set(by_name.keys()) == VALID_PROVIDERS
    assert by_name["wikipedia"]["enabled"] is True
    assert by_name["osm"]["enabled"] is True
    assert by_name["gdelt"]["enabled"] is True
    assert by_name["ticketmaster"]["enabled"] is False


# ------- /api/nearby regression on fabricated content -------
def test_nearby_no_fabricated_content(session):
    r = session.get(f"{API}/nearby", params=PARIS)
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert len(items) > 0, "expected at least some wikipedia/osm items for Paris"
    for it in items:
        assert it["title"] not in FABRICATED_TITLES, f"fabricated title detected: {it['title']}"
        src = it.get("sourceUrl") or ""
        assert not any(b in src for b in BAD_HOST_SNIPS), f"search-URL sourceUrl: {src}"
        assert it.get("isDemo") is False
        # schema
        assert it["provider"] in VALID_PROVIDERS
        assert it["externalId"].startswith(it["provider"] + ":"), f"bad externalId: {it['externalId']}"
        assert it["sourceName"]
        assert it["sourceUrl"]
        assert it["fetchedAt"]
        if it["provider"] == "wikipedia":
            assert "wikipedia.org" in it["sourceUrl"]
        elif it["provider"] == "osm":
            assert "openstreetmap.org" in it["sourceUrl"] or it.get("sourceType") == "osm"


# ------- categories=event with no key => empty, NO demo fallback -------
def test_nearby_event_empty_when_no_ticketmaster_key(session):
    r = session.get(f"{API}/nearby", params={**PARIS, "categories": "event"})
    assert r.status_code == 200
    items = r.json()
    assert items == [], f"expected [] but got {len(items)} items (potential demo fallback)"


# ------- Wikipedia landmarks for Paris -------
def test_nearby_landmarks_wikipedia(session):
    r = session.get(f"{API}/nearby", params={**PARIS, "categories": "landmark"})
    assert r.status_code == 200
    items = r.json()
    wiki_items = [i for i in items if i["provider"] == "wikipedia"]
    assert len(wiki_items) >= 3, f"expected >=3 wikipedia landmarks, got {len(wiki_items)}"
    for it in wiki_items:
        assert it["sourceUrl"].startswith("https://en.wikipedia.org/"), it["sourceUrl"]
        assert it["category"] == "landmark"


# ------- Cache: second call is fast + identical -------
def test_nearby_cache_hits(session):
    params = {**PARIS, "categories": "landmark"}
    # warm cache
    r1 = session.get(f"{API}/nearby", params=params)
    assert r1.status_code == 200
    first = r1.json()
    assert len(first) > 0

    t0 = time.time()
    r2 = session.get(f"{API}/nearby", params=params)
    elapsed_ms = (time.time() - t0) * 1000
    assert r2.status_code == 200
    second = r2.json()
    assert elapsed_ms < 2000, f"cache call too slow: {elapsed_ms}ms"
    # externalIds should match (identical cached payload)
    ids1 = sorted(i["externalId"] for i in first)
    ids2 = sorted(i["externalId"] for i in second)
    assert ids1 == ids2


# ------- Isolation: ocean coords => 200 OK, no crash, likely [] -------
def test_nearby_ocean_isolation(session):
    r = session.get(f"{API}/nearby", params={"lat": 0.0, "lng": 0.0, "radius": 3000})
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    # Must still have no fabricated content
    for it in items:
        assert it["title"] not in FABRICATED_TITLES


# ------- Geocode regression -------
def test_geocode_paris(session):
    r = session.get(f"{API}/geocode", params={"q": "paris"})
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list) and len(results) >= 3


# ------- Auth regression -------
def test_auth_me(session, auth):
    r = session.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {auth['token']}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == auth["email"]


def test_auth_login(session, auth):
    r = session.post(f"{API}/auth/login", json={"email": auth["email"], "password": auth["password"]})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == auth["email"]


# ------- Favorites regression -------
def test_favorites_roundtrip(session, auth):
    headers = {"Authorization": f"Bearer {auth['token']}"}
    # Grab a real item
    r = session.get(f"{API}/nearby", params={**PARIS, "categories": "landmark"})
    assert r.status_code == 200
    items = r.json()
    assert items, "need a landmark item for favorites test"
    item = items[0]
    ext_id = item["externalId"]

    # Save
    r1 = session.post(f"{API}/favorites", json={"item": item}, headers=headers)
    assert r1.status_code == 200
    assert r1.json().get("duplicate") is False

    # List
    r2 = session.get(f"{API}/favorites", headers=headers)
    assert r2.status_code == 200
    favs = r2.json()
    assert any(f["externalId"] == ext_id for f in favs)

    # Duplicate
    r3 = session.post(f"{API}/favorites", json={"item": item}, headers=headers)
    assert r3.status_code == 200
    assert r3.json().get("duplicate") is True

    # Delete
    r4 = session.delete(f"{API}/favorites/{ext_id}", headers=headers)
    assert r4.status_code == 200

    # Verify gone
    r5 = session.get(f"{API}/favorites", headers=headers)
    favs2 = r5.json()
    assert not any(f["externalId"] == ext_id for f in favs2)


# ------- AI regression -------
def test_ai_ask_wikipedia_item(session):
    r = session.get(f"{API}/nearby", params={**PARIS, "categories": "landmark"})
    items = [i for i in r.json() if i["provider"] == "wikipedia"]
    assert items
    item = items[0]
    r2 = session.post(
        f"{API}/ai/ask",
        json={"item": item, "question": "What makes this place notable?", "language": "en"},
        timeout=60,
    )
    assert r2.status_code == 200, r2.text
    answer = r2.json().get("answer", "")
    assert isinstance(answer, str) and len(answer.strip()) > 10
