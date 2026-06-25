"""Turn raw check results into a green/amber/red verdict the UI can render.

Each *_status() returns a uniform check dict:
    {key, title, status (clear|warn|alert|unknown), label, detail}
finalize() combines a list of checks into {level, headline, checks}.
"""

# status severity, worst-wins ("unknown" never escalates the headline)
_ORDER = {"alert": 3, "warn": 2, "unknown": 1, "clear": 0}


def bushfire_status(bf):
    if not bf.get("flagged"):
        return {
            "key": "bushfire", "title": "Bushfire", "status": "clear",
            "label": "Not flagged",
            "detail": "No NSW Bush Fire Prone Land mapping at this location.",
        }
    cat = bf.get("category")
    desc = bf.get("description") or "Bush Fire Prone Land"
    return {
        "key": "bushfire", "title": "Bushfire",
        "status": "alert" if cat == 1 else "warn",
        "label": f"Bushfire prone (Cat {cat})",
        "detail": (
            f"Mapped Bush Fire Prone Land - {desc}. Likely needs a BAL assessment "
            "and bushfire-rated construction, and can lift insurance premiums."
        ),
    }


def flood_status(fl):
    if not fl.get("flagged"):
        return {
            "key": "flood", "title": "Flood", "status": "unknown",
            "label": "No flood-planning flag",
            "detail": (
                "Not in a mapped EPI Flood Planning Area. This is NOT a guarantee - "
                "NSW flood mapping is patchy and many councils map flooding outside "
                "the LEP. Always check the s10.7 planning certificate."
            ),
        }
    return {
        "key": "flood", "title": "Flood", "status": "warn",
        "label": "Flood planning area",
        "detail": (
            f"In a mapped EPI Flood Planning Area ({fl.get('lga')} / {fl.get('epi')}). "
            "Development controls apply - check flood levels and insurance."
        ),
    }


def commute_status(c):
    if c.get("status") == "ok":
        mins, ch = c["minutes"], c["changes"]
        modes = ", ".join(c.get("modes") or []) or "walk"
        level = "clear" if mins <= 35 else "warn" if mins <= 55 else "alert"
        ch_txt = "direct" if ch == 0 else f"{ch} change" + ("s" if ch > 1 else "")
        return {
            "key": "commute", "title": "Commute", "status": level,
            "label": f"{mins} min, {ch_txt}",
            "detail": f"Weekday ~9am arrival to {c.get('work', 'your work')} via {modes}.",
        }
    msgs = {
        "unconfigured": "Add a free TfNSW key (TFNSW_API_KEY in .env) to enable the commute check.",
        "no_work_geocode": "Couldn't locate that work address - add the suburb and 'NSW'.",
        "no_route": "No public-transport route found for a weekday 9am arrival.",
        "error": c.get("detail", "Commute lookup failed."),
    }
    return {
        "key": "commute", "title": "Commute", "status": "unknown",
        "label": "Unavailable", "detail": msgs.get(c.get("status"), "Commute unavailable."),
    }


def rent_status(r):
    if r.get("status") != "ok":
        msgs = {
            "no_db": "Rent data not loaded yet (run data/ingest_rent.py).",
            "no_data": (
                f"No median-rent data for postcode {r.get('postcode')} / "
                f"{r.get('bedrooms_label', 'that size')} this quarter (too few bonds lodged)."
            ),
            "bad_input": "Enter a weekly rent and choose the number of bedrooms.",
        }
        return {
            "key": "rent", "title": "Rent", "status": "unknown",
            "label": "No comparison", "detail": msgs.get(r.get("status"), "Rent check unavailable."),
        }

    rent, median, q1, q3 = r["listing_rent"], r["median"], r["q1"], r["q3"]
    pct = round((rent - median) / median * 100)
    sign = "+" if pct >= 0 else ""
    basis = (
        f"${rent:.0f}/wk vs ${median:.0f} median ({sign}{pct}%) for a "
        f"{r['bedrooms_label'].lower()} {r['dwelling_label']} in {r['postcode']}. "
        f"Based on {r['new_bonds']} new bonds ({r['quarter']})."
    )

    if rent < q1 * 0.6:   # far below market => classic bait/scam tell
        return {
            "key": "rent", "title": "Rent", "status": "warn",
            "label": f"Suspiciously cheap ({sign}{pct}%)",
            "detail": (
                "Priced far below the local market - a classic bait/scam tell. Never pay a "
                "holding deposit or transfer money before inspecting in person. " + basis
            ),
        }
    if rent > q3:
        return {
            "key": "rent", "title": "Rent", "status": "warn",
            "label": f"Above market (+{pct}%)",
            "detail": "Above the top quartile for this postcode - room to negotiate or keep looking. " + basis,
        }
    label = "Below market" if rent <= q1 else "Around market"
    return {
        "key": "rent", "title": "Rent", "status": "clear",
        "label": f"{label} ({sign}{pct}%)", "detail": basis,
    }


def finalize(checks):
    checks = [c for c in checks if c]
    worst = max((c["status"] for c in checks), key=lambda s: _ORDER[s]) if checks else "clear"
    if worst == "alert":
        level, headline = "red", "Serious red flags - dig deeper before you inspect"
    elif worst == "warn":
        level, headline = "amber", "Some flags worth checking before you commit"
    else:
        level, headline = "green", "No major flags at this point"
    return {"level": level, "headline": headline, "checks": checks}
