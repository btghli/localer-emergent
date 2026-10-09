"""Localer backend end-to-end tests."""
import os
import time
import uuid
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load frontend .env to get the public base URL
load_dotenv(Path("/app/frontend/.env"))
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

REQUIRED_FIELDS = [
    "id", "externalId", "category", "title", "summary",
    "latitude", "longitude", "sourceName", "provider", "fetchedAt",
    "distanceMeters",
]


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def user_ctx(session):
    """Register a fresh user and return (token, email, password)."""
    nonce = uuid.uuid4().hex[:10]
    email = f"tester+localer+{nonce}@example.com"
    password = "pass1234"
    r = session.post(f"{BASE_URL}/api/auth/register",
                     json={"email": email, "password": password, "name": "Tester"})
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and "user" in data
    assert data["user"]["email"] == email
    return {"token": data["token"], "email": email, "password": password, "user": data["user"]}


@pytest.fixture(scope="session")
def auth_headers(user_ctx):
    return {"Authorization": f"Bearer {user_ctx['token']}"}


# ---------- Health ----------
def test_root(session):
    r = session.get(f"{BASE_URL}/api/")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True


# ---------- Nearby ----------
def test_nearby_paris_all_categories(session):
    url = f"{BASE_URL}/api/nearby?lat=48.8566&lng=2.3522&radius=3000"
    r = session.get(url, timeout=40)
    if r.status_code == 200 and len(r.json()) < 3:
        time.sleep(2)
        r = session.get(url, timeout=40)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list) and len(items) > 0
    cats = {it["category"] for it in items}
    # Expect all 5 categories (landmark via wiki, food/nature via OSM, event/news demo)
    expected = {"landmark", "food", "nature", "event", "news"}
    missing = expected - cats
    assert not missing, f"Missing categories: {missing}; got {cats}"
    # Validate required fields on first item
    for field in REQUIRED_FIELDS:
        assert field in items[0], f"missing field {field}"


def test_nearby_category_filter(session):
    r = session.get(
        f"{BASE_URL}/api/nearby?lat=48.8566&lng=2.3522&radius=3000&categories=food,nature",
        timeout=40,
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) > 0
    cats = {it["category"] for it in items}
    assert cats.issubset({"food", "nature"}), f"unexpected categories: {cats}"


# ---------- Geocode ----------
def test_geocode_paris(session):
    r = session.get(f"{BASE_URL}/api/geocode?q=Paris", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) >= 1
    assert "lat" in data[0] and "lng" in data[0]
    assert isinstance(data[0]["lat"], float) and isinstance(data[0]["lng"], float)


# ---------- Auth ----------
def test_register_duplicate(session, user_ctx):
    r = session.post(f"{BASE_URL}/api/auth/register",
                     json={"email": user_ctx["email"], "password": user_ctx["password"]})
    assert r.status_code == 400


def test_login_success(session, user_ctx):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": user_ctx["email"], "password": user_ctx["password"]})
    assert r.status_code == 200
    data = r.json()
    assert "token" in data and data["user"]["email"] == user_ctx["email"]


def test_login_wrong_password(session, user_ctx):
    r = session.post(f"{BASE_URL}/api/auth/login",
                     json={"email": user_ctx["email"], "password": "wrong-password"})
    assert r.status_code == 401


def test_auth_me(session, auth_headers, user_ctx):
    r = session.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == user_ctx["email"]


def test_auth_settings_language_zh(session, auth_headers):
    r = session.patch(f"{BASE_URL}/api/auth/settings",
                      headers=auth_headers, json={"language": "zh"})
    assert r.status_code == 200
    assert r.json()["language"] == "zh"
    # Verify persistence
    r2 = session.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
    assert r2.json()["language"] == "zh"


# ---------- Favorites ----------
@pytest.fixture(scope="session")
def sample_item(session):
    r = session.get(
        f"{BASE_URL}/api/nearby?lat=48.8566&lng=2.3522&radius=3000&categories=event",
        timeout=40,
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) > 0
    return items[0]


def test_favorites_flow(session, auth_headers, sample_item):
    # Add
    r = session.post(f"{BASE_URL}/api/favorites", headers=auth_headers,
                     json={"item": sample_item})
    assert r.status_code == 200
    assert r.json().get("ok") is True
    assert r.json().get("duplicate") is False

    # List
    r = session.get(f"{BASE_URL}/api/favorites", headers=auth_headers)
    assert r.status_code == 200
    favs = r.json()
    assert any(f["externalId"] == sample_item["externalId"] for f in favs)

    # Duplicate add
    r = session.post(f"{BASE_URL}/api/favorites", headers=auth_headers,
                     json={"item": sample_item})
    assert r.status_code == 200
    assert r.json().get("duplicate") is True

    # Delete
    key = sample_item["externalId"]
    r = session.delete(f"{BASE_URL}/api/favorites/{key}", headers=auth_headers)
    assert r.status_code == 200

    r = session.get(f"{BASE_URL}/api/favorites", headers=auth_headers)
    assert not any(f["externalId"] == key for f in r.json())


# ---------- AI ----------
def test_ai_ask_english(session, sample_item):
    r = session.post(f"{BASE_URL}/api/ai/ask", timeout=60,
                     json={"item": sample_item, "question": "What is this?",
                           "language": "en"})
    assert r.status_code == 200, r.text
    answer = r.json().get("answer", "")
    assert isinstance(answer, str) and len(answer.strip()) > 0


def test_ai_ask_chinese(session, sample_item):
    r = session.post(f"{BASE_URL}/api/ai/ask", timeout=60,
                     json={"item": sample_item, "question": "这是什么?",
                           "language": "zh"})
    assert r.status_code == 200, r.text
    answer = r.json().get("answer", "")
    assert isinstance(answer, str) and len(answer.strip()) > 0


def test_ai_translate_and_cache(session):
    payload = {"text": "Hello world", "target": "zh"}
    t0 = time.time()
    r1 = session.post(f"{BASE_URL}/api/ai/translate", json=payload, timeout=60)
    t1 = time.time() - t0
    assert r1.status_code == 200, r1.text
    text1 = r1.json().get("text", "")
    assert text1 and isinstance(text1, str)

    # Second call should hit cache -> same text and faster
    t0 = time.time()
    r2 = session.post(f"{BASE_URL}/api/ai/translate", json=payload, timeout=60)
    t2 = time.time() - t0
    assert r2.status_code == 200
    text2 = r2.json().get("text", "")
    assert text2 == text1
    # Cache should be noticeably faster; allow some margin
    assert t2 <= max(t1, 1.0), f"cached call not fast: first={t1:.2f}s cached={t2:.2f}s"
