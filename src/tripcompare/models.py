"""Core data types. Money is INR; time is minutes."""
from dataclasses import dataclass, field


@dataclass
class Leg:
    mode: str                 # "flight" | "bus" | "train"
    origin: str               # place id
    dest: str
    duration_min: int
    price_lo: int
    price_hi: int
    price_kind: str = "estimate"   # "estimate" | "live"
    source: str = "seed"
    note: str = ""

    @property
    def price_mid(self) -> float:
        return (self.price_lo + self.price_hi) / 2


@dataclass
class Itinerary:
    legs: list
    extras: list = field(default_factory=list)   # (label, minutes, lo, hi): transfers/airport access (assumptions)

    @property
    def total_min(self): return sum(l.duration_min for l in self.legs) + sum(e[1] for e in self.extras)
    @property
    def price_lo(self): return sum(l.price_lo for l in self.legs) + sum(e[2] for e in self.extras)
    @property
    def price_hi(self): return sum(l.price_hi for l in self.legs) + sum(e[3] for e in self.extras)
    @property
    def price_mid(self): return (self.price_lo + self.price_hi) / 2
    @property
    def n_flights(self): return sum(1 for l in self.legs if l.mode == "flight")
    @property
    def is_live(self): return all(l.price_kind == "live" for l in self.legs)

    @property
    def kind(self) -> str:
        modes = [l.mode for l in self.legs]
        if len(modes) == 1:
            return "Direct flight" if modes[0] == "flight" else modes[0].capitalize()
        if all(m == "flight" for m in modes):
            return f"Connecting flights ({len(modes) - 1} stop{'s' if len(modes) > 2 else ''})"
        parts, i = [], 0
        while i < len(modes):
            j = i
            while j < len(modes) and modes[j] == modes[i]:
                j += 1
            n = j - i
            parts.append(modes[i].capitalize() if modes[i] != "flight" else ("Flight" if n == 1 else f"{n} flights"))
            i = j
        return " + ".join(parts)

    def score(self, rupees_per_hour: float) -> float:
        return self.price_mid + rupees_per_hour * self.total_min / 60.0
