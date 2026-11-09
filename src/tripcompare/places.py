import difflib, json, math, re
from pathlib import Path

DATA = Path(__file__).parent / "data"


def load_places(path=None):
    return {p["id"]: p for p in json.loads(Path(path or DATA / "places.json").read_text())}


def alias_map(places):
    m = {}
    for pid, p in places.items():
        for a in [pid, p["name"].lower(), *p.get("aliases", [])] + ([p["iata"].lower()] if p.get("iata") else []):
            m[a.lower()] = pid
    return m


def suggest(text, places, n=3):
    names = list(alias_map(places))
    return [alias_map(places)[x] for x in difflib.get_close_matches(text.lower(), names, n=n, cutoff=0.6)]


def haversine_km(a, b):
    r = 6371.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dl = math.radians(b["lon"] - a["lon"]); dp = p2 - p1
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))
