# Localer

Localer is a location-aware AI companion that helps you discover real places,
events, and news on an interactive world map. It is built with FastAPI,
MongoDB, and React (Leaflet + OpenStreetMap tiles) and uses the Emergent LLM
key for Gemini-powered Q&A and translation.

## Content providers

Localer's nearby content comes from a provider-adapter layer in
`backend/providers/`. Every item displayed in production comes from a
traceable real source — the system never fabricates titles, descriptions,
dates, coordinates, sources, or URLs.

| Category   | Provider                        | Env var required      | Enabled by default |
|------------|---------------------------------|-----------------------|--------------------|
| Landmarks  | Wikipedia GeoSearch + Summary   | —                     | Yes                |
| Food       | OpenStreetMap / Nominatim       | — (public, throttled) | Yes                |
| Nature     | OpenStreetMap / Nominatim       | — (public, throttled) | Yes                |
| Events     | Ticketmaster Discovery API      | `TICKETMASTER_API_KEY`| **Off** until key  |
| News       | GDELT 2.1 DOC API               | — (public, throttled) | Yes                |

A missing API key disables that provider and is exposed through
`GET /api/providers`, allowing the UI to mark its category unavailable. One
failing provider never breaks the other categories.

## Required environment variables

See `backend/.env.example` for the complete list.

| Variable              | Purpose                                             |
|-----------------------|-----------------------------------------------------|
| `MONGO_URL`           | Mongo connection string                             |
| `DB_NAME`             | Mongo database                                      |
| `JWT_SECRET`          | HS256 signing key for user tokens                   |
| `EMERGENT_LLM_KEY`    | Emergent universal key — powers Ask Localer + translate |
| `TICKETMASTER_API_KEY`| Optional. Get a free key at developer.ticketmaster.com |
| `CORS_ORIGINS`        | Comma-separated allowed origins (default `*`)       |

API keys live server-side only. The frontend never sees any provider key.

## Cache & reliability

Each provider call is cached in Mongo (`provider_cache` collection) keyed on
`(provider, categories, geo-cell, radius bucket)`. TTLs:

- News: 25 min
- Events: 1 h
- Landmarks: 7 d
- Food / Nature: 24 h

If a live fetch fails but a stale cache entry exists, Localer serves the
cached data with `stale=true` so the UI can label it as such. Fabricated
content is **never** used as a fallback.

Throttling:

- Nominatim (geocode + POI) is serialized to 1 request/second globally.
- GDELT is serialized to 1 request / 5 seconds globally.

## Validation

- `event`: must have real `sourceUrl` (never a Google search URL), stable
  `providerItemId`, `startsAt`, not already ended, not cancelled, not a test
  event.
- `news`: must have a real article URL, publisher, `publishedAt`, and a
  computed `confidenceScore ≥ 0.3` after locality / country / recency
  scoring.
- Items whose `sourceUrl` points to `google.com/search` or
  `news.google.com/search` are rejected.

## Deduplication & ranking

Duplicates are merged in this order:

1. Same `externalId`
2. Same `canonicalUrl` / `sourceUrl`
3. Normalized `(category, title, venueName, startsAt-day)` signature — the
   higher-authority copy wins (`official > venue > ticketing > news > wiki
   > aggregator > osm`).

Ranking is a transparent weighted sum of:

- Distance (closer is better) · 40 pts
- `confidenceScore` · 20 pts
- Source authority · 10 pts
- Freshness / soon-ness (events: starts within 14 d, news: within 48 h) · 20 pts

Penalties: `stale=-5`, `postponed=-3`.

## Image policy

Localer only renders a photo when the provider supplies one. There is no
category-level stock-photo fallback — items without an image show a tinted
gradient and the category icon so users are never misled into believing a
generic photo depicts the item.

## Running locally

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Fill MONGO_URL, DB_NAME and JWT_SECRET; add EMERGENT_LLM_KEY for AI features.
# Optionally add TICKETMASTER_API_KEY

python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
npx -y yarn@1.22.22 --cwd frontend install --frozen-lockfile
```

Backend runs on `:8001`, frontend on `:3000`. All backend routes are prefixed
with `/api`. The frontend reads `REACT_APP_BACKEND_URL` from
`frontend/.env`.

Start the two development processes in separate terminals:

```bash
backend/.venv/bin/uvicorn server:app --app-dir backend --reload --port 8001
npx -y yarn@1.22.22 --cwd frontend start
```

## Production notes

- Nominatim's public API is **not** intended for high-volume POI discovery.
  Localer caches aggressively and throttles globally, but production
  deployments should either self-host Overpass/Nominatim or move to a
  licensed POI API.
- GDELT's DOC API is rate-limited to roughly 1 request / 5 seconds per
  client. The 25-minute cache keeps real-world traffic well within limits
  for any one city, but global load balancers may need their own throttle.
- The `GET /api/providers` endpoint returns the live enabled/disabled
  status of every provider — useful for ops dashboards.

## Attribution

- Map tiles: © OpenStreetMap contributors.
- Landmarks: Wikipedia (CC BY-SA).
- Food / Nature POI data: © OpenStreetMap contributors (ODbL).
- Events: Ticketmaster (subject to their TOU).
- News headlines: GDELT 2.1 and the respective publisher of each article.
