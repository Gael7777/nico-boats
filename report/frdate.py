# -*- coding: utf-8 -*-
"""French dates without depending on the system locale (fr_FR is not installed on the box).

    python3 report/frdate.py subject [YYYY-MM-DD]     -> "Nico Boats – 24 novembre 2026"
    python3 report/frdate.py long    [YYYY-MM-DD]     -> "Mardi 24 novembre 2026"
    python3 report/frdate.py fix "Nico Boats – 24 November 2026"   -> English month/day names translated
Default date: today in Europe/Zurich."""
import re, sys
from datetime import date, datetime

MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
          "août", "septembre", "octobre", "novembre", "décembre"]
MONTHS_SHORT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]
_EN_MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_EN_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def today_zurich():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Zurich")).date()
    except Exception:
        return date.today()

def as_date(d=None):
    if d is None:
        return today_zurich()
    if isinstance(d, str):
        return date.fromisoformat(d[:10])
    return d

def _day(n):
    return "1er" if n == 1 else str(n)

def fr_date(d=None):
    """'24 novembre 2026'"""
    d = as_date(d)
    return f"{_day(d.day)} {MONTHS[d.month - 1]} {d.year}"

def fr_date_short(d=None):
    """'24 nov. 2026'"""
    d = as_date(d)
    return f"{_day(d.day)} {MONTHS_SHORT[d.month - 1]} {d.year}"

def fr_date_long(d=None, capital=True):
    """'Mardi 24 novembre 2026'"""
    d = as_date(d)
    s = f"{DAYS[d.weekday()]} {fr_date(d)}"
    return s[0].upper() + s[1:] if capital else s

def subject(d=None, prefix="Nico Boats"):
    return f"{prefix} – {fr_date(d)}"

def fix_english(text):
    """Translate English month / weekday names left in a string (e.g. a subject built with `date +%B`)."""
    for en, fr in zip(_EN_DAYS, DAYS):
        text = re.sub(rf"\b{en}\b", fr, text)
    for en, fr in zip(_EN_MONTHS, MONTHS):
        text = re.sub(rf"\b{en}\b", fr, text)
    for en, fr in zip(_EN_MONTHS_SHORT, MONTHS_SHORT):
        text = re.sub(rf"\b{en}\b\.?", fr, text)
    return re.sub(r"\b0(\d) (?=[a-zéû])", r"\1 ", text)   # "03 décembre" -> "3 décembre"

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "subject"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    if cmd == "subject":
        print(subject(arg))
    elif cmd == "long":
        print(fr_date_long(arg))
    elif cmd == "short":
        print(fr_date_short(arg))
    elif cmd == "date":
        print(fr_date(arg))
    elif cmd == "fix":
        print(fix_english(arg or ""))
    else:
        sys.exit(__doc__)
