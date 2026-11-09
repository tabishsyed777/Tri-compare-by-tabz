"""Price/route providers. Each returns Legs. Add real sources here WITHOUT touching the planner.

Rules for any provider you add:
  * Only use sources whose terms permit it (official API, affiliate feed, licensed data, your own data).
  * Do NOT scrape sites that forbid it.
  * Mark live prices price_kind="live" and set source="<provider name>".
Later providers override earlier ones for the same (origin, dest, mode).
"""
import json
from pathlib import Path

from ..models import Leg


class Provider:
    name = "base"

    def legs(self, date=None):  # -> list[Leg]
        raise NotImplementedError


class SeedProvider(Provider):
    """Rough, editable estimates from data/routes.json. NOT live prices, NOT timetables."""
    name = "seed"

    def __init__(self, path=None):
        self.path = Path(path or Path(__file__).parent.parent / "data" / "routes.json")

    def legs(self, date=None):
        out = []
        for r in json.loads(self.path.read_text())["routes"]:
            for a, b in ((r["a"], r["b"]), (r["b"], r["a"])):
                out.append(Leg(r["mode"], a, b, r["min"], r["lo"], r["hi"], "estimate", "seed", r.get("note", "")))
        return out


class AmadeusProviderTemplate(Provider):
    """TEMPLATE (not implemented). Sketch for a licensed flight-price source.

    1. Register for Amadeus Self-Service (or Duffel / another licensed API) and read its terms.
    2. Read keys from environment variables, never hard-code them.
    3. For each airport pair with place['iata'], call the flight-offers search for `date`,
       take min/max total price as price_lo/price_hi, duration from the itinerary, and return
       Leg("flight", a, b, minutes, lo, hi, price_kind="live", source="amadeus").
    4. Cache responses (prices expire) and respect rate limits/quotas.
    """
    name = "amadeus-template"

    def legs(self, date=None):
        raise NotImplementedError("Template only - implement with licensed API access.")
