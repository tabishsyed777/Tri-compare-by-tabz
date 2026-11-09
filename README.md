# TripCompare (MVP)

Type "Akola to Mumbai tomorrow cheapest" and get ranked options across **flight, bus and train**, including mixed
trips (e.g. bus to a nearby airport + flight), connecting-flight savings, and links to check live prices.

## Honest status
- **Prices are seed ESTIMATES** (`src/tripcompare/data/routes.json`), not live quotes or timetables. Every result is labelled
  `estimate` or `live`. Replace the seed with real providers (below).
- The web UI is a responsive natural-language search page that compares route options and explains connection estimates.
- Tested: 9 unit tests pass; CLI and web server smoke-tested. No external services are called.
- Seed numbers were written from general knowledge and have NOT been verified - check them before showing anyone.

## Run (Python 3.10+, no installs)
```bash
PYTHONPATH=src python -m tripcompare "Akola to Mumbai on friday cheapest"   # CLI
PYTHONPATH=src python -m tripcompare.server                                   # web UI at http://127.0.0.1:8000
PYTHONPATH=src python -m pytest tests            # if pytest installed; tests are plain functions
```

## How it answers your five requirements
| You asked | Where |
|---|---|
| Flight prices / cheapest | `planner.py` ranks; response has `highlights` via tags `cheapest`, `fastest`, `best balance` |
| Bus vs flight vs train to the destination | `enumerate_itineraries` builds single and mixed-mode trips (max 3 legs) |
| Which kinds of flights exist | `flight_options.kinds` (Direct flight, Connecting flights, Bus + Flight, ...) |
| Connecting flights and money saved | `connection_analysis`: compares with the nonstop (or best single-flight) option; warns about separate tickets |
| Natural-language interface | `nlp.py` rule-based parser (offline). An LLM can replace it with the same output shape |

## Data sources: what is allowed
There is no public Google API for flight/bus prices. Do not scrape Google Flights, MakeMyTrip, redBus, IRCTC etc.; their terms
forbid it. Legitimate routes, in order of effort:
1. **Deep links / affiliate links** (built in, `deeplinks.py`): user checks live price on the partner site; add your affiliate IDs.
2. **Licensed flight API** (Amadeus Self-Service, Duffel, ...): implement `providers/AmadeusProviderTemplate`. Later providers override seed prices.
3. **Open timetable data** (GTFS from agencies/data.gov.in, where available) for routes and times.
4. **Operator/partner feeds** for buses and trains; **user-reported fares** for small routes.
Always read each source's terms first.

## Design choices
- Transparent rules, every assumption a constant (`planner.py`): transfer buffers, airport access time/cost, value of time (Rs 250/h).
- Itinerary cost = legs + transfer/airport extras, shown as a range plus a typical value.
- Fallback distance-based guesses are labelled LOW confidence.
- LLMs should only parse requests and explain results, never invent prices.
- Web page renders results with `textContent` (no HTML injection); server limits request size; no stack traces leaked.

## Limits / next
No departure times, seat availability, date-specific prices, or booking. Hidden-city ticketing is intentionally excluded (violates airline terms).
See `docs/HANDOFF.md` for the roadmap and API contract.
