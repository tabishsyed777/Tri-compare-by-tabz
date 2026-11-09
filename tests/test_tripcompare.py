import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from datetime import date
from tripcompare.models import Leg
from tripcompare.places import load_places
from tripcompare.nlp import parse
from tripcompare.planner import build_graph, enumerate_itineraries, connection_analysis, merge_legs
from tripcompare.providers import SeedProvider
from tripcompare.service import search

P = load_places(); TODAY = date(2026, 11, 9)  # a Monday


def test_parse_basic():
    r = parse("Akola to Mumbai on friday cheapest", P, TODAY)
    assert (r["origin"], r["dest"], r["pref"]) == ("akola", "mumbai", "cheapest") and r["date"] == date(2026, 11, 13)


def test_parse_reversed_and_alias():
    r = parse("to bangalore from nagpur tomorrow", P, TODAY)
    assert (r["origin"], r["dest"]) == ("nagpur", "bengaluru") and r["date"] == date(2026, 11, 10)


def test_parse_unknown_place_gives_error():
    assert parse("akola to atlantis", P, TODAY)["errors"]


def test_exclude_flights():
    r = search("akola to mumbai no flights", today=TODAY)
    assert r["ok"] and all(l["mode"] != "flight" for o in r["options"] for l in o["legs"])


def test_akola_mumbai_has_multimodal_options():
    r = search("akola to mumbai", today=TODAY)
    kinds = {o["kind"] for o in r["options"]}
    assert "Train" in kinds and "Bus" in kinds and any("Flight" in k for k in kinds)
    assert all(o["price_lo"] <= o["price_hi"] for o in r["options"])


def test_estimates_are_labelled_and_disclaimer_present():
    r = search("akola to mumbai", today=TODAY)
    assert all(o["price_kind"] == "estimate" for o in r["options"]) and "ESTIMATES" in r["disclaimer"]


def test_connection_saving_math_with_live_override():
    class Live:
        name = "fake-live"
        def legs(self, date=None):  # direct NAG-BOM expensive, via HYD cheap
            return [Leg("flight", "nagpur", "mumbai", 90, 9000, 9000, "live", "fake"),
                    Leg("flight", "nagpur", "hyderabad", 80, 2000, 2000, "live", "fake"),
                    Leg("flight", "hyderabad", "mumbai", 90, 2000, 2000, "live", "fake")]
    legs = merge_legs(SeedProvider().legs(), Live().legs())
    its = enumerate_itineraries(build_graph(legs), "nagpur", "mumbai")
    a = connection_analysis(its)
    assert a["saving_mid"] > 1000 and a["extra_min"] > 0 and "NOT protected" in a["text"]


def test_no_route_uses_labelled_fallback():
    from tripcompare.planner import PlannerConfig
    r = search("akola to pune", today=TODAY, cfg=PlannerConfig(max_legs=1))   # no direct seed route
    assert r["ok"] and r["notes"] and any("low confidence" in w.lower() for o in r["options"] for w in o["warnings"])


def test_same_origin_dest_rejected():
    assert not search("akola to akola")["ok"]
