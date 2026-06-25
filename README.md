---
title: DealBreaker
emoji: 🏠
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

# DealBreaker

The 60-second background check on a Sydney property listing — flood, bushfire, commute, and too-cheap/scam flags, on a map — *before* you waste a Saturday inspecting it.

**🔗 [Code on GitHub](https://github.com/yash1120/dealbreaker) · [Live demo — HF Spaces](https://huggingface.co/spaces/yash1120/dealbreaker)**

The "anti-listing" tool: it surfaces the things Domain/REA are structurally motivated to hide.

## How it works

```
address -> geocode (OSM Nominatim) -> NSW Planning Portal Hazard ArcGIS REST -> verdict
```

All on **free, keyless** data — no API key needed for the hazard checks.

| Check | Source | Notes |
|-------|--------|-------|
| 🔥 Bushfire | NSW Planning Portal Bush Fire Prone Land (ArcGIS layer 229) | Solid, statewide |
| 🌊 Flood | NSW EPI Flood Planning (ArcGIS layer 230) | **Patchy** — only councils that mapped flood-planning in their LEP. "No flag" ≠ "won't flood". |
| 💰 Rent / scam | NSW DCJ Rent & Sales Report medians (`data/rent.db`) | "Is this rent fair?" + a too-cheap bait/scam tell |
| 🚆 Commute | Transport for NSW Trip Planner | Door-to-door transit time; needs a free `TFNSW_API_KEY` |
| 📍 Geocoding | OpenStreetMap Nominatim (cached) | MVP-grade; AU street precision is weak → roadmap: G-NAF |

## Setup & run

```bash
# 1. (once) build the rent database from NSW DCJ data
.venv\Scripts\python.exe data\ingest_rent.py

# 2. (optional) enable the commute check — copy .env.example to .env and paste
#    your free key from https://opendata.transport.nsw.gov.au/
copy .env.example .env

# 3. run
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir F:\projects\dealbreaker
# then open http://127.0.0.1:8000
```

## Deploy

Containerised — the image ships a prebuilt `data/rent.db` (1.3 MB, no LFS) and listens on `$PORT` (default 7860).

### Hugging Face Spaces (Docker)
1. Create a Space → **SDK: Docker** → Blank.
2. Keep this `README.md`'s YAML frontmatter (`sdk: docker`, `app_port: 7860`) — HF reads it to run the Space.
3. Space → **Settings → Variables and secrets** → add secret `TFNSW_API_KEY` (your TfNSW key).
4. Push the repo to the Space:
   ```bash
   git init && git add . && git commit -m "DealBreaker MVP"
   git remote add space https://huggingface.co/spaces/<user>/<space>
   git push space main          # or 'master'
   ```
   Commit `data/rent.db`; **never** commit `.env` (it's git/docker-ignored).

### Local Docker / Render / Railway / Fly
```bash
docker build -t dealbreaker .
docker run -p 7860:7860 -e TFNSW_API_KEY=your-key dealbreaker   # http://localhost:7860
```
On Render/Railway/Fly: New Web Service → Docker → set `TFNSW_API_KEY`; they inject `$PORT`.
Refresh rent data with `python data/ingest_rent.py`, then rebuild.

> **Public-demo heads-up:** geocoding uses OSM **Nominatim**, which rate-limits shared IPs (1 req/s) and may throttle a busy Space. The example buttons and in-memory cache keep light demos smooth; for heavy use, move to G-NAF (roadmap).

## Roadmap

- [x] Spatial spike — prove hazard checks work keyless
- [x] FastAPI `/api/check` + verdict
- [x] Address-check UI (green/amber/red card)
- [x] Interactive map (Leaflet) with live NSW bushfire/flood polygon overlays + verdict-colored pin
- [x] Too-cheap / scam flag (NSW DCJ median rents)
- [x] Commute check (TfNSW Trip Planner) — code done; set `TFNSW_API_KEY` to enable
- [x] Median-rent map layer — per-postcode medians by bedroom count (NSW DCJ + postcode centroids)
- [x] Dockerised + free-host deploy docs
- [ ] Sale-price map (NSW Valuer-General sales register) — the "price of houses" layer
- [ ] G-NAF property-level geocoding (Nominatim is weak on AU street precision)
- [ ] Saved per-address dossiers (Supabase free tier)
- [ ] Per-council flood layers for better flood coverage

## Disclaimer

Not financial, legal, or planning advice. Always confirm with the s10.7 planning certificate and your own due diligence.
