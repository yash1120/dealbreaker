"""
DealBreaker - spatial spike
Proves the core hazard check works end-to-end on FREE, keyless data:

    address -> geocode (Nominatim) -> NSW Planning Portal Hazard ArcGIS REST
            -> bushfire-prone?  flood-planning area?

No API keys required.

Usage:
    python check_hazards.py "10 Macquarie St, Sydney NSW"
    python check_hazards.py            # runs the demo address set
"""
import sys
import time
import requests

NOMINATIM = "https://nominatim.openstreetmap.org/search"
HAZARD_BASE = (
    "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
    "ePlanning/Planning_Portal_Hazard/MapServer"
)
BUSHFIRE_LAYER = 229
FLOOD_LAYER = 230

# Nominatim policy requires a real, identifying User-Agent.
HEADERS = {
    "User-Agent": "DealBreaker-MVP-spike/0.1 (Sydney property check; contact: shorya.annie@gmail.com)"
}


def geocode(address):
    """Address string -> (lat, lon, display_name) via OSM Nominatim, or None."""
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
    if not data:
        return None
    top = data[0]
    return float(top["lat"]), float(top["lon"]), top.get("display_name", address)


def query_hazard(lon, lat, layer_id, out_fields="*"):
    """Point-in-polygon against an NSW hazard layer. Returns list of features."""
    url = f"{HAZARD_BASE}/{layer_id}/query"
    params = {
        "geometry": f"{lon},{lat}",          # ArcGIS point geometry = x,y = lon,lat
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,                          # we send WGS84; server reprojects
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": out_fields,
        "returnGeometry": "false",
        "f": "json",
    }
    last_err = None
    for _ in range(3):                         # gov ArcGIS can throw transient 500s
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json().get("features", [])
        except Exception as e:                 # noqa: BLE001 - spike-level retry
            last_err = e
            time.sleep(1.5)
    raise last_err


def check(address):
    print(f"\n=== {address} ===")
    geo = geocode(address)
    if not geo:
        print("  ! could not geocode")
        return
    lat, lon, display = geo
    print(f"  geocoded -> {lat:.5f}, {lon:.5f}")
    print(f"  ({display})")

    bf = query_hazard(lon, lat, BUSHFIRE_LAYER, "Category,d_Category")
    if bf:
        a = bf[0]["attributes"]
        print(f"  BUSHFIRE : PRONE  (Category {a.get('Category')} - {a.get('d_Category')})")
    else:
        print("  BUSHFIRE : not flagged")

    fl = query_hazard(lon, lat, FLOOD_LAYER, "EPI_NAME,LGA_NAME,LAY_CLASS")
    if fl:
        a = fl[0]["attributes"]
        print(f"  FLOOD    : EPI flood-planning area  ({a.get('LAY_CLASS')} / {a.get('LGA_NAME')} / {a.get('EPI_NAME')})")
    else:
        print("  FLOOD    : no EPI flood-planning flag  (NOT a guarantee it won't flood)")

    time.sleep(1)  # be polite to Nominatim between lookups


DEMOS = [
    "Sydney Opera House, Sydney NSW",   # CBD - expect clear
    "Windsor NSW 2756",                 # Hawkesbury - flood country
    "Faulconbridge NSW 2776",           # Blue Mountains - bushfire
    "Springwood NSW 2777",              # Blue Mountains - bushfire
]


if __name__ == "__main__":
    args = sys.argv[1:]
    targets = [" ".join(args)] if args else DEMOS
    for t in targets:
        try:
            check(t)
        except Exception as e:  # noqa: BLE001
            print(f"  ! error: {e}")
