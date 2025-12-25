# utils/date_parser.py
from __future__ import annotations
from datetime import date, datetime
from typing import Optional
import re

import dateparser
from dateparser.search import search_dates

# Hint dateparser with the languages we commonly see (English, Turkish, Azerbaijani).
PREFERRED_LANGS = ["en", "tr", "az"]
_DIACRITICS_MAP = str.maketrans(
    {
        "ə": "e",
        "ı": "i",
        "ö": "o",
        "ü": "u",
        "ğ": "g",
        "ş": "s",
        "ç": "c",
        "Ə": "e",
        "İ": "i",
        "Ö": "o",
        "Ü": "u",
        "Ğ": "g",
        "Ş": "s",
        "Ç": "c",
        "â": "a",
        "î": "i",
        "û": "u",
    }
)
# Month name variants across English/Turkish/Azerbaijani.
_MONTH_BASES = [
    # English
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    # Turkish
    "ocak",
    "subat",
    "mart",
    "nisan",
    "mayis",
    "haziran",
    "temmuz",
    "agustos",
    "eylul",
    "ekim",
    "kasim",
    "aralik",
    # Azerbaijani
    "yanvar",
    "fevral",
    "aprel",
    "iyun",
    "iyul",
    "avqust",
    "sentyabr",
    "oktyabr",
    "noyabr",
    "dekabr",
]
_MONTH_TO_NUM = {
    # English
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    # Turkish
    "ocak": 1,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "agustos": 8,
    "eylul": 9,
    "ekim": 10,
    "kasim": 11,
    "aralik": 12,
    # Azerbaijani
    "yanvar": 1,
    "fevral": 2,
    "aprel": 4,
    "iyun": 6,
    "iyul": 7,
    "avqust": 8,
    "sentyabr": 9,
    "oktyabr": 10,
    "noyabr": 11,
    "dekabr": 12,
}
_MONTH_PATTERN = re.compile(rf"\b({'|'.join(_MONTH_BASES)})\w*", re.IGNORECASE)
_MONTH_ONLY_PATTERN = re.compile(rf"\b({'|'.join(_MONTH_TO_NUM.keys())})\b", re.IGNORECASE)


def _normalize_month_tokens(text: str) -> str:
    """
    Lowercase + strip diacritics + trim suffixes from month names
    so dateparser can recognize them (e.g., 'Martın' -> 'mart').
    """
    lowered = (text or "").lower()
    normalized = lowered.translate(_DIACRITICS_MAP)
    return _MONTH_PATTERN.sub(lambda m: m.group(1), normalized)


def _manual_month_day(text: str) -> Optional[date]:
    """
    Extract a month/day pair near a detected month name.
    Useful when search_dates finds only a month (no day) because of suffixes.
    """
    normalized = _normalize_month_tokens(text)
    if not normalized:
        return None

    for match in _MONTH_ONLY_PATTERN.finditer(normalized):
        month_num = _MONTH_TO_NUM.get(match.group(1).lower())
        if not month_num:
            continue

        window_start = max(0, match.start() - 8)
        window_end = min(len(normalized), match.end() + 8)
        window = normalized[window_start:window_end]

        day_match = re.search(r"\b([0-3]?\d)\b", window)
        if not day_match:
            continue

        day = int(day_match.group(1))
        year_match = re.search(r"\b(20\d{2})\b", normalized)
        year = int(year_match.group(1)) if year_match else date.today().year

        try:
            candidate = date(year, month_num, day)
        except ValueError:
            continue

        today = date.today()
        if candidate < today:
            try:
                candidate = date(today.year + 1, month_num, day)
            except ValueError:
                pass

        return candidate

    return None

def parse_date(value: str) -> Optional[date]:
    """
    Parses common date inputs. Supports:
    - YYYY-MM-DD
    - YYYY/MM/DD
    - DD.MM.YYYY
    - DD/MM/YYYY
    - Natural language dates (e.g., "5 Mart", "Martın 5-i") via dateparser
    If parsing fails, returns None.
    """
    if not value:
        return None

    v = value.strip()

    fmts = ["%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y", "%d/%m/%Y"]
    for fmt in fmts:
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            pass

    # Last resort: try fromisoformat-like cleanup
    try:
        return datetime.fromisoformat(v).date()
    except Exception:
        pass

    # Natural language fallback (helps with Azerbaijani/Turkish month names)
    parsed = dateparser.parse(
        v,
        languages=PREFERRED_LANGS,
        settings={"PREFER_DATES_FROM": "future"},
    )
    manual = _manual_month_day(v)
    if manual:
        if not parsed or parsed.date() != manual:
            return manual
    if parsed:
        return parsed.date()

    normalized = _normalize_month_tokens(v)
    if normalized and normalized != v:
        parsed = dateparser.parse(
            normalized,
            languages=PREFERRED_LANGS,
            settings={"PREFER_DATES_FROM": "future"},
        )
        manual = _manual_month_day(normalized)
        if manual:
            if not parsed or parsed.date() != manual:
                return manual
        if parsed:
            return parsed.date()
        if manual:
            return manual

    return None


def extract_first_date(text: str) -> Optional[date]:
    """
    Scan free-form text for the first date-like expression.
    Returns the next future occurrence when possible.
    """
    if not text:
        return None

    hits = search_dates(
        text,
        languages=PREFERRED_LANGS,
        settings={"PREFER_DATES_FROM": "future"},
    )
    if not hits:
        normalized = _normalize_month_tokens(text)
        if normalized and normalized != text:
            hits = search_dates(
                normalized,
                languages=PREFERRED_LANGS,
                settings={"PREFER_DATES_FROM": "future"},
            )
    if not hits:
        manual = _manual_month_day(text)
        return manual

    # search_dates returns [(matched_text, datetime), ...]
    match_text, dt = hits[0]
    if not any(char.isdigit() for char in str(match_text)):
        manual = _manual_month_day(text)
        if manual:
            return manual

    return dt.date()
