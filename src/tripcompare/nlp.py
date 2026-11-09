"""Rule-based request parser (works offline). An LLM parser can replace `parse` via the same output shape:
{origin, dest, date, pref, exclude_modes, errors}. The LLM must only PARSE/EXPLAIN - never invent prices."""
import re
from datetime import date, timedelta

from .places import alias_map, suggest

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def parse_date(text, today):
    t = text.lower()
    if re.search(r"\bday after tomorrow\b", t): return today + timedelta(days=2)
    if re.search(r"\btomorrow\b", t): return today + timedelta(days=1)
    if re.search(r"\btoday\b", t): return today
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        try: return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError: return None
    m = re.search(r"\b(\d{1,2})\s*(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", t)
    if m:
        try:
            d = date(today.year, MONTHS[m[2]], int(m[1]))
            return d if d >= today else d.replace(year=today.year + 1)
        except ValueError: return None
    for i, w in enumerate(WEEKDAYS):
        if re.search(rf"\b{w}\b", t):
            return today + timedelta(days=(i - today.weekday()) % 7 or 7)
    return None


def parse(text, places, today=None):
    today = today or date.today()
    t = " " + text.lower() + " "
    amap = alias_map(places)
    found = []
    for alias, pid in sorted(amap.items(), key=lambda kv: -len(kv[0])):
        for m in re.finditer(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", t):
            if not any(s <= m.start() < e for s, e, _, _ in found):
                found.append((m.start(), m.end(), pid, t[max(0, m.start() - 6):m.start()].strip()))
    found.sort()
    origin = dest = None
    for _, _, pid, before in found:
        if before.endswith("from") and not origin: origin = pid
        elif before.endswith("to") and not dest: dest = pid
    rest = [p for _, _, p, _ in found if p not in (origin, dest)]
    if not origin and rest: origin = rest.pop(0)
    if not dest and rest: dest = rest.pop(0)
    errors = []
    if not origin or not dest:
        m = re.search(r"(?:from\s+)?([a-z ]+?)\s+to\s+([a-z ]+?)(?:\s+(?:on|for|by|tomorrow|today)\b|$)", t.strip())
        for label, val in (("origin", m and m[1].strip()), ("destination", m and m[2].strip())):
            if (label == "origin" and not origin) or (label == "destination" and not dest):
                sug = suggest(val, places) if val else []
                errors.append(f"Could not recognise the {label}" + (f" '{val}'. Did you mean: {', '.join(sug)}?" if sug else ". Try 'Akola to Mumbai'."))
    if origin and origin == dest:
        errors.append("Origin and destination are the same.")
    pref = "balanced"
    if re.search(r"\b(cheap|cheapest|budget|lowest|save)\b", t): pref = "cheapest"
    elif re.search(r"\b(fast|fastest|quick|quickest|urgent)\b", t): pref = "fastest"
    ex = []
    if re.search(r"\b(no|without|avoid)\s+(flights?|air)\b|\bby (bus|train)\b|\b(bus|train) only\b", t) and not re.search(r"\bby flight\b", t):
        ex.append("flight")
    if re.search(r"\b(no|without|avoid)\s+bus(es)?\b", t): ex.append("bus")
    if re.search(r"\b(no|without|avoid)\s+trains?\b", t): ex.append("train")
    return {"origin": origin, "dest": dest, "date": parse_date(text, today), "pref": pref, "exclude_modes": ex, "errors": errors}
