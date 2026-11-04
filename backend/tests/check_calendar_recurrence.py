"""Comprobación rápida: python tests/check_calendar_recurrence.py (desde backend/)."""

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.errors import AppError  # noqa: E402
from app.services.calendar_recurrence import (  # noqa: E402
    expand_dates, normalize_rrule, parse_rrule, rule_matches, to_display, to_utc, utc_iso,
)

D = date.fromisoformat


def z(local: str, strict: bool = False) -> str:
    return utc_iso(to_utc(datetime.fromisoformat(local), "Europe/Madrid", strict=strict))


# Diario 09:00 Madrid a través del cambio de hora del 25-10-2026
days = expand_dates(parse_rrule("FREQ=DAILY"), D("2026-10-19"), D("2026-10-19"), D("2026-10-28"))
got = {d.isoformat(): z(f"{d}T09:00:00")[11:16] for d in days}
assert got["2026-10-19"] == "07:00" and got["2026-10-24"] == "07:00", got
assert got["2026-10-25"] == "08:00" and got["2026-10-26"] == "08:00", got
print("diario Madrid:", got["2026-10-24"], "->", got["2026-10-25"])

# hora inexistente / ambigua
try:
    z("2026-03-29T02:30:00", strict=True)
    raise SystemExit("debía fallar")
except AppError as e:
    assert e.code == "nonexistent_local_time"
assert z("2026-03-29T02:30:00") == "2026-03-29T01:30:00.000Z"
assert z("2026-10-25T02:30:00", strict=True) == "2026-10-25T00:30:00.000Z"
assert to_display(to_utc(datetime(2026, 10, 26, 9), "Europe/Madrid", strict=True), "Europe/Madrid") == "2026-10-26T09:00:00"

# COUNT con ventana tardía (cuenta desde DTSTART)
r = parse_rrule("FREQ=DAILY;COUNT=10")
assert expand_dates(r, D("2026-01-01"), D("2026-01-08"), D("2026-02-01")) == [D("2026-01-08"), D("2026-01-09"), D("2026-01-10")]
assert expand_dates(r, D("2026-01-01"), D("2026-03-01"), D("2026-04-01")) == []

# BYDAY semanal con INTERVAL=2 (dtstart lunes 2026-01-05)
r = parse_rrule("FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,WE")
assert [d.isoformat() for d in expand_dates(r, D("2026-01-05"), D("2026-01-05"), D("2026-02-02"))] == [
    "2026-01-05", "2026-01-07", "2026-01-19", "2026-01-21"]
assert rule_matches(r, D("2026-01-05"), D("2026-01-21")) and not rule_matches(r, D("2026-01-05"), D("2026-01-14"))

# BYMONTHDAY=31 omite meses cortos; -1FR; ventana lejana sin COUNT
r = parse_rrule("FREQ=MONTHLY;BYMONTHDAY=31")
assert [d.isoformat() for d in expand_dates(r, D("2026-01-31"), D("2026-01-01"), D("2026-06-01"))] == [
    "2026-01-31", "2026-03-31", "2026-05-31"]
r = parse_rrule("FREQ=MONTHLY;BYDAY=-1FR")
assert [d.isoformat() for d in expand_dates(r, D("2026-01-30"), D("2026-01-01"), D("2026-04-01"))] == [
    "2026-01-30", "2026-02-27", "2026-03-27"]
assert expand_dates(parse_rrule("FREQ=DAILY"), D("1990-01-01"), D("2026-05-01"), D("2026-05-03")) == [D("2026-05-01"), D("2026-05-02")]
assert expand_dates(parse_rrule("FREQ=YEARLY"), D("2024-02-29"), D("2024-01-01"), D("2033-01-01")) == [D("2024-02-29"), D("2028-02-29"), D("2032-02-29")]

# normalización y errores
assert normalize_rrule("rrule:freq=weekly;byday=we,mo;until=20261231T000000Z") == "FREQ=WEEKLY;BYDAY=MO,WE;UNTIL=20261231"
for bad in ("FREQ=DAILY;COUNT=2;UNTIL=20260101", "FREQ=DAILY;FOO=1", "FREQ=DAILY;FREQ=DAILY",
            "FREQ=WEEKLY;BYDAY=1MO", "FREQ=DAILY;INTERVAL=0", "FREQ=DAILY;COUNT=5001", "FREQ=MONTHLY;BYMONTHDAY=32"):
    try:
        parse_rrule(bad)
        raise SystemExit(f"debía fallar: {bad}")
    except AppError as e:
        assert e.details[0].code == "invalid_rrule"
print("OK")
