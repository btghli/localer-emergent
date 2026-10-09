# Localer — PRD & Build Memory

## Problem Statement (verbatim from user)
Localer is a location-aware AI companion that helps people discover what is interesting and useful around them. It turns the user's current location, or any area they explore on the map, into an interactive local discovery experience. Users can browse nearby landmarks, local news, events, food, and scenic or interesting places directly on a map. They can open an item, read about it in English or Chinese, ask AI follow-up questions, listen to the content using text-to-speech, and save favorites after signing in.

## User Choices Confirmed
- AI: Gemini 3 Flash via Emergent LLM key
- Auth: Email/password (JWT) only
- TTS: Browser Web Speech API
- Content providers: Wikipedia (landmarks) + OSM/Nominatim (food, nature) + demo seeded data (events, news)
- Map tiles: Leaflet + OpenStreetMap standard tiles (no key)

## Core Requirements (static)
1. Full-screen interactive map as the home page (no API key required).
2. Nearby categories with distinct icons + colors: Landmarks (purple), Events (orange), News (blue), Food (red), Nature (green).
3. Category filter bar; "Search this area" + recenter-to-me button.
4. Mobile bottom sheet + desktop left discovery panel; synchronized selection.
5. Item detail with image, distance, source link, EN/中文 toggle, Listen (TTS play/pause/resume/stop), Ask Localer (AI Q&A), save/favorite.
6. Global place search (Nominatim geocoder).
7. JWT auth; favorites persist per user with dedup.
8. Full UI localization (EN + 简体中文); default from browser language.
9. AI answers grounded in item context; translate on-demand with DB caching.

## What's Been Implemented (2026-02)
- Backend `/api` (FastAPI + Motor + emergentintegrations):
  - Auth: `/auth/register`, `/auth/login`, `/auth/me`, `/auth/settings`
  - Content: `/nearby`, `/geocode`
  - AI: `/ai/ask`, `/ai/translate` (DB-cached)
  - Favorites: `/favorites` list/add, `/favorites/{key}` delete (dedup by externalId)
- Frontend (React 19 + Leaflet + shadcn):
  - `Explore` map page (full-screen Leaflet, custom category divIcon markers, user-location pulsing dot, "Search this area" + recenter, geocoder search, discovery panel with skeletons/empty/error states, mobile draggable-style bottom sheet)
  - `ItemDetail` panel (image, source link, approximate-location badge, EN/中文 toggle with on-demand translation, Listen TTS, Ask Localer chat with suggested questions and TTS for AI answers, save/favorite)
  - `Favorites`, `Account` (language + voice preference) pages, bottom nav + desktop header
  - `AuthDialog` (register/sign-in tabs)
  - Full i18n dictionary EN + ZH; browser-language default
- Backend tested end-to-end (13/13 passing).

## Integrations Status
- Gemini 3 Flash via Emergent LLM key — LIVE
- Wikipedia (landmarks) — LIVE
- OSM/Nominatim (food/nature + geocoding) — LIVE
- Events / News — DEMO seeded data (clearly labeled "Localer Demo"), easy to swap in real providers later
- TTS — browser Web Speech API (works offline)

## Setup Checklist
Already configured: `EMERGENT_LLM_KEY`, `JWT_SECRET`, Mongo via `MONGO_URL`. No Google Maps or Google Places key needed.

## Backlog / Next
- P1: Real events provider (Ticketmaster/Eventbrite) + real local-news provider (NewsAPI/Google News RSS)
- P1: Marker clustering (react-leaflet-cluster already installed) when zoomed out
- P2: Password reset flow
- P2: Dark map theme toggle
- P2: Share deep-link to a selected item
