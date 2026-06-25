"""NSW Planning Portal hazard checks.

Keyless ArcGIS REST point-in-polygon queries against the NSW Planning Portal
Hazard MapServer. No API key, no GIS libraries -- the server does the
point-in-polygon for us; we just send a lat/long and read the result.

    Bush Fire Prone Land  -> layer 229
    EPI Flood Planning    -> layer 230
"""
import time
import requests

HAZARD_BASE = (
    "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
    "ePlanning/Planning_Portal_Hazard/MapServer"
)
BUSHFIRE_LAYER = 229
FLOOD_LAYER = 230
HEADERS = {"User-Agent": "DealBreaker/0.1 (Sydney property check)"}


def _query(lon, lat, layer_id, out_fields):
    """Point-in-polygon query. Returns the list of intersecting features."""
    url = f"{HAZARD_BASE}/{layer_id}/query"
    params = {
        "geometry": f"{lon},{lat}",          # ArcGIS point = x,y = lon,lat
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,                          # send WGS84; server reprojects
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": out_fields,
        "returnGeometry": "false",
        "f": "json",
    }
    last_err = None
    for _ in range(3):                         # gov ArcGIS can throw transient 5xx
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json().get("features", [])
        except Exception as e:                 # noqa: BLE001
            last_err = e
            time.sleep(1.0)
    raise last_err


def bushfire(lon, lat):
    feats = _query(lon, lat, BUSHFIRE_LAYER, "Category,d_Category")
    if not feats:
        return {"flagged": False}
    a = feats[0]["attributes"]
    return {
        "flagged": True,
        "category": a.get("Category"),
        "description": a.get("d_Category"),
    }


def flood(lon, lat):
    feats = _query(lon, lat, FLOOD_LAYER, "EPI_NAME,LGA_NAME,LAY_CLASS")
    if not feats:
        return {"flagged": False}
    a = feats[0]["attributes"]
    return {
        "flagged": True,
        "class": a.get("LAY_CLASS"),
        "lga": a.get("LGA_NAME"),
        "epi": a.get("EPI_NAME"),
    }
