"""Single entry point used by CLI, web server, and any future frontend/LLM tool."""
from datetime import date as Date

from .deeplinks import links_for
from .nlp import parse
from .places import load_places
from .planner import (PlannerConfig, best_per_kind, build_graph, connection_analysis, enumerate_itineraries,
                      fallback_legs, merge_legs)
from .providers import SeedProvider

DISCLAIMER = ("Prices and durations are ESTIMATES from seed data unless marked 'live'. They are not timetables or quotes. "
              "Always confirm on the booking site before paying.")


def _fmt_it(it, places, on_date, cfg, tags):
    return {
        "kind": it.kind, "tags": tags,
        "route": " -> ".join([places[it.legs[0].origin]["name"]] + [places[l.dest]["name"] for l in it.legs]),
        "total_hours": round(it.total_min / 60, 1), "price_lo": round(it.price_lo), "price_hi": round(it.price_hi),
        "price_typical": round(it.price_mid), "price_kind": "live" if it.is_live else "estimate",
        "legs": [{"mode": l.mode, "from": places[l.origin]["name"], "to": places[l.dest]["name"], "minutes": l.duration_min,
                  "price_lo": l.price_lo, "price_hi": l.price_hi, "price_kind": l.price_kind, "source": l.source,
                  "note": l.note, "links": links_for(l, places, on_date)} for l in it.legs],
        "extras": [{"label": e[0], "minutes": e[1], "price_lo": e[2], "price_hi": e[3]} for e in it.extras],
        "warnings": (["Several separately booked tickets: a missed connection is not protected."] if len(it.legs) > 1 else [])
                    + (["Includes distance-based guesses (low confidence)."] if any(l.source == "fallback-distance" for l in it.legs) else []),
    }


def search(query=None, origin=None, dest=None, on_date=None, pref=None, exclude_modes=(), providers=None,
           places=None, today=None, cfg=None):
    places = places or load_places()
    providers = providers or [SeedProvider()]
    cfg = cfg or PlannerConfig()
    parsed = {"origin": origin, "dest": dest, "date": on_date, "pref": pref or "balanced", "exclude_modes": list(exclude_modes), "errors": []}
    if query:
        p = parse(query, places, today)
        for k in ("origin", "dest", "date", "pref"):
            parsed[k] = p[k] if (p[k] and not parsed.get(k) or k == "pref" and not pref) else parsed[k]
        parsed["exclude_modes"] = sorted(set(parsed["exclude_modes"]) | set(p["exclude_modes"]))
        parsed["errors"] = p["errors"]
    if parsed["errors"] or not parsed["origin"] or not parsed["dest"]:
        return {"ok": False, "errors": parsed["errors"] or ["Please give an origin and destination."], "disclaimer": DISCLAIMER}
    o, d = parsed["origin"], parsed["dest"]
    legs = merge_legs(*[p.legs(parsed["date"]) for p in providers])
    graph = build_graph(legs, tuple(parsed["exclude_modes"]))
    its = enumerate_itineraries(graph, o, d, cfg.max_legs)
    notes = []
    if not its:
        extra = [l for l in fallback_legs(places, o, d) if l.mode not in parsed["exclude_modes"]]
        its = enumerate_itineraries(build_graph(legs + extra, tuple(parsed["exclude_modes"])), o, d, cfg.max_legs)
        notes.append("No route in the data; showing distance-based guesses (low confidence).")
    if not its:
        return {"ok": False, "errors": ["No options found with the current filters."], "disclaimer": DISCLAIMER}
    best = best_per_kind(its, cfg)
    cheapest = min(its, key=lambda i: i.price_mid); fastest = min(its, key=lambda i: i.total_min); balanced = min(its, key=lambda i: i.score(cfg.rupees_per_hour))
    tag = lambda it: [t for t, x in (("cheapest", cheapest), ("fastest", fastest), ("best balance", balanced)) if x is it]
    ordered = {"cheapest": cheapest, "fastest": fastest, "balanced": balanced}[parsed["pref"]]
    options = sorted(best, key=lambda i: {"cheapest": i.price_mid, "fastest": i.total_min}.get(parsed["pref"], i.score(cfg.rupees_per_hour)))
    tagged = [i for i in options if tag(i)]
    options = (options[:6] + [i for i in tagged if i not in options[:6]])
    if o in places and not places[o].get("iata"):
        notes.append(f"{places[o]['name']}: {places[o].get('note') or 'no airport in the data'} Flights start from a nearby airport.")
    cheap_flight = min((i for i in its if i.n_flights), key=lambda i: i.price_mid, default=None)
    cheap_price = ordered.kind
    answer = (f"For {places[o]['name']} to {places[d]['name']}, the {parsed['pref']} pick is **{cheap_price}**: about Rs {ordered.price_lo:,}-{ordered.price_hi:,} "
              f"(typical Rs {ordered.price_mid:,.0f}), around {ordered.total_min / 60:.1f} h door to door. Cheapest overall: {cheapest.kind} (~Rs {cheapest.price_mid:,.0f}); "
              f"fastest: {fastest.kind} (~{fastest.total_min / 60:.1f} h).")
    return {"ok": True, "query": query, "parsed": {**parsed, "date": parsed["date"].isoformat() if parsed["date"] else None},
            "answer": answer, "options": [_fmt_it(i, places, parsed["date"], cfg, tag(i)) for i in options],
            "flight_options": {"cheapest_flight": _fmt_it(cheap_flight, places, parsed["date"], cfg, tag(cheap_flight)) if cheap_flight else None,
                               "kinds": sorted({i.kind for i in its if i.n_flights})},
            "connection_analysis": connection_analysis(its), "notes": notes, "n_routes_considered": len(its),
            "disclaimer": DISCLAIMER}
