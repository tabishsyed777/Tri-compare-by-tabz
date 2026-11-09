"""Hand-off links so users can check LIVE prices on the provider's own site.
Only generic, public URL patterns are used. Add affiliate parameters via AFFILIATE (your own programs, per their terms)."""
from urllib.parse import quote_plus

AFFILIATE = {}   # e.g. {"redbus": "?utm_source=yourid"}  -> appended where noted; keep empty until you join a program


def links_for(leg, places, on_date=None):
    o, d = places[leg.origin], places[leg.dest]
    when = f" on {on_date.isoformat()}" if on_date else ""
    if leg.mode == "flight" and o.get("iata") and d.get("iata"):
        return [{"label": "Check live fares (Google Flights)",
                 "url": "https://www.google.com/travel/flights?q=" + quote_plus(f"Flights from {o['iata']} to {d['iata']}{when}")}]
    maps = ("https://www.google.com/maps/dir/?api=1&travelmode=transit&origin=" + quote_plus(o["name"]) +
            "&destination=" + quote_plus(d["name"]))
    if leg.mode == "bus":
        return [{"label": "Find buses (redBus)", "url": "https://www.redbus.in/" + AFFILIATE.get("redbus", "")},
                {"label": "Route on Google Maps", "url": maps}]
    if leg.mode == "train":
        return [{"label": "Check trains (IRCTC)", "url": "https://www.irctc.co.in/" + AFFILIATE.get("irctc", "")},
                {"label": "Route on Google Maps", "url": maps}]
    return [{"label": "Route on Google Maps", "url": maps}]
