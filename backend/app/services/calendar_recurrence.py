"""Tiempo y recurrencia: subconjunto RRULE propio (sin dependencias) y conversión local<->UTC.

Se guarda hora local + zona IANA; UTC es derivado. Las series se expanden en lectura.
"""

import calendar
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.errors import AppError

_FREQS = ("DAILY", "WEEKLY", "MONTHLY", "YEARLY")
_DAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
_KEYS = frozenset({"FREQ", "INTERVAL", "COUNT", "UNTIL", "BYDAY", "BYMONTHDAY"})
_BYDAY_RE = re.compile(r"^([+-]?\d{1,2})?(MO|TU|WE|TH|FR|SA|SU)$")
_UNTIL_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})(?:T\d{6}Z)?$")
_MAX_PERIODS = 100_000  # tope duro de iteraciones por expansión


@dataclass(frozen=True)
class Rule:
    freq: str
    interval: int
    count: int | None
    until: date | None
    byday: tuple[str, ...]
    bymonthday: tuple[int, ...]


def _bad(message: str) -> AppError:
    return AppError("invalid_rrule", message, status_code=422)


def _int(value: str, name: str, low: int, high: int) -> int:
    if not re.fullmatch(r"[+-]?\d{1,6}", value):
        raise _bad(f"{name} debe ser un entero.")
    number = int(value)
    if not low <= number <= high:
        raise _bad(f"{name} fuera de rango ({low}..{high}).")
    return number


def _byday_key(token: str) -> tuple[int, int]:
    match = _BYDAY_RE.match(token)
    assert match
    return _DAYS.index(match.group(2)), int(match.group(1) or 0)


def parse_rrule(text: str) -> Rule:
    if not isinstance(text, str) or not text.strip():
        raise _bad("RRULE vacía.")
    body = text.strip()
    if body.upper().startswith("RRULE:"):
        body = body[6:]
    parts: dict[str, str] = {}
    for chunk in body.split(";"):
        if not chunk:
            continue
        key, sep, value = chunk.partition("=")
        key = key.strip().upper()
        if not sep or not value.strip():
            raise _bad("Parte de RRULE mal formada.")
        if key not in _KEYS:
            raise _bad(f"Clave RRULE no admitida: {key[:20]}.")
        if key in parts:
            raise _bad(f"Clave RRULE repetida: {key}.")
        parts[key] = value.strip().upper()
    freq = parts.get("FREQ")
    if freq not in _FREQS:
        raise _bad("FREQ debe ser DAILY, WEEKLY, MONTHLY o YEARLY.")
    interval = _int(parts["INTERVAL"], "INTERVAL", 1, 999) if "INTERVAL" in parts else 1
    count = _int(parts["COUNT"], "COUNT", 1, 5000) if "COUNT" in parts else None
    until = None
    if "UNTIL" in parts:
        match = _UNTIL_RE.match(parts["UNTIL"])
        if not match:
            raise _bad("UNTIL debe ser AAAAMMDD o AAAAMMDDTHHMMSSZ.")
        try:
            until = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            raise _bad("UNTIL no es una fecha válida.") from None
    if count is not None and until is not None:
        raise _bad("COUNT y UNTIL no pueden combinarse.")
    byday: set[str] = set()
    if "BYDAY" in parts:
        for token in parts["BYDAY"].split(","):
            match = _BYDAY_RE.match(token)
            if not match:
                raise _bad("BYDAY inválido.")
            if match.group(1) is not None:
                ordinal = int(match.group(1))
                if ordinal == 0 or abs(ordinal) > 5:
                    raise _bad("Ordinal de BYDAY fuera de rango (±1..5).")
                if freq not in ("MONTHLY", "YEARLY"):
                    raise _bad("BYDAY con ordinal solo en MONTHLY o YEARLY.")
                token = f"{ordinal}{match.group(2)}"
            byday.add(token)
    bymonthday: set[int] = set()
    if "BYMONTHDAY" in parts:
        if freq == "WEEKLY":
            raise _bad("BYMONTHDAY no es válido con WEEKLY.")
        for token in parts["BYMONTHDAY"].split(","):
            day = _int(token, "BYMONTHDAY", -31, 31)
            if day == 0:
                raise _bad("BYMONTHDAY no puede ser 0.")
            bymonthday.add(day)
    return Rule(
        freq=freq,
        interval=interval,
        count=count,
        until=until,
        byday=tuple(sorted(byday, key=_byday_key)),
        bymonthday=tuple(sorted(bymonthday)),
    )


def normalize_rrule(text: str) -> str:
    rule = parse_rrule(text)
    out = [f"FREQ={rule.freq}"]
    if rule.interval != 1:
        out.append(f"INTERVAL={rule.interval}")
    if rule.byday:
        out.append("BYDAY=" + ",".join(rule.byday))
    if rule.bymonthday:
        out.append("BYMONTHDAY=" + ",".join(str(d) for d in rule.bymonthday))
    if rule.count is not None:
        out.append(f"COUNT={rule.count}")
    if rule.until is not None:
        out.append(f"UNTIL={rule.until:%Y%m%d}")
    return ";".join(out)


# --- expansión ---------------------------------------------------------------


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _month_dates(rule: Rule, dtstart: date, year: int, month: int) -> set[date]:
    """Fechas de un mes según BYDAY/BYMONTHDAY (intersección); sin BY*: día de DTSTART."""
    last = calendar.monthrange(year, month)[1]
    by_md: set[int] = set()
    for value in rule.bymonthday:
        day = value if value > 0 else last + 1 + value
        if 1 <= day <= last:
            by_md.add(day)
    by_wd: set[int] = set()
    if rule.byday:
        weekdays: dict[int, list[int]] = {i: [] for i in range(7)}
        for day in range(1, last + 1):
            weekdays[date(year, month, day).weekday()].append(day)
        for token in rule.byday:
            idx, ordinal = _byday_key(token)
            days = weekdays[idx]
            if ordinal == 0:
                by_wd.update(days)
            elif -len(days) <= ordinal <= len(days) and ordinal != 0:
                by_wd.add(days[ordinal - 1] if ordinal > 0 else days[ordinal])
    if rule.byday and rule.bymonthday:
        chosen = by_md & by_wd
    elif rule.byday:
        chosen = by_wd
    elif rule.bymonthday:
        chosen = by_md
    else:
        chosen = {dtstart.day} if dtstart.day <= last else set()
    return {date(year, month, day) for day in chosen}


def _period_start(rule: Rule, dtstart: date, n: int) -> date:
    step = n * rule.interval
    if rule.freq == "DAILY":
        return dtstart + timedelta(days=step)
    if rule.freq == "WEEKLY":
        return _monday(dtstart) + timedelta(weeks=step)
    if rule.freq == "MONTHLY":
        year, month = divmod(dtstart.year * 12 + dtstart.month - 1 + step, 12)
        return date(year, month + 1, 1)
    return date(dtstart.year + step, 1, 1)


def _period_dates(rule: Rule, dtstart: date, n: int) -> list[date]:
    start = _period_start(rule, dtstart, n)
    if rule.freq == "DAILY":
        found = {start}
        if rule.byday and _DAYS[start.weekday()] not in {t.lstrip("+-0123456789") for t in rule.byday}:
            found = set()
        if rule.bymonthday:
            last = calendar.monthrange(start.year, start.month)[1]
            allowed = {v if v > 0 else last + 1 + v for v in rule.bymonthday}
            if start.day not in allowed:
                found = set()
    elif rule.freq == "WEEKLY":
        idxs = {_byday_key(t)[0] for t in rule.byday} or {dtstart.weekday()}
        found = {start + timedelta(days=i) for i in idxs}
    elif rule.freq == "MONTHLY":
        found = _month_dates(rule, dtstart, start.year, start.month)
    else:
        found = _month_dates(rule, dtstart, start.year, dtstart.month)
        found = {d.replace(year=start.year) for d in found}
    if n == 0:
        found.add(dtstart)  # DTSTART es siempre la primera ocurrencia
    return sorted(d for d in found if d >= dtstart)


def _first_period(rule: Rule, dtstart: date, target: date) -> int:
    if target <= dtstart:
        return 0
    if rule.freq == "DAILY":
        gap = (target - dtstart).days
    elif rule.freq == "WEEKLY":
        gap = (_monday(target) - _monday(dtstart)).days // 7
    elif rule.freq == "MONTHLY":
        gap = (target.year * 12 + target.month) - (dtstart.year * 12 + dtstart.month)
    else:
        gap = target.year - dtstart.year
    return max(0, gap // rule.interval)


def expand_dates(
    rule: Rule,
    dtstart: date,
    window_start: date,
    window_end_exclusive: date,
    limit: int = 1000,
) -> list[date]:
    if window_end_exclusive <= window_start or limit <= 0:
        return []
    result: list[date] = []
    emitted = 0
    # Con COUNT hay que contar desde DTSTART; sin COUNT se salta hacia la ventana.
    n = 0 if rule.count is not None else _first_period(rule, dtstart, window_start)
    for _ in range(_MAX_PERIODS):
        try:
            if _period_start(rule, dtstart, n) >= window_end_exclusive:
                break
            dates = _period_dates(rule, dtstart, n)
        except (ValueError, OverflowError):  # fuera de 0001..9999
            break
        for d in dates:
            if rule.until is not None and d > rule.until:
                return result
            emitted += 1
            if window_start <= d < window_end_exclusive:
                result.append(d)
                if len(result) >= limit:
                    return result
            if rule.count is not None and emitted >= rule.count:
                return result
        n += 1
    return result


def rule_matches(rule: Rule, dtstart: date, day: date) -> bool:
    if day < dtstart:
        return False
    return bool(expand_dates(rule, dtstart, day, day + timedelta(days=1), limit=1))


# --- tiempo ------------------------------------------------------------------


def _zone(tz: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError, OSError, TypeError):
        raise AppError("invalid_timezone", "Zona horaria IANA no válida.", status_code=422) from None


def to_utc(local: datetime, tz: str, *, strict: bool) -> datetime:
    zone = _zone(tz)
    naive = local.replace(tzinfo=None, fold=0)
    # fold=0: hora ambigua -> primera; hueco -> desfase anterior al hueco (RFC 5545).
    utc = naive.replace(tzinfo=zone).astimezone(UTC)
    if strict and utc.astimezone(zone).replace(tzinfo=None) != naive:
        raise AppError(
            "nonexistent_local_time",
            "Esa hora local no existe en la zona indicada (cambio de hora).",
            status_code=422,
        )
    return utc


def utc_iso(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone(UTC)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def to_display(utc: datetime, tz: str) -> str:
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=UTC)
    return utc.astimezone(_zone(tz)).strftime("%Y-%m-%dT%H:%M:%S")


def today_in(tz: str) -> date:
    return datetime.now(_zone(tz)).date()
