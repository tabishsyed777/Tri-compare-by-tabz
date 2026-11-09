# Handoff notes (for the next tool/developer)

## Architecture
`nlp.parse` -> `service.search` -> (providers.legs -> planner.build_graph -> enumerate_itineraries -> best_per_kind / connection_analysis) -> JSON.
Frontends (web page, CLI, a future chat UI, mobile) only call `service.search(query=...)` or POST `/api/search {"query": "..."}`.

## API contract (POST /api/search)
Request: `{"query": "Akola to Mumbai tomorrow cheapest"}` (1-300 chars).
Response (ok): `answer`, `parsed{origin,dest,date,pref,exclude_modes}`, `options[]` (kind, tags, route, total_hours, price_lo/hi/typical,
price_kind, legs[] with links, extras[], warnings[]), `flight_options`, `connection_analysis`, `notes`, `disclaimer`.
Response (error): `{"ok": false, "errors": [...]}`.

## Priority tasks
1. Verify/replace `data/routes.json` and `places.json` with real data; add more cities (consider a geocoder + nearest-airport lookup).
2. Implement one licensed flight provider (Amadeus/Duffel) behind `providers.Provider`; cache; keep keys in env vars.
3. Add departure times/frequency (GTFS or operator data) so "connections" use real schedules instead of fixed buffers.
4. LLM parser: same output shape as `nlp.parse`; validate output against `places.json` ids; never let it produce prices.
5. Production wrapper: FastAPI (or Next.js API route) around `service.search`; rate limiting; HTTPS; privacy policy; analytics consent.
6. Affiliate programs: fill `deeplinks.AFFILIATE`; disclose commissions to users.
7. Add price-calibration tests against real quotes; show "last updated" per leg.

## Do not
Scrape sites that forbid it; present estimates as live prices; offer hidden-city tricks; store users' queries without consent.
