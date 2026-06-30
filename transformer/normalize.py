from __future__ import annotations

import re
import unicodedata
from typing import Any

import phonenumbers
import pycountry
from dateutil import parser

from transformer.skills import canonicalize_skill


JUNK_VALUES = {"", "n/a", "na", "none", "null", "see resume", "-", "--", "unknown"}
EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)
BARE_YEAR_RE = re.compile(r"^\d{4}$")

COUNTRY_ALIASES = {
    "india": "IN",
    "in": "IN",
    "usa": "US",
    "us": "US",
    "u.s.": "US",
    "u.s.a.": "US",
    "united states": "US",
    "united states of america": "US",
    "uk": "GB",
    "united kingdom": "GB",
}


def is_junk(raw: Any) -> bool:
    if raw is None:
        return True
    if not isinstance(raw, str):
        return False
    return raw.strip().lower() in JUNK_VALUES


def clean_text(raw: Any) -> str | None:
    if is_junk(raw):
        return None
    value = unicodedata.normalize("NFC", str(raw)).strip()
    value = re.sub(r"\s+", " ", value)
    return value or None


def normalize_email(raw: Any) -> str | None:
    value = clean_text(raw)
    if not value:
        return None
    value = value.lower()
    return value if EMAIL_RE.match(value) else None


def normalize_phone(raw: Any, region: str = "IN") -> str | None:
    value = clean_text(raw)
    if not value:
        return None
    try:
        parsed = phonenumbers.parse(value, region.upper() if region else None)
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return None


def normalize_date(raw: Any) -> str | None:
    value = clean_text(raw)
    if not value:
        return None
    lowered = value.lower()
    if lowered in {"present", "current", "now"}:
        return None
    if BARE_YEAR_RE.match(value):
        return f"{value}-01"
    try:
        dt = parser.parse(value, default=parser.parse("1900-01-01"), fuzzy=False)
        return f"{dt.year:04d}-{dt.month:02d}"
    except (ValueError, OverflowError, parser.ParserError):
        return None


def normalize_country(raw: Any) -> str | None:
    value = clean_text(raw)
    if not value:
        return None
    key = value.lower()
    if key in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[key]
    try:
        country = pycountry.countries.lookup(value)
        return country.alpha_2
    except LookupError:
        return None


def normalize_skill(raw: Any) -> str | None:
    value, _ = canonicalize_skill(str(raw) if raw is not None else None)
    return value


def normalize_link(raw: Any) -> str | None:
    value = clean_text(raw)
    if not value:
        return None
    if re.match(r"^https?://[^\s]+$", value, re.IGNORECASE):
        return value.rstrip("/")
    return None


def normalize_year(raw: Any) -> int | None:
    if raw is None or is_junk(raw):
        return None
    match = re.search(r"\b(19|20)\d{2}\b", str(raw))
    if not match:
        return None
    return int(match.group(0))
