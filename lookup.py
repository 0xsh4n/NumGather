"""
NumGather 2.0 — phone number intelligence engine.
Deterministic lookups via libphonenumber + India MSC database.
"""

from __future__ import annotations

from typing import Any

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberType, carrier, geocoder, timezone

import areadatabase

VERSION = "2.0.0"

NUMBER_TYPE_NAMES = {
    PhoneNumberType.FIXED_LINE: "fixed_line",
    PhoneNumberType.MOBILE: "mobile",
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_line_or_mobile",
    PhoneNumberType.TOLL_FREE: "toll_free",
    PhoneNumberType.PREMIUM_RATE: "premium_rate",
    PhoneNumberType.SHARED_COST: "shared_cost",
    PhoneNumberType.VOIP: "voip",
    PhoneNumberType.PERSONAL_NUMBER: "personal_number",
    PhoneNumberType.PAGER: "pager",
    PhoneNumberType.UAN: "uan",
    PhoneNumberType.VOICEMAIL: "voicemail",
    PhoneNumberType.UNKNOWN: "unknown",
}


def analyze_number(raw: str, region: str | None = None) -> dict[str, Any]:
    """
    Build a structured intelligence report for a phone number.

    Args:
        raw: Phone number string (prefer E.164 with +country_code).
        region: Default region if number has no country code (e.g. "IN", "US").
    """
    result: dict[str, Any] = {
        "version": VERSION,
        "input": raw.strip() if raw else "",
        "valid": False,
        "possible": False,
        "error": None,
    }

    if not raw or not str(raw).strip():
        result["error"] = "empty_number"
        return result

    try:
        phone = phonenumbers.parse(raw.strip(), region)
    except NumberParseException as exc:
        result["error"] = f"parse_error: {exc}"
        return result

    ntype = phonenumbers.number_type(phone)
    country = geocoder.description_for_number(phone, "en") or None
    isp = carrier.name_for_number(phone, "en") or None
    zones = list(timezone.time_zones_for_number(phone)) or []

    e164 = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)
    international = phonenumbers.format_number(
        phone, phonenumbers.PhoneNumberFormat.INTERNATIONAL
    )
    national = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.NATIONAL)
    rfc3966 = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.RFC3966)

    india_matches = areadatabase.lookup_india(e164)
    india_info = None
    if india_matches:
        # Best match: first unique circle/operator (DB ordered by prefix blocks)
        best = india_matches[0]
        india_info = {
            "circle": best["circle"],
            "operator_db": best["operator"],
            "prefix": best["prefix"],
            "all_matches": india_matches[:5],
        }

    region_code = phonenumbers.region_code_for_number(phone)

    result.update(
        {
            "valid": phonenumbers.is_valid_number(phone),
            "possible": phonenumbers.is_possible_number(phone),
            "country_code": phone.country_code,
            "national_number": str(phone.national_number),
            "region_code": region_code,
            "country": country,
            "location": country,
            "carrier": isp,
            "number_type": NUMBER_TYPE_NAMES.get(ntype, "unknown"),
            "timezones": zones,
            "formats": {
                "e164": e164,
                "international": international,
                "national": national,
                "rfc3966": rfc3966,
            },
            "india": india_info,
            "insights": _build_insights(
                valid=phonenumbers.is_valid_number(phone),
                possible=phonenumbers.is_possible_number(phone),
                ntype=NUMBER_TYPE_NAMES.get(ntype, "unknown"),
                region_code=region_code,
                carrier=isp,
                india=india_info,
                timezones=zones,
            ),
        }
    )
    return result


def _build_insights(
    *,
    valid: bool,
    possible: bool,
    ntype: str,
    region_code: str | None,
    carrier: str | None,
    india: dict | None,
    timezones: list[str],
) -> list[str]:
    """Rule-based intelligence notes (no LLM)."""
    notes: list[str] = []

    if not possible:
        notes.append("Number length/pattern is not possible for its country code.")
    elif not valid:
        notes.append(
            "Number is possible but fails full validation — may be incomplete, "
            "ported incorrectly, or a fake/test pattern."
        )
    else:
        notes.append("Number passes libphonenumber validation for its region.")

    type_notes = {
        "mobile": "Typical mobile subscriber number.",
        "fixed_line": "Landline / fixed-line number.",
        "fixed_line_or_mobile": "Could be either mobile or fixed line in this region.",
        "toll_free": "Toll-free service number (not a personal handset).",
        "premium_rate": "Premium-rate number — often paid services.",
        "voip": "VoIP-assigned number — may not map to a physical SIM/handset.",
        "uan": "Universal Access Number — company/shared routing.",
        "personal_number": "Personal numbering service (call forwarding style).",
    }
    if ntype in type_notes:
        notes.append(type_notes[ntype])

    if carrier:
        notes.append(f"Original/network carrier reported as: {carrier}.")
    else:
        notes.append(
            "No carrier name from libphonenumber (common for some countries "
            "or after number portability)."
        )

    if india:
        notes.append(
            f"India MSC prefix {india['prefix']} maps to {india['circle']} "
            f"circle (DB operator: {india['operator_db']})."
        )
        if carrier and india["operator_db"]:
            db_op = india["operator_db"].upper()
            lib_op = carrier.upper()
            if db_op not in lib_op and lib_op not in db_op:
                notes.append(
                    "Carrier from libphonenumber differs from India MSC DB — "
                    "likely MNP (mobile number portability) or stale prefix data."
                )

    if timezones:
        notes.append(f"Likely timezone(s): {', '.join(timezones)}.")

    if region_code:
        notes.append(f"ISO region: {region_code}.")

    return notes


def format_report(data: dict[str, Any], *, color: bool = True) -> str:
    """Pretty text report for terminal output."""
    c = _Colors if color else _NoColors

    if data.get("error"):
        return f"{c.RED}[!] Error:{c.RESET} {data['error']}"

    rule = "-" * 52
    lines = [
        f"{c.CYAN}{rule}{c.RESET}",
        f"{c.BOLD}  NumGather {data.get('version', VERSION)} - Intelligence Report{c.RESET}",
        f"{c.CYAN}{rule}{c.RESET}",
        f"  Input          : {data.get('input')}",
        f"  Valid          : {_yn(data.get('valid'), c)}",
        f"  Possible       : {_yn(data.get('possible'), c)}",
        f"  Country        : {data.get('country') or 'N/A'}",
        f"  Region (ISO)   : {data.get('region_code') or 'N/A'}",
        f"  Country code   : +{data.get('country_code')}",
        f"  National #     : {data.get('national_number')}",
        f"  Number type    : {data.get('number_type')}",
        f"  Carrier / ISP  : {data.get('carrier') or 'N/A'}",
        f"  Timezone(s)    : {', '.join(data.get('timezones') or []) or 'N/A'}",
    ]

    fmt = data.get("formats") or {}
    lines.extend(
        [
            f"  E.164          : {fmt.get('e164', 'N/A')}",
            f"  International  : {fmt.get('international', 'N/A')}",
            f"  National fmt   : {fmt.get('national', 'N/A')}",
        ]
    )

    india = data.get("india")
    if india:
        lines.extend(
            [
                f"  India circle   : {india.get('circle')}",
                f"  India operator : {india.get('operator_db')} (MSC {india.get('prefix')})",
            ]
        )

    insights = data.get("insights") or []
    if insights:
        lines.append(f"{c.CYAN}{rule}{c.RESET}")
        lines.append(f"{c.BOLD}  Insights{c.RESET}")
        for note in insights:
            lines.append(f"  {c.YELLOW}*{c.RESET} {note}")

    lines.append(f"{c.CYAN}{rule}{c.RESET}")
    return "\n".join(lines)


def _yn(value: bool | None, c: type) -> str:
    if value:
        return f"{c.GREEN}yes{c.RESET}"
    return f"{c.RED}no{c.RESET}"


class _Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"


class _NoColors:
    RESET = BOLD = RED = GREEN = YELLOW = CYAN = ""
