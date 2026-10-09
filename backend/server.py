from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import hashlib
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext

from emergentintegrations.llm.chat import LlmChat, UserMessage

from models import NearbyItem
from providers.wikipedia import WikipediaProvider
from providers.osm import OsmPoiProvider
from providers.ticketmaster import TicketmasterProvider
from providers.gdelt import GdeltNewsProvider
from providers.geocoder import Geocoder
from services.nearby import NearbyService

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("localer")

# Provider wiring. New providers can be appended here with no changes
# elsewhere.
_providers = [
    WikipediaProvider(),
    OsmPoiProvider(),
    TicketmasterProvider(),
    GdeltNewsProvider(),
]
nearby_service = NearbyService(db, _providers)
geocoder = Geocoder(db)


# -------------------- Auth models --------------------

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


class AskIn(BaseModel):
    item: NearbyItem
    question: str
    language: str = "en"


class AskOut(BaseModel):
    answer: str
    sourceUrl: Optional[str] = None


class TranslateIn(BaseModel):
    text: str
    target: str


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
    return jwt.encode(
        {"sub": uid,
         "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DAYS),
         "iat": datetime.now(timezone.utc)},
        JWT_SECRET, algorithm=JWT_ALGO,
    )


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


# -------------------- Auth routes --------------------

@api.post("/auth/register", response_model=AuthOut)
async def register(body: RegisterIn):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    uid = str(uuid.uuid4())
    await db.users.insert_one({
        "id": uid, "email": email, "name": body.name,
        "language": "en", "tts_voice": None,
        "password_hash": _hash_pw(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    user = User(id=uid, email=email, name=body.name, language="en")
    return AuthOut(token=_make_token(uid), user=user)


@api.post("/auth/login", response_model=AuthOut)
async def login(body: LoginIn):
    email = body.email.lower()
    doc = await db.users.find_one({"email": email})
    if not doc or not _verify_pw(body.password, doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = User(
        id=doc["id"], email=doc["email"], name=doc.get("name"),
        language=doc.get("language", "en"), tts_voice=doc.get("tts_voice"),
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
    if await db.favorites.find_one({"user_id": user.id, "key": key}):
        return {"ok": True, "duplicate": True}
    await db.favorites.insert_one({
        "user_id": user.id, "key": key,
        "item": body.item.model_dump(),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "duplicate": False}


@api.delete("/favorites/{key}")
async def rm_fav(key: str, user: User = Depends(current_user)):
    await db.favorites.delete_one({"user_id": user.id, "key": key})
    return {"ok": True}


# -------------------- Content --------------------

@api.get("/nearby", response_model=List[NearbyItem])
async def nearby(lat: float, lng: float, radius: int = 3000, categories: Optional[str] = None):
    cats = [c.strip() for c in categories.split(",") if c.strip()] if categories else None
    return await nearby_service.nearby(lat, lng, radius, cats)


@api.get("/geocode")
async def geocode(q: str):
    return await geocoder.forward(q)


# -------------------- AI --------------------

def _item_context(item: NearbyItem) -> str:
    bits = [
        f"Title: {item.title}",
        f"Category: {item.category}",
        f"Provider: {item.provider}",
        f"Source: {item.sourceName} ({item.sourceUrl or 'n/a'})",
    ]
    if item.latitude is not None and item.longitude is not None:
        bits.append(f"Coordinates: {item.latitude:.5f}, {item.longitude:.5f}")
    bits.append(f"Location precision: {item.locationPrecision}")
    if item.venueName:
        bits.append(f"Venue: {item.venueName}")
    if item.address:
        bits.append(f"Address: {item.address}")
    if item.locality:
        bits.append(f"Locality: {item.locality}")
    if item.summary:
        bits.append(f"Known description: {item.summary}")
    if item.startsAt:
        bits.append(f"Starts at: {item.startsAt}")
    if item.endsAt:
        bits.append(f"Ends at: {item.endsAt}")
    if item.publishedAt:
        bits.append(f"Published at: {item.publishedAt}")
    if item.eventStatus:
        bits.append(f"Event status: {item.eventStatus}")
    if item.isDemo:
        bits.append("NOTE: This is explicitly-labelled demo content. Treat its details as placeholders only.")
    return "\n".join(bits)


@api.post("/ai/ask", response_model=AskOut)
async def ai_ask(body: AskIn):
    lang_name = "Simplified Chinese" if body.language.startswith("zh") else "English"
    system = (
        f"You are Localer, a concise, grounded local-discovery assistant. "
        f"Answer in {lang_name}. Base your answer STRICTLY on the provided item context. "
        f"Never invent opening hours, prices, availability, cancellation status, addresses, "
        f"historical facts, or breaking-news details. If the context is insufficient, say so "
        f"briefly and tell the user to open the source URL. If the item is marked demo, say "
        f"it is placeholder content and avoid making factual claims about it. "
        f"Keep the answer under 160 words."
    )
    user_msg = f"ITEM CONTEXT:\n{_item_context(body.item)}\n\nQUESTION: {body.question}"
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
        "Preserve proper nouns, place names, and factual metadata. "
        "Return ONLY the translation, no quotes, no notes."
    )
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY, session_id=f"tr-{cache_key[:12]}",
            system_message=system,
        ).with_model("gemini", "gemini-3-flash-preview")
        resp = await chat.send_message(UserMessage(text=body.text))
        translated = str(resp).strip()
    except Exception as e:
        logger.exception("translate failed")
        raise HTTPException(status_code=502, detail=f"Translation unavailable: {e}")
    await db.translations.insert_one({
        "key": cache_key, "target": target, "source_text": body.text,
        "text": translated, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return TranslateOut(text=translated)


# -------------------- Health --------------------

@api.get("/")
async def root():
    return {"ok": True, "service": "localer", "providers": [p.name for p in _providers]}


@api.get("/providers")
async def provider_status():
    return [
        {
            "name": p.name,
            "categories": list(p.categories),
            "enabled": p.is_enabled(),
            "requires_env": p.enabled_env_var,
        }
        for p in _providers
    ]


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
