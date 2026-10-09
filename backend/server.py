from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import math
import uuid
import json
import asyncio
import hashlib
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import httpx

from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
JWT_ALGO = "HS256"
JWT_EXP_DAYS = 30

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

app = FastAPI(title="Localer API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("localer")

# -------------------- Models --------------------

Category = Literal["landmark", "event", "news", "food", "nature"]
Precision = Literal["exact", "venue", "neighborhood", "city", "region"]


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    language: str = "en"
    tts_voice: Optional[str] = None


class AuthOut(BaseModel):
    token: str
    user: User


class SettingsIn(BaseModel):
    language: Optional[str] = None
    tts_voice: Optional[str] = None


class NearbyItem(BaseModel):
    id: str
    externalId: str
    category: Category
    title: str
    titleZh: Optional[str] = None
    summary: str
    summaryZh: Optional[str] = None
    latitude: float
    longitude: float
    locationPrecision: Precision = "venue"
    address: Optional[str] = None
    locality: Optional[str] = None
    country: Optional[str] = None
    distanceMeters: Optional[float] = None
    imageUrl: Optional[str] = None
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    publishedAt: Optional[str] = None
    sourceName: str
    sourceUrl: Optional[str] = None
    provider: str
    fetchedAt: str


class AskIn(BaseModel):
    item: NearbyItem
    question: str
    language: str = "en"


class AskOut(BaseModel):
    answer: str
    sourceUrl: Optional[str] = None


class TranslateIn(BaseModel):
    text: str
    target: str  # "zh" or "en"


class TranslateOut(BaseModel):
    text: str


class FavoriteIn(BaseModel):
    item: NearbyItem


# -------------------- Auth helpers --------------------

def _hash_pw(pw: str) -> str:
    return pwd_ctx.hash(pw)


def _verify_pw(pw: str, hashed: str) -> bool:
    return pwd_ctx.verify(pw, hashed)


def _make_token(uid: str) -> str:
    payload = {
        "sub": uid,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> User:
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
        uid = payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    doc = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
    if not doc:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**doc)


async def optional_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> Optional[User]:
    if not creds:
        return None
    try:
        return await current_user(creds)
    except HTTPException:
        return None


# -------------------- Auth routes --------------------

@api.post("/auth/register", response_model=AuthOut)
async def register(body: RegisterIn):
    email = body.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    uid = str(uuid.uuid4())
    doc = {
        "id": uid,
        "email": email,
        "name": body.name,
        "language": "en",
        "tts_voice": None,
        "password_hash": _hash_pw(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    user = User(id=uid, email=email, name=body.name, language="en")
    return AuthOut(token=_make_token(uid), user=user)


@api.post("/auth/login", response_model=AuthOut)
async def login(body: LoginIn):
    email = body.email.lower()
    doc = await db.users.find_one({"email": email})
    if not doc or not _verify_pw(body.password, doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = User(
        id=doc["id"],
        email=doc["email"],
        name=doc.get("name"),
        language=doc.get("language", "en"),
        tts_voice=doc.get("tts_voice"),
    )
    return AuthOut(token=_make_token(doc["id"]), user=user)


@api.get("/auth/me", response_model=User)
async def me(user: User = Depends(current_user)):
    return user


@api.patch("/auth/settings", response_model=User)
async def update_settings(body: SettingsIn, user: User = Depends(current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"id": user.id}, {"$set": updates})
    doc = await db.users.find_one({"id": user.id}, {"_id": 0, "password_hash": 0})
    return User(**doc)


# -------------------- Favorites --------------------

@api.get("/favorites", response_model=List[NearbyItem])
async def list_favs(user: User = Depends(current_user)):
    docs = await db.favorites.find({"user_id": user.id}, {"_id": 0, "user_id": 0}).sort("saved_at", -1).to_list(500)
    return [NearbyItem(**d["item"]) for d in docs if "item" in d]


@api.post("/favorites")
async def add_fav(body: FavoriteIn, user: User = Depends(current_user)):
    key = body.item.externalId or body.item.id
    existing = await db.favorites.find_one({"user_id": user.id, "key": key})
    if existing:
        return {"ok": True, "duplicate": True}
    await db.favorites.insert_one({
        "user_id": user.id,
        "key": key,
        "item": body.item.model_dump(),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "duplicate": False}


@api.delete("/favorites/{key}")
async def rm_fav(key: str, user: User = Depends(current_user)):
    await db.favorites.delete_one({"user_id": user.id, "key": key})
    return {"ok": True}


# -------------------- Content providers --------------------

def _distance_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


async def _wiki_nearby(lat: float, lng: float, radius_m: int = 10000, limit: int = 15) -> List[NearbyItem]:
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "geosearch",
        "gscoord": f"{lat}|{lng}",
        "gsradius": min(max(radius_m, 10), 10000),
        "gslimit": limit,
        "format": "json",
    }
    ua = "Localer/1.0 (https://localer.app; contact@localer.app)"
    items: List[NearbyItem] = []
    try:
        async with httpx.AsyncClient(timeout=12.0, headers={"User-Agent": ua, "Accept": "application/json"}) as hx:
            r = await hx.get(url, params=params)
            data = r.json()
            pages = data.get("query", {}).get("geosearch", [])
            if not pages:
                return []

            async def fetch_detail(p):
                title = p["title"]
                try:
                    sr = await hx.get(
                        f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
                    )
                    return title, sr.json() if sr.status_code == 200 else {}
                except Exception:
                    return title, {}

            detail_results = await asyncio.gather(*[fetch_detail(p) for p in pages])
            details = {t: d for t, d in detail_results}
            for p in pages:
                title = p["title"]
                d = details.get(title, {})
                image = (d.get("thumbnail") or {}).get("source")
                summary = d.get("extract") or f"A notable place near this area called {title}."
                url_page = (d.get("content_urls") or {}).get("desktop", {}).get("page") or f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                items.append(NearbyItem(
                    id=str(uuid.uuid4()),
                    externalId=f"wiki-{p['pageid']}",
                    category="landmark",
                    title=title,
                    summary=summary[:600],
                    latitude=p["lat"],
                    longitude=p["lon"],
                    locationPrecision="exact",
                    imageUrl=image,
                    sourceName="Wikipedia",
                    sourceUrl=url_page,
                    provider="wikipedia",
                    fetchedAt=_now_iso(),
                ))
    except Exception as e:
        logger.warning(f"wiki_nearby failed: {e}")
    return items


async def _osm_nearby(lat: float, lng: float, radius_m: int = 3000) -> List[NearbyItem]:
    """Fetch food (restaurants, cafes) and nature (parks) from Nominatim."""
    ua = "Localer/1.0 (https://localer.app; contact@localer.app)"
    # Convert radius to a rough viewbox (1 deg lat ≈ 111 km)
    dlat = radius_m / 111000.0
    dlng = radius_m / (111000.0 * max(math.cos(math.radians(lat)), 0.1))
    viewbox = f"{lng - dlng},{lat + dlat},{lng + dlng},{lat - dlat}"

    base = "https://nominatim.openstreetmap.org/search"
    queries = [
        ("restaurant", "food", "venue"),
        ("cafe", "food", "venue"),
        ("park", "nature", "venue"),
    ]
    out: List[NearbyItem] = []
    try:
        async with httpx.AsyncClient(timeout=12.0, headers={"User-Agent": ua, "Accept": "application/json"}) as hx:
            async def one(q, cat, prec):
                try:
                    r = await hx.get(base, params={
                        "q": q, "format": "json", "limit": 8, "bounded": 1,
                        "viewbox": viewbox, "addressdetails": 1,
                    })
                    return cat, prec, q, r.json()
                except Exception:
                    return cat, prec, q, []

            results = await asyncio.gather(*[one(q, c, p) for q, c, p in queries])
            seen = set()
            for cat, prec, q, data in results:
                for d in data[:8]:
                    try:
                        osm_id = d.get("osm_id")
                        key = f"osm-{osm_id}-{d.get('osm_type', 'n')}"
                        if key in seen:
                            continue
                        seen.add(key)
                        name = d.get("display_name", "").split(",")[0].strip() or q.title()
                        addr = d.get("address", {}) if isinstance(d.get("address"), dict) else {}
                        locality = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("suburb")
                        summary_en = f"{q.title()} nearby — {name}. " + (addr.get("road", "") or "")
                        out.append(NearbyItem(
                            id=str(uuid.uuid4()),
                            externalId=key,
                            category=cat,
                            title=name,
                            summary=summary_en.strip(),
                            latitude=float(d["lat"]),
                            longitude=float(d["lon"]),
                            locationPrecision=prec,
                            address=addr.get("road"),
                            locality=locality,
                            country=addr.get("country"),
                            sourceName="OpenStreetMap",
                            sourceUrl=f"https://www.openstreetmap.org/{d.get('osm_type', 'node')}/{osm_id}",
                            provider="nominatim",
                            fetchedAt=_now_iso(),
                        ))
                    except Exception:
                        continue
    except Exception as e:
        logger.warning(f"osm_nearby failed: {e}")
    return out


def _demo_events_news(lat: float, lng: float) -> List[NearbyItem]:
    """Clearly-labeled demo seeded data for events and news.
    sourceUrl deep-links to a Google query so users can quickly find real local alternatives."""
    now = datetime.now(timezone.utc)
    seeds = [
        # events
        ("event", "Weekend Open-Air Market", "A curated open-air market with local artisans, live music, and street food. Great family-friendly atmosphere every weekend.", 0.004, -0.003, "demo-events", "Localer Demo"),
        ("event", "Sunset Jazz in the Park", "Local jazz quartet performs under the stars in the central park. Bring a blanket and enjoy acoustic sets.", -0.006, 0.004, "demo-events", "Localer Demo"),
        ("event", "Community Film Night", "A free outdoor screening of a classic film, hosted by the neighborhood association.", 0.008, 0.006, "demo-events", "Localer Demo"),
        # news
        ("news", "New Pedestrian Street Opens Downtown", "The city has unveiled a new pedestrian-only zone featuring expanded sidewalks, planters, and seating. Residents welcomed the change at a ribbon-cutting ceremony.", 0.002, 0.005, "demo-news", "Localer Demo"),
        ("news", "Local Library Launches Weekend Workshops", "Hands-on workshops in writing, robotics, and photography begin this month, open to all ages.", -0.004, -0.005, "demo-news", "Localer Demo"),
    ]
    items = []
    for idx, (cat, title, summ, dlat, dlng, prov, src) in enumerate(seeds):
        if cat == "event":
            # Try to deep-link into real event discovery platforms + a Google fallback.
            from urllib.parse import quote_plus
            q = quote_plus(f"{title} events near {lat:.3f},{lng:.3f}")
            source_url = f"https://www.google.com/search?q={q}"
            source_name = "Find events online"
        else:
            from urllib.parse import quote_plus
            q = quote_plus(f"{title} local news")
            source_url = f"https://news.google.com/search?q={q}"
            source_name = "Google News"
        it = NearbyItem(
            id=str(uuid.uuid4()),
            externalId=f"{prov}-{idx}",
            category=cat,
            title=title,
            summary=summ,
            latitude=lat + dlat,
            longitude=lng + dlng,
            locationPrecision="neighborhood" if cat == "news" else "venue",
            sourceName=source_name,
            sourceUrl=source_url,
            provider=prov,
            fetchedAt=_now_iso(),
            startsAt=(now + timedelta(days=2 + idx)).isoformat() if cat == "event" else None,
            publishedAt=(now - timedelta(hours=5 + idx * 3)).isoformat() if cat == "news" else None,
        )
        items.append(it)
    return items


@api.get("/nearby", response_model=List[NearbyItem])
async def nearby(lat: float, lng: float, radius: int = 3000, categories: Optional[str] = None):
    cats = set(categories.split(",")) if categories else {"landmark", "event", "news", "food", "nature"}

    tasks = []
    if "landmark" in cats:
        tasks.append(_wiki_nearby(lat, lng, radius_m=max(radius, 5000), limit=12))
    else:
        tasks.append(asyncio.sleep(0, result=[]))
    if cats & {"food", "nature"}:
        tasks.append(_osm_nearby(lat, lng, radius_m=min(radius, 3000)))
    else:
        tasks.append(asyncio.sleep(0, result=[]))

    wiki_items, osm_items = await asyncio.gather(*tasks)

    items: List[NearbyItem] = []
    items.extend(wiki_items)
    items.extend([i for i in osm_items if i.category in cats])

    if cats & {"event", "news"}:
        for it in _demo_events_news(lat, lng):
            if it.category in cats:
                items.append(it)

    # Dedup by externalId
    seen = set()
    deduped = []
    for it in items:
        if it.externalId in seen:
            continue
        seen.add(it.externalId)
        it.distanceMeters = _distance_m(lat, lng, it.latitude, it.longitude)
        deduped.append(it)

    # Sort by distance; news boosted by freshness slightly
    deduped.sort(key=lambda x: (x.distanceMeters or 1e9))
    return deduped[:60]


@api.get("/geocode")
async def geocode(q: str):
    """Worldwide place search — Photon primary with Nominatim fallback and short cache."""
    q = (q or "").strip()
    if not q:
        return []
    cache_key = hashlib.sha256(f"geo:{q.lower()}".encode()).hexdigest()
    cached = await db.geocode_cache.find_one({"key": cache_key}, {"_id": 0})
    if cached and cached.get("expires_at", "") > _now_iso():
        return cached["results"]

    ua = "Localer/1.0 (https://localer.app; contact@localer.app)"
    results = []
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": ua, "Accept": "application/json"}) as hx:
            r = await hx.get(
                "https://photon.komoot.io/api",
                params={"q": q, "limit": 7},
            )
            data = r.json()
            for f in data.get("features", []):
                try:
                    coords = f["geometry"]["coordinates"]
                    props = f.get("properties", {})
                    name = props.get("name") or ""
                    bits = [name]
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
        logger.warning(f"photon geocode failed: {e}")

    # Nominatim fallback if photon returned nothing
    if not results:
        try:
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": ua, "Accept": "application/json"}) as hx:
                r = await hx.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": q, "format": "json", "limit": 6, "addressdetails": 1},
                )
                data = r.json() if r.status_code == 200 else []
                results = [
                    {
                        "display_name": d.get("display_name", ""),
                        "lat": float(d["lat"]),
                        "lng": float(d["lon"]),
                        "type": d.get("type"),
                    }
                    for d in (data if isinstance(data, list) else [])
                ]
        except Exception as e:
            logger.warning(f"nominatim geocode fallback failed: {e}")

    # Cache for 24h
    try:
        expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        await db.geocode_cache.update_one(
            {"key": cache_key},
            {"$set": {"key": cache_key, "q": q, "results": results, "expires_at": expires}},
            upsert=True,
        )
    except Exception:
        pass
    return results


# -------------------- AI (Gemini via Emergent) --------------------

def _item_context(item: NearbyItem) -> str:
    bits = [
        f"Title: {item.title}",
        f"Category: {item.category}",
        f"Coordinates: {item.latitude:.5f}, {item.longitude:.5f}",
        f"Location precision: {item.locationPrecision}",
    ]
    if item.address:
        bits.append(f"Address: {item.address}")
    if item.locality:
        bits.append(f"Locality: {item.locality}")
    if item.summary:
        bits.append(f"Known description: {item.summary}")
    if item.sourceName:
        bits.append(f"Source: {item.sourceName} ({item.sourceUrl or 'n/a'})")
    if item.startsAt:
        bits.append(f"Starts at: {item.startsAt}")
    if item.publishedAt:
        bits.append(f"Published at: {item.publishedAt}")
    return "\n".join(bits)


@api.post("/ai/ask", response_model=AskOut)
async def ai_ask(body: AskIn):
    lang_name = "Simplified Chinese" if body.language.startswith("zh") else "English"
    system = (
        f"You are Localer, a concise, grounded local-discovery assistant. "
        f"Answer in {lang_name}. Base your answer strictly on the provided item context and widely-known facts. "
        f"If the context is insufficient, say so briefly and point the user to the source. "
        f"Never fabricate opening hours, prices, event availability, breaking-news facts, or precise historical claims. "
        f"Keep the answer under 160 words."
    )
    user_msg = (
        f"ITEM CONTEXT:\n{_item_context(body.item)}\n\n"
        f"QUESTION: {body.question}"
    )
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"ask-{body.item.externalId}-{uuid.uuid4().hex[:8]}",
            system_message=system,
        ).with_model("gemini", "gemini-3-flash-preview")
        resp = await chat.send_message(UserMessage(text=user_msg))
        answer = str(resp).strip()
    except Exception as e:
        logger.exception("ai_ask failed")
        raise HTTPException(status_code=502, detail=f"AI unavailable: {e}")
    return AskOut(answer=answer, sourceUrl=body.item.sourceUrl)


@api.post("/ai/translate", response_model=TranslateOut)
async def ai_translate(body: TranslateIn):
    target = "zh" if body.target.lower().startswith("zh") else "en"
    if not body.text.strip():
        return TranslateOut(text="")
    cache_key = hashlib.sha256(f"{target}:{body.text}".encode()).hexdigest()
    cached = await db.translations.find_one({"key": cache_key}, {"_id": 0})
    if cached:
        return TranslateOut(text=cached["text"])

    target_lang = "Simplified Chinese" if target == "zh" else "English"
    system = (
        f"You are a professional translator. Translate the user's text to {target_lang}. "
        "Preserve proper nouns, place names, and factual metadata. Return ONLY the translation, no quotes, no notes."
    )
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"tr-{cache_key[:12]}",
            system_message=system,
        ).with_model("gemini", "gemini-3-flash-preview")
        resp = await chat.send_message(UserMessage(text=body.text))
        translated = str(resp).strip()
    except Exception as e:
        logger.exception("translate failed")
        raise HTTPException(status_code=502, detail=f"Translation unavailable: {e}")

    await db.translations.insert_one({
        "key": cache_key,
        "target": target,
        "source_text": body.text,
        "text": translated,
        "created_at": _now_iso(),
    })
    return TranslateOut(text=translated)


# -------------------- Health --------------------

@api.get("/")
async def root():
    return {"ok": True, "service": "localer"}


# -------------------- App wiring --------------------

app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown():
    client.close()
