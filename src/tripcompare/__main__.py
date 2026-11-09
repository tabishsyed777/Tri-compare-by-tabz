import json, sys
from .service import search

q = " ".join(sys.argv[1:]) or "Akola to Mumbai cheapest"
r = search(q)
if not r["ok"]:
    print("\n".join(r["errors"])); sys.exit(1)
print(r["answer"].replace("**", "")); print()
for o in r["options"]:
    print(f"- {o['kind']:<28} Rs {o['price_lo']:>6,}-{o['price_hi']:<6,} ~{o['total_hours']:>4} h  {' '.join('['+t+']' for t in o['tags'])}\n    {o['route']}")
print("\nConnecting flights:", r["connection_analysis"]["text"])
for n in r["notes"]: print("Note:", n)
print("\n" + r["disclaimer"])
