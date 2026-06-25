"""Door-to-door public-transport commute via the TfNSW Trip Planner API.

Free, but needs a user-registered API key (TFNSW_API_KEY in .env). Until a key
is set, commute() returns {"status": "unconfigured"} and the UI hides the leg.

API: https://api.transport.nsw.gov.au/v1/tp/trip  (EFA rapidJSON)
Auth header: Authorization: apikey <KEY>
Coordinates are passed as  lon:lat:EPSG:4326  (note the order).
"""
from datetime import datetime, timedelta

import requests

from . import config, geocode

TRIP_URL = "https://api.transport.nsw.gov.au/v1/tp/trip"

# EFA transport product classes: <99 == an actual public-transport mode
# (1 train, 2 metro, 4 light rail, 5/11 bus, 7 coach, 9 ferry); 99/100 == walk.
_MODE_NAMES = {1: "Train", 2: "Metro", 4: "Light Rail", 5: "Bus", 7: "Coach", 9: "Ferry", 11: "Bus"}


def _next_weekday_0900():
    """A representative weekday-9am ARRIVAL time, so we model a real commute."""
    d = datetime.now() + timedelta(days=1)
    while d.weekday() >= 5:        # Sat=5, Sun=6 -> roll to Monday
        d += timedelta(days=1)
    return d.strftime("%Y%m%d"), "0900"


def _summarise_journey(journey):
    legs = journey.get("legs", []) or []
    total_seconds = sum(leg.get("duration", 0) or 0 for leg in legs)
    modes = []
    for leg in legs:
        cls = leg.get("transportation", {}).get("product", {}).get("class", 99)
        if cls is not None and cls < 99:
            modes.append(_MODE_NAMES.get(cls, "Transit"))
    return {
        "minutes": round(total_seconds / 60),
        "changes": max(0, len(modes) - 1),
        "modes": modes,
    }


def commute(prop_lat, prop_lon, work_address):
    """Return a commute summary from the property to the work address.

    Status values: ok | unconfigured | no_work_geocode | no_route | error
    """
    if not config.TFNSW_API_KEY:
        return {"status": "unconfigured"}

    work = geocode.geocode(work_address)
    if not work:
        return {"status": "no_work_geocode"}

    date, time = _next_weekday_0900()
    params = {
        "outputFormat": "rapidJSON",
        "coordOutputFormat": "EPSG:4326",
        "depArrMacro": "arr",                 # arrive-by
        "itdDate": date,
        "itdTime": time,
        "type_origin": "coord",
        "name_origin": f"{prop_lon}:{prop_lat}:EPSG:4326",
        "type_destination": "coord",
        "name_destination": f"{work['lon']}:{work['lat']}:EPSG:4326",
        "calcNumberOfTrips": 3,
        "TfNSWTR": "true",
        "version": "10.2.1.42",
    }
    headers = {"Authorization": f"apikey {config.TFNSW_API_KEY}", "Accept": "application/json"}

    try:
        r = requests.get(TRIP_URL, params=params, headers=headers, timeout=20)
        if r.status_code == 401:
            return {"status": "error", "detail": "TfNSW key rejected (401)."}
        r.raise_for_status()
        journeys = r.json().get("journeys", []) or []
        if not journeys:
            return {"status": "no_route"}
        best = min(
            (_summarise_journey(j) for j in journeys),
            key=lambda s: s["minutes"],
        )
        best["status"] = "ok"
        best["work"] = work["display_name"]
        return best
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "detail": str(e)}
