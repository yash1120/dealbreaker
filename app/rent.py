"""Rent intelligence against NSW DCJ medians (data/rent.db).

  check_rent() -> 'is this listing fair?' (+ a too-cheap/scam tell)
  rent_map()   -> per-postcode medians with centroids, for the map layer
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "rent.db"

_BED = {"1": "1 Bedroom", "2": "2 Bedrooms", "3": "3 Bedrooms", "4": "4 or more Bedrooms"}
_DWELL = {
    "unit": "Flat/Unit", "flat": "Flat/Unit", "apartment": "Flat/Unit",
    "house": "House", "townhouse": "Townhouse",
    "any": "Total", "total": "Total", "": "Total",
}
_FRIENDLY = {"Flat/Unit": "unit", "House": "house", "Townhouse": "townhouse", "Total": "home"}


def _lookup(postcode, bedrooms, dwelling):
    con = sqlite3.connect(DB)
    try:
        cur = con.execute(
            "SELECT median_rent, q1_rent, q3_rent, new_bonds, quarter FROM median_rent "
            "WHERE postcode=? AND bedrooms=? AND dwelling_type=? AND median_rent IS NOT NULL "
            "ORDER BY quarter DESC LIMIT 1",
            (postcode, bedrooms, dwelling),
        )
        return cur.fetchone()
    finally:
        con.close()


def check_rent(postcode, weekly_rent, beds, dwelling="any"):
    if not (postcode and weekly_rent and beds):
        return {"status": "bad_input"}
    if not DB.exists():
        return {"status": "no_db"}

    bedrooms = _BED.get(str(beds).strip()[:1])
    if bedrooms is None:
        return {"status": "bad_input"}
    dwelling_key = _DWELL.get((dwelling or "any").lower(), "Total")

    row = _lookup(postcode, bedrooms, dwelling_key)
    used_dwelling = dwelling_key
    if not row and dwelling_key != "Total":     # specific type suppressed -> all types
        row = _lookup(postcode, bedrooms, "Total")
        used_dwelling = "Total"
    if not row:
        return {"status": "no_data", "postcode": postcode, "bedrooms_label": bedrooms}

    median, q1, q3, new_bonds, quarter = row
    return {
        "status": "ok",
        "listing_rent": float(weekly_rent),
        "median": float(median),
        "q1": float(q1) if q1 else float(median),
        "q3": float(q3) if q3 else float(median),
        "new_bonds": int(new_bonds) if new_bonds else 0,
        "quarter": quarter,
        "postcode": postcode,
        "bedrooms_label": bedrooms,
        "dwelling_label": _FRIENDLY.get(used_dwelling, used_dwelling),
    }


def rent_map(beds="2", dwelling="any"):
    """All NSW postcodes (with a centroid) and their median rent for beds/dwelling."""
    if not DB.exists():
        return []
    bedrooms = _BED.get(str(beds).strip()[:1], "2 Bedrooms")
    dwelling_key = _DWELL.get((dwelling or "any").lower(), "Total")

    con = sqlite3.connect(DB)
    try:
        rows = con.execute(
            "SELECT m.postcode, c.lat, c.lon, m.median_rent, m.q1_rent, m.q3_rent, m.new_bonds "
            "FROM median_rent m JOIN postcode_centroid c ON c.postcode = m.postcode "
            "WHERE m.bedrooms = ? AND m.dwelling_type = ? AND m.median_rent IS NOT NULL "
            "AND m.quarter = (SELECT MAX(quarter) FROM median_rent)",
            (bedrooms, dwelling_key),
        ).fetchall()
    except sqlite3.OperationalError:
        return []   # centroid table not built yet
    finally:
        con.close()

    return [
        {
            "postcode": r[0], "lat": round(r[1], 5), "lon": round(r[2], 5),
            "median": int(r[3]),
            "q1": int(r[4]) if r[4] else None,
            "q3": int(r[5]) if r[5] else None,
            "bonds": int(r[6]) if r[6] else 0,
        }
        for r in rows
    ]
