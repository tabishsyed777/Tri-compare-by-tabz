"""Itinerary search + ranking. Transparent rules; every assumption is a constant you can edit."""
from dataclasses import dataclass

from .models import Itinerary, Leg
from .places import haversine_km

AIR = {"flight"}
cls = lambda m: "air" if m in AIR else "ground"
TRANSFER_MIN = {("ground", "ground"): 45, ("ground", "air"): 150, ("air", "ground"): 90, ("air", "air"): 120}
TRANSFER_COST = {("ground", "air"): (250, 600), ("air", "ground"): (250, 600), ("air", "air"): (0, 0), ("ground", "ground"): (0, 0)}
AIRPORT_ACCESS_START = (60, 300, 700)   # minutes, lo, hi: travel to airport + check-in
AIRPORT_ACCESS_END = (45, 300, 700)     # airport -> city centre


@dataclass
class PlannerConfig:
    max_legs: int = 3
    rupees_per_hour: float = 250.0      # value of time for the "best balance" ranking
    exclude_modes: tuple = ()


def build_graph(legs, exclude=()):
    g = {}
    for l in legs:
        if l.mode in exclude:
            continue
        g.setdefault(l.origin, []).append(l)
    return g


def merge_legs(*lists):
    """Later lists override earlier ones for the same (origin, dest, mode)."""
    m = {}
    for lst in lists:
        for l in lst:
            m[(l.origin, l.dest, l.mode)] = l
    return list(m.values())


def fallback_legs(places, a, b):
    """Rough ground estimates when the seed graph has no route. Low confidence, always labelled."""
    km = haversine_km(places[a], places[b]) * 1.3          # road/rail factor
    out = [Leg("bus", a, b, int(km / 45 * 60), int(km * 1.1), int(km * 2.2), "estimate", "fallback-distance",
               f"~{km:.0f} km by road; LOW confidence, distance-based guess"),
           Leg("train", a, b, int(km / 50 * 60), int(km * 0.5), int(km * 2.5), "estimate", "fallback-distance",
               f"~{km:.0f} km; LOW confidence, may not be a real route")]
    return out


def make_itinerary(legs):
    extras = []
    if legs[0].mode in AIR:
        extras.append(("Travel to airport + check-in", *AIRPORT_ACCESS_START))
    for a, b in zip(legs, legs[1:]):
        k = (cls(a.mode), cls(b.mode))
        lo, hi = TRANSFER_COST[k]
        extras.append((f"Transfer at {a.dest}", TRANSFER_MIN[k], lo, hi))
    if legs[-1].mode in AIR:
        extras.append(("Airport to destination", *AIRPORT_ACCESS_END))
    return Itinerary(list(legs), extras)


def enumerate_itineraries(graph, o, d, max_legs=3):
    out = []

    def dfs(node, seen, legs):
        if node == d:
            out.append(make_itinerary(legs)); return
        if len(legs) == max_legs:
            return
        for leg in graph.get(node, []):
            if leg.dest in seen:
                continue
            if legs and leg.mode == legs[-1].mode and leg.mode not in AIR:
                continue                                    # no bus->bus chains
            dfs(leg.dest, seen | {leg.dest}, legs + [leg])
    dfs(o, {o}, [])
    return out


def best_per_kind(its, cfg):
    best = {}
    for it in its:
        k = it.kind
        if k not in best or it.score(cfg.rupees_per_hour) < best[k].score(cfg.rupees_per_hour):
            best[k] = it
    return sorted(best.values(), key=lambda i: i.score(cfg.rupees_per_hour))


def connection_analysis(its):
    """Compare connecting flights with the fairest baseline: the nonstop flight if one exists,
    otherwise the best single-flight itinerary (which may include ground legs)."""
    multi = [i for i in its if i.n_flights >= 2]
    if not multi:
        return {"available": False, "text": "No connecting-flight option found in the current data."}
    cm = min(multi, key=lambda i: i.price_mid)
    direct = [i for i in its if len(i.legs) == 1 and i.n_flights == 1]
    single = direct or [i for i in its if i.n_flights == 1]
    via = [l.dest for l in cm.legs if l.mode == "flight"][:-1]
    if not single:
        return {"available": True, "saving_mid": None, "via": via,
                "text": "No single-flight option found; connecting flights are the only air route in the current data."}
    cs = min(single, key=lambda i: i.price_mid)
    saving = cs.price_mid - cm.price_mid
    extra = cm.total_min - cs.total_min
    base = "the nonstop flight" if direct else f"the best single-flight option ({cs.kind})"
    when = (f"adds about {extra / 60:.1f} h" if extra > 0 else f"is also about {-extra / 60:.1f} h faster")
    if saving > 0:
        text = (f"Connecting flights could save about Rs {saving:,.0f} versus {base} (typical estimates) and {when}. "
                "If booked as separate tickets, a missed connection is NOT protected - verify live prices and leave a long buffer.")
    else:
        text = (f"No saving: the cheapest connecting option is about Rs {-saving:,.0f} MORE than {base} and {when} "
                "(based on current estimates).")
    return {"available": True, "saving_mid": round(saving), "extra_min": extra, "via": via, "text": text}
