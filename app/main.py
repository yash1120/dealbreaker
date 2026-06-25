"""DealBreaker API + static frontend.

    GET /api/check?address=...[&work=...&rent=...&beds=...&dwelling=...]
        -> geocode + bushfire + flood (+ optional commute + rent) verdict (JSON)
    GET /api/rent-map?beds=2[&dwelling=...]
        -> per-postcode median rents with centroids, for the map layer
    GET /  -> the UI
"""
import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from . import commute, geocode, hazards, rent as rent_mod, verdict

app = FastAPI(title="DealBreaker", description="Sydney property background check")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_PC = re.compile(r"\b(2\d{3})\b")  # NSW postcodes


@app.get("/api/check")
def check(
    address: str = Query(..., min_length=3),
    work: Optional[str] = None,
    rent: Optional[float] = None,
    beds: Optional[str] = None,
    dwelling: Optional[str] = None,
):
    geo = geocode.geocode(address)
    if not geo:
        raise HTTPException(status_code=404, detail="Couldn't find that address. Try adding the suburb and 'NSW'.")

    lat, lon = geo["lat"], geo["lon"]
    bf = hazards.bushfire(lon, lat)
    fl = hazards.flood(lon, lat)
    checks = [verdict.bushfire_status(bf), verdict.flood_status(fl)]

    if work:
        checks.append(verdict.commute_status(commute.commute(lat, lon, work)))

    if rent and beds:
        m = _PC.search(address)
        postcode = int(m.group(1)) if m else (
            int(geo["postcode"]) if str(geo.get("postcode") or "").isdigit() else None
        )
        checks.append(verdict.rent_status(rent_mod.check_rent(postcode, rent, beds, dwelling)))

    return {
        "address": geo["display_name"],
        "lat": lat,
        "lon": lon,
        "verdict": verdict.finalize(checks),
    }


@app.get("/api/rent-map")
def rent_map(beds: str = "2", dwelling: Optional[str] = None):
    return {"beds": beds, "points": rent_mod.rent_map(beds, dwelling)}


# Serve the single-page UI. Mounted last so /api/* routes win.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
