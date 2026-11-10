#!/usr/bin/env python3
"""Validate the portable Account Intel envelope; prose grounding still needs review."""
from __future__ import annotations
import argparse
from datetime import date
import json
import math
from pathlib import Path
import sys
from urllib.parse import urlparse


def valid_date(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("date must be YYYY-MM-DD")
    return date.fromisoformat(value)


def source_url(value):
    if not isinstance(value, str) or urlparse(value).scheme not in ("http", "https") or not urlparse(value).netloc:
        raise ValueError("fact requires an HTTP(S) source URL")


def validate_brief(obj):
    if not isinstance(obj, dict) or obj.get("schema_version") != "account-intel/v2":
        raise ValueError("unsupported brief schema")
    as_of = valid_date(obj.get("as_of"))
    company = obj.get("company")
    if not isinstance(company, dict) or any(not isinstance(company.get(k), str) or not company[k].strip() for k in ("uuid", "permalink", "name", "url")):
        raise ValueError("company requires canonical uuid, permalink, name and url")
    source_url(company["url"])
    parsed = urlparse(company["url"])
    if parsed.hostname not in ("crunchbase.com", "www.crunchbase.com") or parsed.path.rstrip("/") != "/organization/" + company["permalink"]:
        raise ValueError("company URL must identify its canonical organization")
    scope, coverage = obj.get("scope"), obj.get("coverage")
    if not isinstance(scope, dict) or not scope.get("purpose") or scope.get("seller_mode") not in ("tailored", "product-neutral"):
        raise ValueError("scope requires purpose and seller_mode")
    start, end = scope.get("event_start"), scope.get("event_end")
    if (start is None) != (end is None):
        raise ValueError("event window requires both boundaries")
    if start is not None and not valid_date(start) <= valid_date(end) <= as_of:
        raise ValueError("invalid event window")
    if not isinstance(coverage, dict) or type(coverage.get("complete")) is not bool or not isinstance(coverage.get("limitations"), list) or not isinstance(coverage.get("sources"), list):
        raise ValueError("coverage requires complete, limitations and sources")
    if obj.get("meeting_type") not in ("first", "follow_up") or not isinstance(obj.get("summary"), str):
        raise ValueError("meeting_type and summary required")
    for key in ("talking_points", "recent_events", "people", "competitors", "notes"):
        if not isinstance(obj.get(key), list):
            raise ValueError(key + " must be an array")
    if "crm" not in obj or (obj["crm"] is not None and not isinstance(obj["crm"], dict)):
        raise ValueError("crm must be an object or null")

    def check_event(event, fact=False):
        if not isinstance(event, dict):
            raise ValueError("event must be an object")
        day = valid_date(event.get("date"))
        if day > as_of or (start is not None and not valid_date(start) <= day <= valid_date(end)):
            raise ValueError("fact/event outside accepted window")
        source_url(event.get("source_url"))
        if not event.get("fact" if fact else "description"):
            raise ValueError("event needs supported text")

    for ev in obj["recent_events"]:
        check_event(ev)
    for point in obj["talking_points"]:
        if not isinstance(point, dict) or not point.get("fact") or not isinstance(point["fact"], list):
            raise ValueError("talking point requires dated fact evidence")
        for fact in point["fact"]:
            check_event(fact, True)
        if not point.get("implication") or not point.get("say"):
            raise ValueError("talking point requires separate implication and suggested wording")
        if scope["seller_mode"] == "tailored" and not point.get("seller_offering"):
            raise ValueError("tailored talking point requires confirmed offering")
    if obj.get("since_last_meeting"):
        crm = obj.get("crm") or {}
        prior = valid_date((crm.get("last_meeting") or {}).get("date"))
        for ev in obj["since_last_meeting"]:
            check_event(ev)
            if valid_date(ev["date"]) <= prior:
                raise ValueError("since-last-meeting event must follow known meeting")

    def visit(value, key=""):
        if isinstance(value, dict):
            for field, child in value.items():
                if field.lower() in ("email", "email_address", "phone", "phone_number"):
                    raise ValueError("contact email/phone fields are not part of the brief")
                visit(child, field)
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError("nonfinite numeric value")
        elif value is not None and key.endswith("_usd"):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise ValueError("USD values must be nonnegative numbers or null")
    visit(obj)
    return {"valid": True, "schema_version": obj["schema_version"], "as_of": obj["as_of"], "company_uuid": company["uuid"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=Path)
    args = parser.parse_args()
    try:
        result = validate_brief(json.loads(args.brief.read_text()))
    except (OSError, ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
