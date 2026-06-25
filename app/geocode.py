"""Address geocoding via OpenStreetMap Nominatim.

MVP-grade: keyless and free, with a simple in-memory cache so each unique
address only hits Nominatim once (respects their 1 req/s policy). The known
weak spot is AU street-level precision -- the roadmap upgrade is the free
G-NAF address file for authoritative property-level geocoding.
"""
import requests

NOMINATIM = "https://nominatim.openstreetmap.org/search"
HEADERS = {
    "User-Agent": "DealBreaker/0.1 (Sydney property check; contact: shorya.annie@gmail.com)"
}

_cache = {}


def geocode(address):
    """Return {'lat','lon','display_name'} for an address, or None if not found."""
    key = address.strip().lower()
    if key in _cache:
        return _cache[key]

    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "countrycodes": "au",
        "addressdetails": 1,
    }
    r = requests.get(NOMINATIM, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()

    result = None
    if data:
        top = data[0]
        result = {
            "lat": float(top["lat"]),
            "lon": float(top["lon"]),
            "display_name": top.get("display_name", address),
            "postcode": (top.get("address") or {}).get("postcode"),
        }
    _cache[key] = result
    return result
