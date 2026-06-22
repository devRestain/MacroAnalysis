from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .calendar_description_service import load_calendar_event_definitions
from .indicator_explanation_loader import iter_indicator_explanation_items, load_indicator_explanations
from .indicator_registry import INDICATOR_SPECS

Locale = str

DEFAULT_LOCALE = "ko"
FALLBACK_LOCALE = "en"
SUPPORTED_LOCALES = {"ko", "en"}
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATIC_METADATA_TRANSLATION_PATCH_PATH = DATA_DIR / "static_metadata_translation_patch_ko_first_v1.json"

TRANSLATABLE_INDICATOR_FIELDS = (
    "display_name",
    "short_label",
    "description",
    "market_role",
    "higher_meaning",
    "lower_meaning",
    "watch_points",
)

TRANSLATABLE_CALENDAR_FIELDS = (
    "display_name",
    "short_label",
    "description",
    "market_role",
    "higher_meaning",
    "lower_meaning",
    "watch_points",
    "watch_items",
)

ENUM_LABELS: dict[str, dict[str, dict[str, str]]] = {
    "ko": {
        "importance": {"high": "높음", "medium": "보통", "medium_high": "중상", "low": "낮음"},
        "status": {"scheduled": "예정", "released": "발표", "pending": "대기", "success": "성공", "failed": "실패"},
        "signal": {"green": "안정", "yellow": "주의", "red": "경계"},
        "summary_type": {"macro": "거시", "market": "시장", "calendar": "캘린더", "communication": "커뮤니케이션"},
        "provider": {
            "fred": "FRED",
            "yfinance": "Yahoo Finance",
            "exchangerate-api": "ExchangeRate API",
            "seed": "정적 시드",
            "unknown": "미정",
        },
        "source": {
            "fred": "FRED",
            "yfinance": "Yahoo Finance",
            "seed": "정적 시드",
            "unknown": "미정",
            "federal reserve": "연방준비제도",
        },
        "institution": {"federal reserve": "연방준비제도"},
        "event_type": {
            "macro_release": "경제지표 발표",
            "fomc_meeting": "FOMC 회의",
            "statement": "성명",
            "speech": "연설",
            "testimony": "의회 증언",
            "communication": "커뮤니케이션",
        },
        "category": {
            "rates": "금리",
            "macro": "거시",
            "credit": "신용",
            "equity": "주식",
            "fx": "외환",
            "real": "실물",
            "sector": "섹터",
            "fomc": "FOMC",
            "fedwatch": "FedWatch",
            "inflation": "물가",
            "labor": "고용",
            "growth": "성장",
            "housing": "주택",
            "policy": "정책",
            "liquidity": "유동성",
            "volatility": "변동성",
            "communication": "커뮤니케이션",
        },
        "prob_method": {"fed_funds_futures_estimate": "연방기금선물 추정"},
    },
    "en": {
        "importance": {"high": "high", "medium": "medium", "medium_high": "medium-high", "low": "low"},
        "status": {"scheduled": "scheduled", "released": "released", "pending": "pending", "success": "success", "failed": "failed"},
        "signal": {"green": "green", "yellow": "yellow", "red": "red"},
        "summary_type": {"macro": "macro", "market": "market", "calendar": "calendar", "communication": "communication"},
        "provider": {
            "fred": "FRED",
            "yfinance": "Yahoo Finance",
            "exchangerate-api": "ExchangeRate API",
            "seed": "seed",
            "unknown": "unknown",
        },
        "source": {
            "fred": "FRED",
            "yfinance": "Yahoo Finance",
            "seed": "seed",
            "unknown": "unknown",
            "federal reserve": "Federal Reserve",
        },
        "institution": {"federal reserve": "Federal Reserve"},
        "event_type": {
            "macro_release": "Macro release",
            "fomc_meeting": "FOMC meeting",
            "statement": "Statement",
            "speech": "Speech",
            "testimony": "Testimony",
            "communication": "Communication",
        },
        "category": {
            "rates": "Rates",
            "macro": "Macro",
            "credit": "Credit",
            "equity": "Equity",
            "fx": "FX",
            "real": "Real economy",
            "sector": "Sector",
            "fomc": "FOMC",
            "fedwatch": "FedWatch",
            "inflation": "Inflation",
            "labor": "Labor",
            "growth": "Growth",
            "housing": "Housing",
            "policy": "Policy",
            "liquidity": "Liquidity",
            "volatility": "Volatility",
            "communication": "Communication",
        },
        "prob_method": {"fed_funds_futures_estimate": "Fed funds futures estimate"},
    },
}


def normalize_locale(lang: str | None) -> Locale:
    if lang in SUPPORTED_LOCALES:
        return lang
    return DEFAULT_LOCALE


@lru_cache(maxsize=1)
def load_static_metadata_translation_patch() -> dict[str, Any]:
    if not STATIC_METADATA_TRANSLATION_PATCH_PATH.exists():
        return {}
    return json.loads(STATIC_METADATA_TRANSLATION_PATCH_PATH.read_text(encoding="utf-8"))


def label_for(group: str, value: str | None, *, locale: str, fallback: str | None = None) -> str | None:
    if value is None:
        return fallback
    normalized = value.lower() if group in {"provider", "source", "institution"} else value
    return (
        ENUM_LABELS.get(locale, {}).get(group, {}).get(normalized)
        or ENUM_LABELS[DEFAULT_LOCALE].get(group, {}).get(normalized)
        or fallback
        or value
    )


@lru_cache(maxsize=1)
def _indicator_items_by_key() -> dict[str, dict[str, Any]]:
    payload = load_indicator_explanations()
    return {item["key"]: item for item in iter_indicator_explanation_items(payload)}


@lru_cache(maxsize=1)
def _calendar_items_by_key() -> dict[str, dict[str, Any]]:
    payload = load_calendar_event_definitions()
    items = payload.get("calendar_events") or []
    return {str(item.get("key") or item.get("event_key")): item for item in items}


@lru_cache(maxsize=1)
def _indicator_label_patch_by_key() -> dict[str, dict[str, Any]]:
    payload = load_static_metadata_translation_patch()
    for collection in payload.get("collections") or []:
        if collection.get("entity") == "indicator_labels":
            return {
                str(item.get("key")): dict(item.get("field_values") or {})
                for item in collection.get("items") or []
            }
    return {}


@lru_cache(maxsize=1)
def _communication_label_patch_by_event_type() -> dict[str, dict[str, Any]]:
    payload = load_static_metadata_translation_patch()
    for collection in payload.get("collections") or []:
        if collection.get("entity") == "communication_static_labels":
            return {
                str(item.get("key")): dict(item.get("field_values") or {})
                for item in collection.get("items") or []
            }
    return {}


def _pick_translated_fields(
    item: dict[str, Any] | None,
    *,
    locale: str,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    if not item:
        return {}

    translations = item.get("translations") if isinstance(item.get("translations"), dict) else {}
    requested = translations.get(locale) if isinstance(translations.get(locale), dict) else {}
    alternate_locale = FALLBACK_LOCALE if locale == DEFAULT_LOCALE else DEFAULT_LOCALE
    alternate = translations.get(alternate_locale) if isinstance(translations.get(alternate_locale), dict) else {}

    result: dict[str, Any] = {}
    for field in fields:
        for candidate in (requested, alternate, item):
            value = candidate.get(field) if isinstance(candidate, dict) else None
            if value not in (None, "", []):
                result[field] = value
                break
    return result


def _indicator_label_fields(indicator_key: str, *, locale: str) -> dict[str, Any]:
    patch = _indicator_label_patch_by_key().get(indicator_key) or {}
    if locale != "ko":
        return {}
    return {
        "display_name": patch.get("display_name_ko"),
        "short_label": patch.get("short_label_ko"),
        "category_label": patch.get("category_label_ko"),
        "provider_label": patch.get("provider_label_ko"),
    }


def _communication_label_fields(event_type: str | None, *, locale: str) -> dict[str, Any]:
    if locale != "ko" or not event_type:
        return {}
    return _communication_label_patch_by_event_type().get(event_type) or {}


def localized_indicator_fields(indicator_key: str, *, locale: str) -> dict[str, Any]:
    item = _indicator_items_by_key().get(indicator_key)
    localized = _pick_translated_fields(item, locale=locale, fields=TRANSLATABLE_INDICATOR_FIELDS)
    label_patch = _indicator_label_fields(indicator_key, locale=locale)
    if label_patch.get("display_name"):
        localized["display_name"] = label_patch["display_name"]
    if label_patch.get("short_label"):
        localized["short_label"] = label_patch["short_label"]
    if item:
        localized.setdefault("category", item.get("category"))
        localized.setdefault("related_indicators", item.get("related_indicators"))
    return localized


def localized_calendar_fields(event_key: str, *, locale: str) -> dict[str, Any]:
    item = _calendar_items_by_key().get(event_key)
    localized = _pick_translated_fields(item, locale=locale, fields=TRANSLATABLE_CALENDAR_FIELDS)
    if item:
        localized.setdefault("category", item.get("category"))
        localized.setdefault("related_indicators", item.get("related_indicators") or [])
        localized.setdefault("provider", item.get("provider"))
        localized.setdefault("event_definition", item.get("event_definition") or {})
    return localized


def localize_indicator_explanation_dict(payload: dict[str, Any], *, locale: str) -> dict[str, Any]:
    localized = dict(payload)
    fields = localized_indicator_fields(str(payload.get("indicator_key") or ""), locale=locale)
    if fields:
        localized.update({key: value for key, value in fields.items() if value not in (None, "", [])})

    indicator_key = str(localized.get("indicator_key") or "")
    label_patch = _indicator_label_fields(indicator_key, locale=locale)
    provider = localized.get("provider")
    if not provider and indicator_key in INDICATOR_SPECS:
        provider = INDICATOR_SPECS[indicator_key].source
    localized["provider"] = provider
    localized["provider_label"] = label_patch.get("provider_label") or label_for("provider", provider, locale=locale, fallback=provider)
    localized["category_label"] = label_patch.get("category_label") or label_for("category", localized.get("category"), locale=locale, fallback=localized.get("category"))
    display_text = dict(localized.get("display_text") or {})
    for field in ("short_label", "description", "market_role", "higher_meaning", "lower_meaning", "watch_points"):
        if localized.get(field) not in (None, "", []):
            display_text[field] = localized.get(field)
    localized["display_text"] = display_text or None
    return localized


def localize_snapshot_dict(payload: dict[str, Any], *, locale: str) -> dict[str, Any]:
    localized = dict(payload)
    indicator_key = str(localized.get("key") or "")
    fields = localized_indicator_fields(indicator_key, locale=locale)
    if fields.get("display_name"):
        localized["label"] = fields["display_name"]
    label_patch = _indicator_label_fields(indicator_key, locale=locale)
    localized["category_label"] = label_patch.get("category_label") or label_for("category", localized.get("category"), locale=locale, fallback=localized.get("category"))
    provider = INDICATOR_SPECS[indicator_key].source if indicator_key in INDICATOR_SPECS else None
    localized["provider_label"] = label_patch.get("provider_label") or label_for("provider", provider, locale=locale, fallback=provider)
    localized["signal_label"] = label_for("signal", localized.get("signal"), locale=locale, fallback=localized.get("signal"))
    return localized


def localize_calendar_event_dict(payload: dict[str, Any], *, locale: str) -> dict[str, Any]:
    localized = dict(payload)
    event_key = str(localized.get("event_key") or "")
    fields = localized_calendar_fields(event_key, locale=locale)
    if fields:
        if fields.get("display_name"):
            localized["display_name"] = fields["display_name"]
        if fields.get("short_label"):
            localized["short_name"] = fields["short_label"]
        if fields.get("description"):
            localized["beginner_description"] = fields["description"]
        if fields.get("market_role"):
            localized["why_it_matters"] = fields["market_role"]
        if fields.get("watch_items"):
            localized["watch_items"] = fields["watch_items"]

    localized["event_type_label"] = label_for("event_type", localized.get("event_type"), locale=locale, fallback=localized.get("event_type"))
    localized["category_label"] = label_for("category", localized.get("category"), locale=locale, fallback=localized.get("category"))
    localized["importance_label"] = label_for("importance", localized.get("importance"), locale=locale, fallback=localized.get("importance"))
    localized["status_label"] = label_for("status", localized.get("status"), locale=locale, fallback=localized.get("status"))
    localized["source_label"] = label_for("source", localized.get("source"), locale=locale, fallback=localized.get("source"))
    return localized


def localize_fomc_overview_payload(payload: dict[str, Any], *, locale: str) -> dict[str, Any]:
    localized = dict(payload)
    meetings = []
    for meeting in payload.get("meetings") or []:
        localized_meeting = dict(meeting)
        event_key = localized_meeting.get("event_key")
        if event_key:
            fields = localized_calendar_fields(str(event_key), locale=locale)
            if fields.get("display_name"):
                localized_meeting["display_name"] = fields["display_name"]
        event_type = "fomc_meeting" if event_key == "FOMC_MEETING" else None
        communication_labels = _communication_label_fields(event_type, locale=locale)
        if communication_labels.get("event_type_label_ko"):
            localized_meeting["event_type_label"] = communication_labels["event_type_label_ko"]
        if communication_labels.get("source_label_ko"):
            localized_meeting["source_label"] = communication_labels["source_label_ko"]
        if communication_labels.get("institution_label_ko"):
            localized_meeting["institution_label"] = communication_labels["institution_label_ko"]
        meetings.append(localized_meeting)
    localized["meetings"] = meetings

    fedwatch = payload.get("fedwatch")
    if isinstance(fedwatch, dict):
        localized["fedwatch"] = {
            **fedwatch,
            "prob_method_label": label_for("prob_method", fedwatch.get("prob_method"), locale=locale, fallback=fedwatch.get("prob_method")),
        }
    return localized
