#!/usr/bin/env python3
"""Account Pulse helper: read a rep's book, rank accounts by fresh signals,
group plays, build the predicted-raise feed, and decide same-day alerts.

Standard library only. Deterministic: same inputs, same output.

Subcommands
-----------
book   <file> [--out book.json]
    Read a CSV / TSV / TXT account list. Detects name, domain / website,
    Crunchbase URL or permalink, and tier columns. Prints JSON.

match  --book book.json --orgs FILE [FILE ...] [--out accounts.json]
    Match Crunchbase organization search results (raw cb_search_query
    responses) to book rows by permalink, then domain, never by name alone.
    Prints matched accounts and unmatched rows.

rank   --accounts accounts.json --data FILE [FILE ...] [options]
    Score and rank accounts. --data takes raw cb_search_query responses
    (any of funding_rounds, key_employee_changes, product_launches,
    addresses, partnership_announcements, layoffs, funding_predictions,
    people) or compact JSONL records (see references/data-recipe.md).
    Options:
      --today YYYY-MM-DD        required: accepted as-of date
      --lookback DAYS           default 90
      --signals LIST            comma list of funding,leadership,office,
                                launch,prediction,partnership (default:
                                funding,leadership,office,launch,prediction)
      --top N                   size of the call list (default 10)
      --plays-window DAYS       default 60
      --plays-scope SCOPE       all | tier:A | tier:A,B (default: tier:A when
                                tiers exist, else all)
      --alert-scope SCOPE       same syntax (default: tier:A when tiers
                                exist, else all)
      --focus WORDS             comma list of keywords from "what we sell"
      --buyer-titles WORDS      comma list of title words for the buyer
      --coverage FILE          pulse-coverage/v1 retrieval manifest (required)
      --state FILE              state file for daily mode (read, and
                                written back with --write-state)
      --since YYYY-MM-DD        alert window start when there is no state
                                file (scheduled runs without a working
                                folder): events recorded and predictions
                                made on or after this date count as new.
                                Default without state: yesterday
      --write-state             update the state file after this run
      --feed-dir DIR            write predicted-raise feed CSV + JSON there
      --feed-all                feed includes accounts already predicted
                                (default: newly predicted only)
      --list-csv FILE           also write the ranked list as CSV
    Prints one JSON object: ranked, plays, raise_feed, alerts, needs, stats.

The scoring formula is documented in references/scoring.md and in
score_account() below; keep them in step.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import hashlib
import math
import os
import tempfile
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

CB = "https://www.crunchbase.com"

# ---------------------------------------------------------------- weights
TYPE_WEIGHT = {
    "funding": 40,
    "leadership": 30,
    "prediction_new": 25,
    "prediction_ongoing": 10,
    "office": 20,
    "launch": 15,
    "partnership": 10,
    "acquisition_new": 20,   # newly predicted to be acquired (Crunchbase acquisition prediction)
    "growth": 15,            # Crunchbase growth insight: customer, headcount or market growth
}
LAYOFF_PENALTY = 15
HALF_LIFE_DAYS = 30.0
EXTRA_EVENT_POINTS = 3      # per extra event of the same type
EXTRA_EVENT_CAP = 9
TIER_BONUS = {"A": 10, "B": 5}
FOCUS_BONUS = 8
ALERT_MAX_EVENT_AGE = 14    # days: older backfilled events are not "news"

DEFAULT_SIGNALS = ["funding", "leadership", "office", "launch", "prediction", "acquisition", "growth"]
ALL_SIGNALS = DEFAULT_SIGNALS + ["partnership"]

TIER_LABEL = {
    "p100_positive_high": "Very Likely",
    "p200_positive_low": "Probable",
    "p300_neutral": "Uncertain",
    "p400_negative_low": "Doubtful",
    "p500_negative_high": "Very Unlikely",
}
POSITIVE_TIERS = {"p100_positive_high", "p200_positive_low"}
# growth-insight indicators worth a call (funding and M&A have their own signals)
GROWTH_KINDS = {"customers": "customer growth", "headcount": "headcount growth",
                "operations": "operations expansion", "market_share": "market-share gains",
                "engagement": "product usage growth", "finance": "financial growth"}
WINDOWS = [("months_00_to_05", "0-5 months"), ("months_06_to_11", "6-11 months"),
           ("months_12_to_24", "12-24 months"), ("months_24_plus", "24+ months")]

NOT_NEW_MONEY = {"secondary_market", "post_ipo_secondary", "non_equity_assistance", "fund_start"}
EARLY_ROUNDS = {"pre_seed", "seed", "angel", "series_a"}
GROWTH_ROUNDS = {"series_b", "series_c"}
LATE_ROUNDS = {"series_d", "series_e", "series_f", "series_g", "series_h",
               "series_i", "series_j", "private_equity", "corporate_round"}
DEBT_ROUNDS = {"debt_financing", "convertible_note"}

ROUND_NAME = {
    "pre_seed": "Pre-Seed", "seed": "Seed", "angel": "Angel",
    "series_a": "Series A", "series_b": "Series B", "series_c": "Series C",
    "series_d": "Series D", "series_e": "Series E", "series_f": "Series F",
    "series_g": "Series G", "series_h": "Series H", "series_unknown": "Venture round",
    "private_equity": "Private equity round", "debt_financing": "Debt financing",
    "convertible_note": "Convertible note", "grant": "Grant",
    "corporate_round": "Corporate round", "post_ipo_equity": "Post-IPO equity",
    "post_ipo_debt": "Post-IPO debt", "post_ipo_secondary": "Post-IPO secondary",
    "undisclosed": "Funding round", "equity_crowdfunding": "Equity crowdfunding",
    "product_crowdfunding": "Product crowdfunding", "initial_coin_offering": "ICO",
    "non_equity_assistance": "Non-equity assistance", "secondary_market": "Secondary sale",
    "fund_close": "New fund",
}

C_LEVEL = re.compile(r"\b(chief|ceo|cfo|coo|cto|cro|cmo|cpo|ciso|cio|cco|cdo|president|founder|co-founder|general counsel)\b", re.I)
VP_LEVEL = re.compile(r"\b(evp|svp|vp|vice president|head of|managing director|general manager|gm)\b", re.I)
DEPARTURE = re.compile(r"\b(depart|departure|step(?:s|ped)? down|resign|leav(?:e|es|ing)|left|exit(?:s|ed)?|retire)", re.I)
BAD_TITLE = re.compile(r"\b(editor|ambassador|former|ex-|advisor|adviser|intern|assistant|board member|investor)\b", re.I)

FUNCTION_WORDS = [
    ("finance", r"\b(cfo|chief financial|finance|financial officer|treasurer|controller|accounting)\b"),
    ("risk and compliance", r"\b(compliance|risk|fraud|security|ciso|trust|legal|counsel|aml|kyc)\b"),
    ("revenue", r"\b(cro|chief revenue|revenue|sales|commercial|business development|partnerships)\b"),
    ("marketing", r"\b(cmo|chief marketing|marketing|brand|growth)\b"),
    ("product and technology", r"\b(cpo|cto|chief product|chief technology|product|engineering|technology|ai|data|platform)\b"),
    ("operations", r"\b(coo|chief operating|operations)\b"),
    ("people", r"\b(chro|people|human resources|talent)\b"),
    ("chief executive", r"\b(ceo|chief executive)\b"),
]

# Default contact roles per signal when no buyer titles are given.
ROLE_PREFS = {
    "funding": ["cfo", "chief financial", "ceo", "chief executive", "coo", "founder", "president"],
    "prediction": ["cfo", "chief financial", "ceo", "chief executive", "founder", "president"],
    "acquisition": ["ceo", "chief executive", "cfo", "chief financial", "coo", "founder", "president"],
    "growth": ["coo", "chief operating", "ceo", "chief executive", "cro", "chief revenue", "founder"],
    "launch": ["cpo", "chief product", "cto", "chief technology", "head of product", "vp product", "ceo"],
    "office": ["coo", "chief operating", "general manager", "country manager", "managing director", "ceo"],
    "partnership": ["chief business", "partnerships", "cro", "chief revenue", "ceo"],
    "leadership": ["ceo", "chief executive", "coo", "president"],
    "momentum": ["ceo", "chief executive", "coo", "cfo", "founder", "president"],
}

PLAY_THEMES = {
    "funding": "New money usually comes with a plan to scale; lead with how you help them spend it well.",
    "leadership": "New leaders review their stack and vendors in their first 90 days; offer a quick win for the new remit.",
    "launch": "A new product brings new workflows and new risks; lead with what changes for them at launch.",
    "office": "A new office means new teams, markets and processes to set up; offer to make the expansion smoother.",
    "prediction": "Crunchbase predicts a possible raise; ask whether financing plans are relevant before proposing a use case.",
    "partnership": "New partnerships open new channels and integrations; lead with what the partnership needs to work.",
    "acquisition": "A company that may be acquired is reviewed by its buyer; make sure your value is documented and more than one leader owns it.",
    "growth": "More customers or a bigger team strains the tools that worked at the old size; offer to take one bottleneck off their plate.",
}


# ---------------------------------------------------------------- helpers
def norm_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\b(inc|incorporated|llc|ltd|limited|corp|corporation|co|company|gmbh|plc|sa|ag|bv|the)\b", " ", text)
    return " ".join(text.split())


def norm_domain(value: str) -> str:
    if not value:
        return ""
    value = value.strip().lower()
    if "@" in value and "/" not in value:
        value = value.split("@", 1)[1]
    if "://" not in value:
        value = "http://" + value
    host = urlparse(value).hostname or ""
    return host[4:] if host.startswith("www.") else host


def url_path(value: str) -> str:
    if not value:
        return ""
    if "://" not in value:
        value = "http://" + value
    return (urlparse(value).path or "").strip("/")


def parse_day(value) -> date | None:
    if not value:
        return None
    if isinstance(value, dict):
        value = value.get("value")
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def ident(value) -> dict:
    """Return identifier dict {permalink, value, uuid} from a property."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return {"permalink": value, "value": value}
    return {}


def link_of(value):
    if isinstance(value, dict):
        return value.get("value"), value.get("label")
    if isinstance(value, str):
        return value, None
    return None, None


def fmt_day(d: date) -> str:
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def fmt_money(usd) -> str:
    if not usd:
        return ""
    usd = float(usd)
    if usd >= 1e9:
        return f"${usd / 1e9:.1f}B".replace(".0B", "B")
    if usd >= 1e6:
        return f"${usd / 1e6:.0f}M"
    if usd >= 1e3:
        return f"${usd / 1e3:.0f}K"
    return f"${usd:.0f}"


def load_json_any(path: Path):
    raw = path.read_text(encoding="utf-8-sig")
    raw_stripped = raw.strip()
    if not raw_stripped:
        return []
    try:
        return json.loads(raw_stripped)
    except json.JSONDecodeError:
        rows = []
        for line in raw.splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows


def properties_of(entity: dict) -> dict:
    """Normalize live nested properties, replay projections and entity-get arrays."""
    if not isinstance(entity, dict):
        raise ValueError("entity must be an object")
    props = entity.get("properties", entity)
    if isinstance(props, dict):
        return props
    if isinstance(props, list):
        values = {}
        for field in props:
            if not isinstance(field, dict) or not isinstance(field.get("field_id"), str) or "value" not in field:
                raise ValueError("invalid property array entry")
            key, value = field["field_id"], field["value"]
            if key in values and values[key] != value:
                raise ValueError("conflicting duplicate property field")
            values[key] = value
        return values
    raise ValueError("entity properties must be an object or field/value array")


def iter_payloads(obj):
    """Yield (collection_id, entities) or ('compact', record) items."""
    if isinstance(obj, list):
        for item in obj:
            yield from iter_payloads(item)
        return
    if not isinstance(obj, dict):
        raise ValueError("unsupported tool payload type")
    # Claude Code sometimes wraps tool output as [{"type":"text","text":"{...}"}]
    if obj.get("type") == "text" and isinstance(obj.get("text"), str):
        try:
            yield from iter_payloads(json.loads(obj["text"]))
        except json.JSONDecodeError as exc:
            raise ValueError("unparseable tool text payload") from exc
        return
    if obj.get("isError") or obj.get("error"):
        raise ValueError("tool error payload is not a complete dataset")
    if "structuredContent" in obj:
        yield from iter_payloads(obj["structuredContent"])
        return
    if "content" in obj:
        yield from iter_payloads(obj["content"])
        return
    if "data" in obj and isinstance(obj["data"], dict):
        yield from iter_payloads(obj["data"])
        return
    if "properties" in obj and "collection_id" in obj and "entities" not in obj:
        yield obj["collection_id"], [obj]
        return
    if "entities" in obj and "collection_id" in obj:
        yield obj["collection_id"], obj["entities"]
        return
    if "entities" in obj and isinstance(obj["entities"], list):
        yield obj.get("collection_id", "unknown"), obj["entities"]
        return
    if "kind" in obj or "type" in obj:
        yield "compact", obj
        return
    raise ValueError("unsupported tool response envelope")


# ---------------------------------------------------------------- book
NAME_COLS = ["company", "company name", "account", "account name", "organization", "organization name", "org", "name"]
DOMAIN_COLS = ["domain", "website", "website url", "url", "company domain", "company website", "web"]
CB_COLS = ["crunchbase", "crunchbase url", "cb url", "crunchbase link", "permalink", "cb permalink"]
TIER_COLS = ["tier", "account tier", "priority", "abm tier", "tier (a/b/c)"]


def pick_col(headers, options):
    lowered = {h.strip().lower(): h for h in headers if h}
    for option in options:
        if option in lowered:
            return lowered[option]
    for option in options:
        for low, original in lowered.items():
            if option in low:
                return original
    return None


def cb_permalink(value: str) -> str:
    if not value:
        return ""
    m = re.search(r"crunchbase\.com/organization/([^/?#\s]+)", value)
    if m:
        return m.group(1)
    if re.fullmatch(r"[a-z0-9][a-z0-9\-]*", value.strip()):
        return value.strip()
    return ""


def read_book(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    rows = []
    sample = text[:4096]
    looks_tabular = ("," in sample or "\t" in sample) and len(text.splitlines()) > 1
    if looks_tabular:
        dialect = "excel-tab" if sample.count("\t") > sample.count(",") else "excel"
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        headers = reader.fieldnames or []
        name_c, dom_c = pick_col(headers, NAME_COLS), pick_col(headers, DOMAIN_COLS)
        cb_c, tier_c = pick_col(headers, CB_COLS), pick_col(headers, TIER_COLS)
        if dom_c and dom_c == cb_c:
            cb_c = None
        for i, rec in enumerate(reader, start=2):
            name = (rec.get(name_c) or "").strip() if name_c else ""
            dom_raw = (rec.get(dom_c) or "").strip() if dom_c else ""
            cb_raw = (rec.get(cb_c) or "").strip() if cb_c else ""
            permalink = cb_permalink(cb_raw) or (cb_permalink(dom_raw) if "crunchbase.com" in dom_raw else "")
            domain = "" if "crunchbase.com" in dom_raw else norm_domain(dom_raw)
            tier = (rec.get(tier_c) or "").strip().upper()[:1] if tier_c else ""
            if not (name or domain or permalink):
                continue
            rows.append({"row": i, "name": name, "domain": domain, "permalink": permalink,
                         "tier": tier if tier in {"A", "B", "C"} else ""})
        columns = {"name": name_c, "domain": dom_c, "crunchbase": cb_c, "tier": tier_c}
    else:
        for i, line in enumerate(text.splitlines(), start=1):
            item = line.strip().strip(",;")
            if not item or item.startswith("#"):
                continue
            permalink = cb_permalink(item) if "crunchbase.com" in item else ""
            domain = norm_domain(item) if (not permalink and re.search(r"\.[a-z]{2,}(/|$)", item.lower()) and " " not in item) else ""
            rows.append({"row": i, "name": "" if (domain or permalink) else item, "domain": domain,
                         "permalink": permalink, "tier": ""})
        columns = {"name": "one per line"}
    seen, unique = set(), []
    for r in rows:
        key = r["permalink"] or r["domain"] or norm_name(r["name"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    tiers = {}
    for r in unique:
        if r["tier"]:
            tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
    return {
        "rows": unique,
        "columns": columns,
        "counts": {
            "rows": len(unique),
            "with_permalink": sum(1 for r in unique if r["permalink"]),
            "with_domain": sum(1 for r in unique if r["domain"] and not r["permalink"]),
            "name_only": sum(1 for r in unique if not r["domain"] and not r["permalink"]),
            "tiers": tiers,
        },
        "domains": sorted({r["domain"] for r in unique if r["domain"] and not r["permalink"]}),
        "permalinks": [r["permalink"] for r in unique if r["permalink"]],
        "names_to_resolve": [r["name"] for r in unique if not r["domain"] and not r["permalink"]],
    }


# ---------------------------------------------------------------- orgs / match
ORG_FIELDS = ["website_url", "num_employees_enum", "last_funding_at", "last_funding_type",
              "funding_prediction_tier", "growth_prediction_tier", "heat_score",
              "heat_score_delta_d90", "growth_score", "ipo_status", "short_description",
              "operating_status", "rank_org_company", "funding_total"]


def org_from_entity(entity: dict) -> dict | None:
    props = properties_of(entity)
    idf = ident(props.get("identifier"))
    permalink = idf.get("permalink")
    if not permalink:
        return None
    org = {
        "permalink": permalink,
        "name": idf.get("value") or entity.get("value") or permalink,
        "uuid": idf.get("uuid") or entity.get("uuid"),
        "url": entity.get("url") or f"{CB}/organization/{permalink}",
        "control_tags": idf.get("control_tags") or [],
    }
    for field in ORG_FIELDS:
        if field in props:
            org[field] = props[field]
    if isinstance(org.get("funding_total"), dict):
        org["funding_total"] = org["funding_total"].get("value_usd")
    return org


def collect_orgs(paths) -> list[dict]:
    orgs = []
    for p in paths:
        for coll, payload in iter_payloads(load_json_any(Path(p))):
            if coll == "organizations":
                for e in payload:
                    o = org_from_entity(e)
                    if o:
                        orgs.append(o)
            elif coll == "compact" and payload.get("kind") == "org":
                o = dict(payload)
                o.setdefault("url", f"{CB}/organization/{o['permalink']}")
                orgs.append(o)
            elif coll == "accounts":
                pass
    return orgs


def org_quality(o: dict) -> tuple:
    has_data = sum(1 for f in ("last_funding_at", "funding_prediction_tier", "growth_score", "num_employees_enum") if o.get(f))
    rank = o.get("rank_org_company") or 10**9
    return (-has_data, rank, o["permalink"])


def match_book(book: dict, orgs: list[dict]) -> dict:
    """Reconcile canonical evidence; names alone never establish identity."""
    by_perm, by_domain = {}, {}
    for o in orgs:
        if not o.get("uuid") or not o.get("permalink") or o.get("control_tags"):
            continue
        by_perm.setdefault(o["permalink"], {})[o["uuid"]] = o
        domain = norm_domain(o.get("website_url") or "")
        if domain:
            by_domain.setdefault(domain, {})[o["uuid"]] = o
    accounts, unmatched, ambiguous, used = [], [], [], set()
    for row in book["rows"]:
        if row.get("permalink"):
            cands, how = list(by_perm.get(row["permalink"], {}).values()), "canonical"
        elif row.get("domain"):
            cands, how = list(by_domain.get(row["domain"], {}).values()), "exact_domain"
        else:
            cands, how = [], "unresolved_name"
        if len(cands) != 1:
            item = dict(row)
            if len(cands) > 1:
                item["candidates"] = [{"uuid": o["uuid"], "permalink": o["permalink"], "name": o["name"], "url": o.get("url")} for o in cands]
                ambiguous.append(item)
            else:
                unmatched.append(item)
            continue
        chosen = cands[0]
        if chosen["uuid"] in used:
            continue
        used.add(chosen["uuid"])
        accounts.append(dict(chosen, tier=row.get("tier", ""), book_name=row.get("name", ""), matched_by=how))
    return {"schema_version": "pulse-accounts/v1", "accounts": accounts, "unmatched": unmatched,
            "ambiguous": ambiguous, "permalinks": [a["permalink"] for a in accounts],
            "coverage": {"requested": len(book["rows"]), "confirmed": len(accounts),
                         "unresolved": len(unmatched), "ambiguous": len(ambiguous)}}


# ---------------------------------------------------------------- events
def leadership_strength(desc: str) -> float:
    if C_LEVEL.search(desc or ""):
        base = 1.0
    elif VP_LEVEL.search(desc or ""):
        base = 0.8
    else:
        base = 0.5
    return base


def function_of(text: str) -> str:
    for label, pattern in FUNCTION_WORDS:
        if re.search(pattern, text or "", re.I):
            return label
    return "leadership"


def funding_strength(kind: str) -> float:
    if kind in DEBT_ROUNDS:
        return 0.6
    if kind in {"grant", "non_equity_assistance", "product_crowdfunding", "equity_crowdfunding"}:
        return 0.4
    return 1.0


def funding_bucket(kind: str) -> str:
    if kind == "fund_close":
        return "new fund (investors)"
    if kind in EARLY_ROUNDS:
        return "early-stage round (Seed or Series A)"
    if kind in GROWTH_ROUNDS:
        return "growth round (Series B or C)"
    if kind in LATE_ROUNDS:
        return "late-stage round (Series D or later, or private equity)"
    if kind in DEBT_ROUNDS:
        return "debt financing"
    return "funding round"


def event_from_raw(coll: str, entity: dict, today: date) -> dict | None:
    p = properties_of(entity)
    if entity.get("control_tags") or ident(p.get("identifier")).get("control_tags"):
        return None
    eid = entity.get("uuid") or ident(p.get("identifier")).get("uuid")
    created = parse_day(p.get("created_at"))
    if coll == "funding_rounds":
        org = ident(p.get("funded_organization_identifier"))
        kind = p.get("investment_type") or ""
        money = p.get("money_raised") or {}
        leads = [ident(x).get("value") for x in (p.get("lead_investor_identifiers") or []) if ident(x).get("value")]
        ev = {"type": "funding", "org": org.get("permalink"), "id": eid, "date": parse_day(p.get("announced_on")),
              "created": created, "round": kind, "amount_usd": money.get("value_usd") if isinstance(money, dict) else None,
              "leads": leads, "source": entity.get("url") or (f"{CB}/funding_round/{ident(p.get('identifier')).get('permalink')}" if ident(p.get('identifier')).get('permalink') else None),
              "source_title": "Crunchbase funding round"}
    elif coll in ("key_employee_changes", "layoffs"):
        org = ident(p.get("organization_identifier"))
        src, title = link_of(p.get("press_reference_link"))
        ev = {"type": "leadership" if coll == "key_employee_changes" else "layoff", "org": org.get("permalink"), "id": eid,
              "date": parse_day(p.get("key_event_date")), "created": created, "desc": p.get("description") or "",
              "sentiment": p.get("sentiment"), "source": src, "source_title": title}
    elif coll in ("product_launches", "partnership_announcements"):
        org = ident(p.get("organization"))
        src, title = link_of(p.get("press_reference_link"))
        ev = {"type": "launch" if coll == "product_launches" else "partnership", "org": org.get("permalink"), "id": eid,
              "date": parse_day(p.get("key_event_date")), "created": created, "desc": p.get("description") or "",
              "source": src, "source_title": title}
    elif coll == "addresses":
        org = ident(p.get("organization"))
        src, title = link_of(p.get("opening_press_reference_link"))
        place = ""
        for loc in p.get("location_identifiers") or []:
            if isinstance(loc, dict) and loc.get("location_type") == "city":
                place = loc.get("value", "")
        if not place:
            for loc in p.get("location_identifiers") or []:
                if isinstance(loc, dict) and loc.get("location_type") == "country":
                    place = loc.get("value", "")
        ev = {"type": "office", "org": org.get("permalink"), "id": eid, "date": parse_day(p.get("opening_date")),
              "created": created, "desc": p.get("opening_description") or "", "place": place,
              "source": src, "source_title": title}
    elif coll == "funds":
        # Search started_on is a fund start date, not proof of a closed financing.
        org = ident(p.get("owner_identifier"))
        money = p.get("money_raised") or {}
        fid = ident(p.get("identifier"))
        ev = {"type": "funding", "org": org.get("permalink"), "id": eid, "date": parse_day(p.get("started_on")),
              "created": created, "round": "fund_start", "fund_name": fid.get("value") or "",
              "amount_usd": money.get("value_usd") if isinstance(money, dict) else None, "leads": [],
              "source": entity.get("url") or (f"{CB}/fund_financial/{fid.get('permalink')}" if fid.get("permalink") else None),
              "source_title": "Crunchbase fund"}
    elif coll == "growth_insights":
        ev = growth_from_props(p, eid, today)
        if ev is None:
            return None
    else:
        return None
    return finish_event(ev, today)


def growth_from_props(p: dict, eid, today: date) -> dict | None:
    """A Crunchbase growth insight as an event: only growing ones with a customer, headcount,
    operations, market-share, usage or financial indicator. Dated by its newest press article (the
    insight's own date is when Crunchbase generated it, often months after the news)."""
    org = ident(p.get("organization")).get("permalink")
    if (p.get("indicator") or "growing") != "growing":
        return None
    kinds = [k for k in (p.get("growth_indicators") or []) if k in GROWTH_KINDS]
    if not org or not kinds:
        return None
    best = None
    for ref in p.get("press_references") or []:
        if not isinstance(ref, dict):
            continue
        d = parse_day(ref.get("posted_on"))
        if d and d <= today and (best is None or d > best[0]):
            best = (d, ref.get("source_url") or ref.get("url"), ref.get("value") or ref.get("title"))
    gen = parse_day(p.get("generated_on"))
    if best is None or not best[1]:
        return None
    words = [GROWTH_KINDS[k] for k in sorted(kinds, key=list(GROWTH_KINDS).index)]
    return {"type": "growth", "org": org, "id": eid, "date": best[0] if best else gen, "created": gen,
            "kinds": kinds, "desc": "Crunchbase growth insight: " + " and ".join(words[:2]),
            "source": best[1] if best else None, "source_title": best[2] if best else None}


def event_from_compact(rec: dict, today: date) -> dict | None:
    kind = rec.get("kind") or rec.get("type")
    if kind == "fund":
        rec = dict(rec, kind="funding", round="fund_close")
        kind = "funding"
    if kind == "growth":
        p = {"organization": {"permalink": rec.get("org")}, "growth_indicators": rec.get("kinds") or [],
             "generated_on": rec.get("created") or rec.get("date"),
             "press_references": [{"posted_on": rec.get("date"), "source_url": rec.get("source"),
                                   "value": rec.get("source_title")}] if rec.get("date") else []}
        ev = growth_from_props(p, rec.get("id"), today)
        return finish_event(ev, today) if ev else None
    if kind not in ("funding", "leadership", "launch", "office", "partnership", "layoff"):
        return None
    ev = dict(rec)
    ev["type"] = kind
    ev["date"] = parse_day(rec.get("date"))
    ev["created"] = parse_day(rec.get("created"))
    ev.setdefault("desc", "")
    return finish_event(ev, today)


def finish_event(ev: dict, today: date) -> dict | None:
    if ev.get("control_tags") or not ev.get("org") or not ev.get("date"):
        return None
    if ev["date"] > today or not ev.get("source"):
        return None
    if not isinstance(ev["source"], str) or not ev["source"].startswith(("https://", "http://")):
        return None
    ev["future_dated"] = False
    # Record creation is observation metadata, never a replacement event date.
    if ev.get("created") and ev["created"] > today:
        return None
    if ev.get("amount_usd") is not None and not finite_number(ev["amount_usd"], minimum=0):
        return None
    if not ev.get("id"):
        basis = [ev["org"], ev["type"], ev["date"].isoformat(), ev.get("source"), ev.get("desc", "")]
        ev["id"] = "derived:" + hashlib.sha256(json.dumps(basis, sort_keys=True).encode()).hexdigest()
    if ev["type"] == "funding":
        ev["new_money"] = ev.get("round") not in NOT_NEW_MONEY
    if ev["type"] == "leadership":
        ev["departure"] = bool(DEPARTURE.search(ev.get("desc", ""))) or ev.get("sentiment") == "c300_negative"
        ev["function"] = function_of(ev.get("desc", ""))
    return ev


# ---------------------------------------------------------------- predictions
def prediction_from_raw(entity: dict) -> dict | None:
    p = properties_of(entity)
    if entity.get("control_tags") or ident(p.get("identifier")).get("control_tags"):
        raise ValueError("restricted prediction cannot enter the artifact")
    org = ident(p.get("organization")).get("permalink")
    gen = parse_day(p.get("generated_on"))
    if not org or not gen:
        raise ValueError("prediction requires organization and valid generated_on")
    ts = p.get("probability_score_timeseries") or {}
    return {
        "org": org, "id": entity.get("uuid"), "generated_on": gen, "tier": p.get("probability_tier"),
        "score": p.get("probability_score"), "ts": ts,
        "reasons": (p.get("financials_reasons") or []) + (p.get("misc_reasons") or []),
        "trajectory": p.get("organization_trajectory"),
    }


def prediction_from_compact(rec: dict) -> dict | None:
    if rec.get("control_tags"):
        raise ValueError("restricted prediction cannot enter the artifact")
    gen = parse_day(rec.get("generated_on"))
    if not rec.get("org") or not gen:
        raise ValueError("prediction requires organization and valid generated_on")
    ts = rec.get("ts") or {k: rec.get(k) for k, _ in WINDOWS if rec.get(k) is not None}
    return {"org": rec["org"], "id": rec.get("id"), "generated_on": gen, "tier": rec.get("tier"),
            "score": rec.get("score"), "ts": ts, "reasons": rec.get("reasons") or [],
            "trajectory": rec.get("trajectory")}


def best_window(ts: dict):
    best, label, prob = None, None, -1.0
    for key, lab in WINDOWS:
        v = ts.get(key)
        if finite_number(v, minimum=0, maximum=1) and v > prob:
            best, label, prob = key, lab, float(v)
    return best, label, prob


def is_positive(pred: dict | None) -> bool:
    if not pred:
        return False
    key, _, _ = best_window(pred.get("ts") or {})
    return pred.get("tier") in POSITIVE_TIERS and key == "months_00_to_05"


def turned_positive(latest: dict | None, previous: dict | None) -> bool:
    """Newly predicted: positive now, and an earlier prediction in the data was not.
    With no earlier prediction to compare, it is not called new."""
    return is_positive(latest) and previous is not None and not is_positive(previous)


def summarize_predictions(preds: list[dict]) -> dict:
    """Latest and previous distinct prediction per org."""
    by_org: dict[str, dict] = {}
    for pr in preds:
        by_org.setdefault(pr["org"], {})
        slot = by_org[pr["org"]]
        cur = slot.get(pr["generated_on"])
        # Conservative and deterministic for contradictory same-day observations.
        def selection(row):
            tier_rank = TIER_ORDER.index(row["tier"]) if row.get("tier") in TIER_ORDER else 99
            return (not is_positive(row), tier_rank, len(row.get("reasons") or []), json.dumps(row, sort_keys=True, default=str))
        if cur is None or selection(pr) > selection(cur):
            slot[pr["generated_on"]] = pr
    out = {}
    for org, rows in by_org.items():
        days = sorted(rows, reverse=True)
        latest = rows[days[0]]
        prev = rows[days[1]] if len(days) > 1 else None
        out[org] = {"latest": latest, "previous": prev}
    return out


def window_rank(key):
    order = [k for k, _ in WINDOWS]
    return order.index(key) if key in order else 99


# ---------------------------------------------------------------- people
def people_from_raw(entity: dict) -> dict | None:
    p = properties_of(entity)
    idf = ident(p.get("identifier"))
    if idf.get("control_tags"):
        return None
    org = ident(p.get("primary_organization")).get("permalink")
    if not org or not idf.get("value"):
        return None
    li, _ = link_of(p.get("linkedin"))
    return {"org": org, "name": idf.get("value"), "permalink": idf.get("permalink"),
            "url": entity.get("url") or (f"{CB}/person/{idf.get('permalink')}" if idf.get("permalink") else None),
            "title": p.get("primary_job_title") or "", "linkedin": li}


HIRE_NAME = re.compile(
    r"(?:appointed|hired|named|promoted|welcomed|added|tapped|elevated|brought on)\s+"
    r"(?:former\s+[\w\- ]+?\s+)?([A-Z][a-zA-Z'\-]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-zA-Z'\-]+){1,2})")
HIRE_NAME_FIRST = re.compile(r"^([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){1,2})\s+(?:joined|joins|has joined|was appointed|was named|became)")
HIRE_TITLE = re.compile(r"\bas\s+(?:its\s+|the\s+|their\s+)?(?:new\s+|next\s+|first\s+)?([A-Z][^,.;]*?)(?:,|\.|;| to | effective| subject|$)")

HIRE_TO_TITLE = re.compile(r"\bto\s+((?:Chief|Head|VP|Vice President|SVP|EVP|President|General Counsel|Managing Director)[^,.;]*?)(?:,|\.|;| to |$)")


def hire_from_text(desc: str):
    """Best-effort name and title of a new leader from an announcement line."""
    name = None
    m = HIRE_NAME.search(desc or "") or HIRE_NAME_FIRST.search(desc or "")
    if m:
        name = m.group(1).strip()
    title = None
    t = HIRE_TITLE.search(desc or "")
    if t:
        title = t.group(1).strip()
    else:
        t = HIRE_TO_TITLE.search(desc or "")
        if t:
            title = t.group(1).strip()
    return name, title


def seniority(title: str) -> int:
    if C_LEVEL.search(title):
        return 0
    if re.search(r"\b(evp|svp)\b", title, re.I):
        return 1
    if VP_LEVEL.search(title):
        return 2
    return 3


def pick_contact(acct: dict, people: list[dict], main_signal: str, main_event: dict | None,
                 buyer_titles: list[str]) -> dict | None:
    # A new leader named in the announcement is the natural contact.
    if main_event and main_event.get("type") == "leadership" and not main_event.get("departure"):
        desc = main_event.get("desc", "")
        for person in people:
            if person["name"] and person["name"].lower() in desc.lower():
                return dict(person, why="new in the role", source="crunchbase")
        name, title = hire_from_text(desc)
        return {"name": name, "title": title, "url": main_event.get("source"), "why": "new in the role",
                "source": "announcement", "from_text": desc}
    usable = [p for p in people if p.get("title") and not BAD_TITLE.search(p["title"])]
    if not usable:
        return None
    if buyer_titles:
        hits = [p for p in usable if any(re.search(r"\b" + re.escape(w) + r"\b", p["title"], re.I) for w in buyer_titles)]
        if hits:
            hits.sort(key=lambda p: (seniority(p["title"]), p["name"]))
            return dict(hits[0], why="matches your buyer", source="crunchbase")
    prefs = ROLE_PREFS.get(main_signal, ROLE_PREFS["momentum"])
    for want in prefs:
        hits = [p for p in usable if re.search(r"\b" + re.escape(want) + r"\b", p["title"], re.I)]
        if hits:
            hits.sort(key=lambda p: (seniority(p["title"]), p["name"]))
            return dict(hits[0], why=f"usual owner after a {main_signal} signal", source="crunchbase")
    usable.sort(key=lambda p: (seniority(p["title"]), p["name"]))
    if seniority(usable[0]["title"]) <= 2:
        return dict(usable[0], why="most senior listed", source="crunchbase")
    return None


# ---------------------------------------------------------------- scoring
def recency(age_days: int) -> float:
    return 0.5 ** (max(age_days, 0) / HALF_LIFE_DAYS)


def event_points(ev: dict, today: date) -> float:
    t = ev["type"]
    if t == "funding":
        if not ev.get("new_money"):
            return 0.0
        strength = funding_strength(ev.get("round", ""))
    elif t == "leadership":
        strength = leadership_strength(ev.get("desc", "")) * (0.6 if ev.get("departure") else 1.0)
    else:
        strength = 1.0
    return TYPE_WEIGHT[t] * strength * recency((today - ev["date"]).days)


def finite_number(value, minimum=None, maximum=None):
    return (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
            and (minimum is None or value >= minimum) and (maximum is None or value <= maximum))


def momentum_points(acct: dict) -> float | None:
    if not finite_number(acct.get("growth_score"), 0, 100) or not finite_number(acct.get("heat_score_delta_d90"), -100, 100) or acct.get("growth_prediction_tier") not in TIER_LABEL:
        return None
    pts = 0.0
    gs = acct.get("growth_score")
    if isinstance(gs, (int, float)):
        pts += max(0.0, min(10.0, gs / 10.0))
    hd = acct.get("heat_score_delta_d90")
    if isinstance(hd, (int, float)):
        pts += max(-5.0, min(5.0, hd / 4.0))
    gt = acct.get("growth_prediction_tier")
    pts += {"p100_positive_high": 5, "p200_positive_low": 3}.get(gt, 0)
    return pts


TIER_ORDER = ["p100_positive_high", "p200_positive_low", "p300_neutral", "p400_negative_low", "p500_negative_high"]


def acq_history(preds: list[dict]) -> dict:
    """Acquisition predictions per org as [(date, tier, row)], newest first, one per date. Crunchbase
    sometimes stores two different readings on one date; the less likely one is kept."""
    by: dict[str, dict] = {}
    for pr in preds:
        slot = by.setdefault(pr["org"], {})
        cur = slot.get(pr["generated_on"])
        rank = TIER_ORDER.index(pr["tier"]) if pr.get("tier") in TIER_ORDER else 99
        if cur is None or rank > (TIER_ORDER.index(cur["tier"]) if cur.get("tier") in TIER_ORDER else 99):
            slot[pr["generated_on"]] = pr
    return {org: [(d, rows[d].get("tier"), rows[d]) for d in sorted(rows, reverse=True)] for org, rows in by.items()}


def acq_confirmed(hist: list | None) -> bool:
    """Crunchbase expects an acquisition, and has for two readings in a row: the latest is Very Likely
    and the one before it Very Likely or Probable. Single readings flip too often to act on
    (Very Likely to Very Unlikely and back within weeks in the 2026-10-07 sample)."""
    return bool(hist) and len(hist) >= 2 and hist[0][1] == "p100_positive_high" and hist[1][1] in POSITIVE_TIERS


def acq_newly(hist: list | None, prev_state: dict | None) -> bool:
    """Newly predicted to be acquired: confirmed now, and not before (state snapshot first, else the
    reading before the confirming pair). Without an earlier reading it is not called new."""
    if not acq_confirmed(hist):
        return False
    if prev_state is not None:
        return not prev_state.get("confirmed")
    return len(hist) >= 3 and hist[2][1] not in POSITIVE_TIERS


def score_account(acct, events, pred_info, today, signals, focus, last_new_money, acq_info=None, acq_prev_state=None):
    """Score = signal points + momentum points + tier bonus + focus bonus - layoffs.

    signal points: for each signal type, the best event's
        TYPE_WEIGHT[type] x strength x 0.5 ** (age_days / 30)
      plus 3 points per additional event of that type (max 9).
    prediction: +25 when newly predicted to raise within 0-5 months
      (latest prediction Very Likely/Probable with 0-5 months the most
      likely window, previous one not), +10 when it was already predicted.
      Skipped when the prediction predates a new-money round.
    momentum (-5..20): growth score / 10 (0-10) + 90-day heat change / 4
      (-5..+5) + growth prediction Very Likely 5 / Probable 3.
    tier bonus: A +10, B +5.  focus bonus: +8 if an event in the window
      mentions a "what we sell" keyword.  layoffs: -15 x recency.
    """
    by_type: dict[str, list] = {}
    for ev in events:
        by_type.setdefault(ev["type"], []).append(ev)
    signal_pts, best = 0.0, []
    for t, evs in by_type.items():
        if t == "layoff":
            continue
        scored = sorted(((event_points(e, today), e) for e in evs), key=lambda x: (-x[0], -x[1]["date"].toordinal(), str(x[1].get("id", ""))))
        scored = [s for s in scored if s[0] > 0]
        if not scored:
            continue
        top_pts, top_ev = scored[0]
        extra = min(EXTRA_EVENT_CAP, EXTRA_EVENT_POINTS * (len(scored) - 1))
        signal_pts += top_pts + extra
        best.append((top_pts + extra, top_ev))
    pred_state = None
    if "prediction" in signals and pred_info:
        latest, prev = pred_info["latest"], pred_info["previous"]
        stale = bool(last_new_money and latest["generated_on"] < last_new_money)
        if is_positive(latest) and not stale:
            newly = turned_positive(latest, prev)
            age = (today - latest["generated_on"]).days
            pts = TYPE_WEIGHT["prediction_new"] * recency(age) if newly else TYPE_WEIGHT["prediction_ongoing"]
            signal_pts += pts
            pred_state = {"newly": newly, "points": pts}
            best.append((pts, {"type": "prediction", "date": latest["generated_on"], "newly": newly}))
    if "acquisition" in signals and acq_newly(acq_info, acq_prev_state):
        day = acq_info[0][0]  # date the newest Very Likely reading confirms the transition
        pts = TYPE_WEIGHT["acquisition_new"] * recency((today - acq_info[0][0]).days)
        signal_pts += pts
        best.append((pts, {"type": "acquisition", "date": day, "newly": True}))
    layoff_pen = sum(LAYOFF_PENALTY * recency((today - e["date"]).days) for e in by_type.get("layoff", []))
    mom = momentum_points(acct)
    tier_b = TIER_BONUS.get(acct.get("tier") or "", 0)
    focus_b = 0
    if focus:
        text = " ".join(e.get("desc", "") for e in events).lower()
        if any(re.search(r"\b" + re.escape(w.lower()) + r"\b", text) for w in focus):
            focus_b = FOCUS_BONUS
    total = signal_pts + mom + tier_b + focus_b - layoff_pen if mom is not None else None
    best.sort(key=lambda x: (-x[0], -x[1]["date"].toordinal(), str(x[1].get("id", ""))))
    return {
        "score": round(total, 1) if total is not None else None,
        "parts": {"signals": round(signal_pts, 1), "momentum": round(mom, 1) if mom is not None else None, "tier": tier_b,
                  "focus": focus_b, "layoffs": round(-layoff_pen, 1)},
        "best": [b[1] for b in best],
        "prediction": pred_state,
    }


# ---------------------------------------------------------------- text
def describe_event(ev: dict, name: str) -> str:
    t = ev["type"]
    if t == "funding" and ev.get("round") == "fund_close":
        amt = fmt_money(ev["amount_usd"]) if ev.get("amount_usd") is not None else ""
        return f"Closed a {amt + ' ' if amt else 'new '}fund" + (f" ({ev['fund_name']})" if ev.get("fund_name") else "")
    if t == "acquisition":
        return "Newly predicted to be acquired"
    if t == "funding":
        bits = [ROUND_NAME.get(ev.get("round", ""), "Funding round")]
        if ev.get("amount_usd") is not None:
            bits.insert(0, fmt_money(ev["amount_usd"]))
        text = " ".join(bits)
        if ev.get("leads"):
            text += " led by " + ", ".join(ev["leads"][:2])
        return text
    if t == "prediction":
        return "Newly predicted to raise within 0-5 months" if ev.get("newly") else "Predicted to raise within 0-5 months"
    desc = (ev.get("desc") or "").strip()
    if t == "office" and not desc:
        return f"New office in {ev.get('place')}" if ev.get("place") else "New office"
    return desc


def signal_label(t: str) -> str:
    return {"funding": "Funding", "leadership": "Leadership change", "launch": "Product launch",
            "office": "New office", "partnership": "Partnership", "prediction": "Predicted raise",
            "layoff": "Layoffs", "acquisition": "Predicted acquisition",
            "growth": "Growth insight"}.get(t, t)


# ---------------------------------------------------------------- scope
def parse_scope(scope: str | None, accounts: list[dict]) -> set[str]:
    has_tiers = any(a.get("tier") for a in accounts)
    if not scope:
        scope = "tier:A" if has_tiers else "all"
    scope = scope.strip()
    if scope == "all":
        return {a["permalink"] for a in accounts}
    if scope.startswith("tier:"):
        wanted = {t.strip().upper() for t in scope[5:].split(",") if t.strip()}
        return {a["permalink"] for a in accounts if (a.get("tier") or "") in wanted}
    return {s.strip() for s in scope.split(",") if s.strip()}


# ---------------------------------------------------------------- state
def load_state(path: Path | None) -> dict | None:
    if not path or not path.exists():
        return None
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("schema_version") != "pulse-state/v2":
        raise ValueError("unsupported or corrupt state; use a new explicit baseline path")
    if not parse_day(state.get("last_run")) or not isinstance(state.get("scope_fingerprint"), str):
        raise ValueError("corrupt state metadata")
    for field in ("seen_events", "predictions", "acq_predictions", "last_alerted"):
        if not isinstance(state.get(field), dict):
            raise ValueError("corrupt state " + field)
    if any(parse_day(v) is None for v in state["seen_events"].values()) or any(parse_day(v) is None for v in state["last_alerted"].values()):
        raise ValueError("corrupt state observation dates")
    for field, flag in (("predictions", "positive"), ("acq_predictions", "confirmed")):
        if any(not isinstance(v, dict) or type(v.get(flag)) is not bool or parse_day(v.get("generated_on")) is None for v in state[field].values()):
            raise ValueError("corrupt state prediction history")
    return state


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, indent=2, ensure_ascii=False, default=str, allow_nan=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


SIGNAL_COLLECTIONS = {"funding": "funding_rounds", "leadership": "key_employee_changes",
    "office": "addresses", "launch": "product_launches", "prediction": "funding_predictions",
    "acquisition": "acquisition_predictions", "growth": "growth_insights", "partnership": "partnership_announcements"}
COMPACT_COLLECTIONS = dict(SIGNAL_COLLECTIONS, prediction="funding_predictions", acq_prediction="acquisition_predictions",
    fund="funds", person="people", org="organizations", layoff="layoffs")


def coverage_check(path, today, accounts, signals, observed):
    if not path:
        raise ValueError("a coverage manifest is required; unknown retrieval is not complete")
    cov = load_json_any(Path(path))
    if not isinstance(cov, dict) or cov.get("schema_version") != "pulse-coverage/v1" or cov.get("as_of") != today.isoformat():
        raise ValueError("invalid coverage schema or as-of date")
    ac = cov.get("accounts", {})
    if type(ac.get("requested")) is not int or ac["requested"] < len(accounts) or ac.get("confirmed") != len(accounts):
        raise ValueError("coverage account counts do not match input")
    entries = cov.get("collections")
    if not isinstance(entries, dict):
        raise ValueError("coverage collections must be an object")
    required = {SIGNAL_COLLECTIONS[s] for s in signals} | {"layoffs"}
    if any(a.get("is_investor") for a in accounts) and "funding" in signals:
        required.add("funds")
    issues = []
    for coll in sorted(required | set(entries)):
        entry = entries.get(coll)
        if not isinstance(entry, dict):
            issues.append(coll + ": retrieval not established")
            continue
        got, total = entry.get("retrieved"), entry.get("total")
        if type(got) is not int or got < 0 or (total is not None and (type(total) is not int or total < got)):
            raise ValueError("invalid coverage counts for " + coll)
        if got != len(observed.get(coll, set())):
            raise ValueError("coverage retrieved count differs from unique input records for " + coll)
        if entry.get("complete") is not True or total is None or total != got or entry.get("error"):
            issues.append(coll + ": incomplete retrieval")
    if ac["requested"] != ac["confirmed"]:
        issues.append("unresolved or excluded requested accounts")
    return cov, issues


def new_state(old: dict | None, today: date, events: list[dict], preds: dict, accounts: list[dict], alerts,
              acq: dict | None = None) -> dict:
    seen = dict((old or {}).get("seen_events", {}))
    for ev in events:
        if ev.get("id") and ev["id"] not in seen:
            seen[ev["id"]] = today.isoformat()
    cutoff = (today - timedelta(days=200)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    snap = dict((old or {}).get("predictions", {}))
    for org, info in preds.items():
        lt = info["latest"]
        key, label, prob = best_window(lt.get("ts") or {})
        snap[org] = {"generated_on": lt["generated_on"].isoformat(), "tier": lt.get("tier"),
                     "window": key, "positive": is_positive(lt)}
    acq_snap = dict((old or {}).get("acq_predictions", {}))
    for org, hist in (acq or {}).items():
        acq_snap[org] = {"generated_on": hist[0][0].isoformat(), "tier": hist[0][1],
                         "confirmed": acq_confirmed(hist)}
    alerted = dict((old or {}).get("last_alerted", {}))
    for a in alerts:
        alerted[a["permalink"]] = today.isoformat()
    return {
        "schema_version": "pulse-state/v2",
        "last_run": today.isoformat(),
        "book": sorted(a["permalink"] for a in accounts),
        "seen_events": seen,
        "predictions": snap,
        "acq_predictions": acq_snap,
        "last_alerted": alerted,
    }


# ---------------------------------------------------------------- rank
def run_rank(args) -> dict:
    if not args.today:
        raise ValueError("explicit --today as-of date is required")
    today = date.fromisoformat(args.today)
    if args.since and date.fromisoformat(args.since) > today:
        raise ValueError("since date cannot be after as-of")
    lookback = int(args.lookback)
    if lookback <= 0 or int(args.top) <= 0 or int(args.plays_window) <= 0:
        raise ValueError("lookback, plays window and top must be positive")
    start = today - timedelta(days=lookback - 1)
    signals = [s.strip() for s in (args.signals or ",".join(DEFAULT_SIGNALS)).split(",") if s.strip()]
    bad = [s for s in signals if s not in ALL_SIGNALS]
    if bad:
        raise ValueError(f"unknown signal(s): {', '.join(bad)}")
    focus = [w.strip() for w in (args.focus or "").split(",") if w.strip()]
    buyer = [w.strip() for w in (args.buyer_titles or "").split(",") if w.strip()]

    acc_raw = load_json_any(Path(args.accounts))
    accounts = acc_raw.get("accounts", acc_raw) if isinstance(acc_raw, dict) else acc_raw
    if not isinstance(accounts, list) or any(not isinstance(a, dict) or not all(a.get(k) for k in ("uuid", "permalink", "name", "url")) or a.get("control_tags") for a in accounts):
        raise ValueError("accounts require confirmed uuid, permalink, name and url; restricted rows are not eligible")
    if len({a["uuid"] for a in accounts}) != len(accounts) or len({a["permalink"] for a in accounts}) != len(accounts):
        raise ValueError("duplicate account identity; reconcile before ranking")
    book = {a["permalink"]: a for a in accounts}
    observed, rejected = {}, []

    events, preds_raw, acq_raw, people, extra_orgs = [], [], [], [], []
    for p in args.data or []:
        for coll, payload in iter_payloads(load_json_any(Path(p))):
            actual = COMPACT_COLLECTIONS.get(payload.get("kind") or payload.get("type"), "unknown") if coll == "compact" else coll
            records = [payload] if coll == "compact" else payload
            for record in records:
                props = properties_of(record)
                rid = record.get("uuid") or record.get("id") or ident(props.get("identifier")).get("uuid")
                if not rid:
                    rid = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
                observed.setdefault(actual, set()).add(str(rid))
            if coll == "compact":
                kind = payload.get("kind") or payload.get("type")
                if kind == "prediction":
                    pr = prediction_from_compact(payload)
                    if pr:
                        preds_raw.append(pr)
                elif kind == "acq_prediction":
                    pr = prediction_from_compact(payload)
                    if pr:
                        acq_raw.append(pr)
                elif kind == "person":
                    if not payload.get("control_tags"):
                        people.append(payload)
                elif kind == "org":
                    extra_orgs.append(payload)
                else:
                    ev = event_from_compact(payload, today)
                    if ev:
                        events.append(ev)
                    else:
                        rejected.append({"collection": actual, "reason": "invalid, future, undated or unsourced event"})
            elif coll == "funding_predictions":
                for e in payload:
                    pr = prediction_from_raw(e)
                    if pr:
                        preds_raw.append(pr)
            elif coll == "acquisition_predictions":
                for e in payload:
                    pr = prediction_from_raw(e)
                    if pr:
                        acq_raw.append(pr)
            elif coll == "people":
                for e in payload:
                    pp = people_from_raw(e)
                    if pp:
                        people.append(pp)
            elif coll == "organizations":
                for e in payload:
                    o = org_from_entity(e)
                    if o:
                        extra_orgs.append(o)
            else:
                for e in payload:
                    ev = event_from_raw(coll, e, today)
                    if ev:
                        events.append(ev)
                    else:
                        rejected.append({"collection": actual, "reason": "invalid, future, undated or unsourced event"})

    for o in extra_orgs:  # refresh enrichment for book members
        if o["permalink"] in book:
            for k, v in o.items():
                if k not in ("tier", "book_name") and v not in (None, ""):
                    book[o["permalink"]].setdefault(k, v)

    # de-duplicate events by id, keep book members, apply window and signal filter
    uniq, seen_ids, canonical_events = [], set(), {}
    type_to_signal = {"funding": "funding", "leadership": "leadership", "launch": "launch",
                      "office": "office", "partnership": "partnership", "layoff": "layoff", "growth": "growth"}
    for ev in sorted(events, key=lambda e: json.dumps(e, sort_keys=True, default=str)):
        key = ev.get("id") or (ev["org"], ev["type"], ev["date"].isoformat(), ev.get("desc", "")[:40])
        if key in seen_ids:
            if canonical_events[key] != ev:
                raise ValueError("conflicting duplicate event identity; reconcile source evidence")
            continue
        seen_ids.add(key)
        canonical_events[key] = ev
        if ev["org"] not in book:
            continue
        if ev["date"] < start:
            continue
        sig = type_to_signal.get(ev["type"])
        if sig != "layoff" and sig not in signals:
            continue
        uniq.append(ev)
    events = uniq

    def valid_predictions(items, funding=False):
        good = []
        for pr in items:
            valid = pr["generated_on"] <= today and pr.get("tier") in TIER_LABEL
            valid = valid and (pr.get("score") is None or finite_number(pr["score"], 0, 1))
            valid = valid and all(v is None or finite_number(v, 0, 1) for v in pr.get("ts", {}).values())
            if funding and pr.get("tier") in POSITIVE_TIERS and best_window(pr.get("ts") or {})[0] is None:
                valid = False
            if not valid:
                rejected.append({"collection": "predictions", "reason": "future or invalid prediction"})
            elif pr["org"] in book:
                good.append(pr)
        return good
    preds = summarize_predictions(valid_predictions(preds_raw, funding=True))
    acq = acq_history(valid_predictions(acq_raw))
    coverage, coverage_issues = coverage_check(getattr(args, "coverage", None), today, accounts, signals, observed)
    scope = {"book": sorted(a["uuid"] for a in accounts), "tiers": sorted((a["uuid"], a.get("tier", "")) for a in accounts),
             "signals": sorted(signals), "lookback_days": lookback, "plays_window": int(args.plays_window),
             "plays_scope": sorted(parse_scope(args.plays_scope, accounts)), "alert_scope": sorted(parse_scope(args.alert_scope, accounts)),
             "focus": sorted(focus), "buyer_titles": sorted(buyer), "rubric_version": "pulse/v2", "window_policy": "inclusive-calendar-days/v1"}
    fingerprint = hashlib.sha256(json.dumps(scope, sort_keys=True).encode()).hexdigest()
    state = load_state(Path(args.state)) if args.state else None
    if state and (state["scope_fingerprint"] != fingerprint or date.fromisoformat(state["last_run"]) > today):
        raise ValueError("state scope changed or as-of precedes baseline; use a new explicit baseline path")
    complete = not coverage_issues and not rejected
    if args.write_state and (not args.state or not args.out or not complete):
        raise ValueError("state commit needs --state, --out and complete valid retrieval")
    people_by_org: dict[str, list] = {}
    for pp in people:
        people_by_org.setdefault(pp["org"], []).append(pp)

    # last new-money date per org (from rounds in data and from org profile)
    last_money: dict[str, date] = {}
    for ev in events:
        if ev["type"] == "funding" and ev.get("new_money"):
            last_money[ev["org"]] = max(last_money.get(ev["org"], ev["date"]), ev["date"])
    for perm, a in book.items():
        d = parse_day(a.get("last_funding_at"))
        if d and a.get("last_funding_type") not in NOT_NEW_MONEY and d <= today:
            last_money[perm] = max(last_money.get(perm, d), d)

    ev_by_org: dict[str, list] = {}
    for ev in events:
        ev_by_org.setdefault(ev["org"], []).append(ev)

    rows = []
    for perm, acct in book.items():
        s = score_account(acct, ev_by_org.get(perm, []), preds.get(perm), today, signals, focus, last_money.get(perm),
                          acq_info=acq.get(perm), acq_prev_state=((state or {}).get("acq_predictions") or {}).get(perm))
        has_signal = bool(s["best"])
        main = s["best"][0] if has_signal else None
        main_signal = main["type"] if main else "momentum"
        contact = pick_contact(acct, people_by_org.get(perm, []), main_signal, main, buyer) if (people_by_org.get(perm) or (main and main["type"] == "leadership")) else None
        signals_out = []
        for ev in s["best"]:
            if ev["type"] == "acquisition":
                h = acq[perm]
                item = {"type": "acquisition", "label": signal_label("acquisition"),
                        "date": h[0][0].isoformat(), "date_text": fmt_day(h[0][0]),
                        "text": "Crunchbase now predicts an acquisition (Very Likely since " + fmt_day(h[0][0]) + ")",
                        "newly": True, "likelihood": TIER_LABEL.get(h[0][1]), "source": acct.get("url")}
                if len(h) >= 3:
                    item["previous"] = {"likelihood": TIER_LABEL.get(h[2][1], h[2][1]), "date": h[2][0].isoformat()}
                signals_out.append(item)
                continue
            if ev["type"] == "prediction":
                info = preds[perm]
                lt, pv = info["latest"], info["previous"]
                _, wlabel, wprob = best_window(lt.get("ts") or {})
                item = {"type": "prediction", "label": signal_label("prediction"),
                        "date": lt["generated_on"].isoformat(), "date_text": fmt_day(lt["generated_on"]),
                        "text": describe_event(ev, acct["name"]), "newly": ev.get("newly"),
                        "likelihood": TIER_LABEL.get(lt.get("tier"), lt.get("tier")),
                        "window": wlabel, "source": acct.get("url")}
                if pv:
                    _, pw, _ = best_window(pv.get("ts") or {})
                    item["previous"] = {"likelihood": TIER_LABEL.get(pv.get("tier"), pv.get("tier")), "window": pw,
                                        "date": pv["generated_on"].isoformat()}
                if lt.get("reasons"):
                    item["reasons"] = lt["reasons"][:4]
            else:
                item = {"type": ev["type"], "label": signal_label(ev["type"]), "date": ev["date"].isoformat(),
                        "date_text": fmt_day(ev["date"]), "text": describe_event(ev, acct["name"]),
                        "source": ev.get("source"), "source_title": ev.get("source_title"), "id": ev.get("id")}
                if ev.get("future_dated"):
                    item["effective"] = ev["effective"].isoformat()
                if ev["type"] == "funding":
                    item["round"] = ev.get("round")
                    item["new_money"] = ev.get("new_money")
                if ev["type"] == "leadership":
                    item["departure"] = ev.get("departure")
                    item["function"] = ev.get("function")
                if ev["type"] == "office":
                    item["place"] = ev.get("place")
                if ev["type"] == "growth":
                    item["kinds"] = ev.get("kinds")
            signals_out.append(item)
        layoffs = [{"date": e["date"].isoformat(), "source": e.get("source")} for e in ev_by_org.get(perm, []) if e["type"] == "layoff"]
        rows.append({
            "uuid": acct["uuid"], "permalink": perm, "name": acct["name"], "url": acct.get("url"), "tier": acct.get("tier") or "",
            "score": s["score"] if complete else None, "score_status": "eligible" if complete and s["score"] is not None else "insufficient_evidence", "score_parts": s["parts"], "has_signal": has_signal,
            "signals": signals_out, "layoffs": layoffs, "contact": contact,
            "employees": acct.get("num_employees_enum"), "description": acct.get("short_description"),
            "growth_score": acct.get("growth_score"), "heat_delta_d90": acct.get("heat_score_delta_d90"),
            "growth_prediction": TIER_LABEL.get(acct.get("growth_prediction_tier") or "", None),
        })

    rows.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0), -(max([date.fromisoformat(x["date"]).toordinal() for x in r["signals"]] or [0])), r["name"].lower(), r["uuid"]))
    for i, r in enumerate(rows, start=1):
        r["rank"] = i if r["score"] is not None else None
    top_n = int(args.top)
    with_signal = [r for r in rows if r["has_signal"]]
    call_list = [r for r in with_signal if r["score"] is not None][:top_n] if complete else []

    for i, r in enumerate(call_list, start=1):
        r["position"] = i

    # ---- plays
    pw = int(args.plays_window)
    play_start = today - timedelta(days=min(pw, lookback) - 1)
    play_scope = parse_scope(args.plays_scope, accounts)
    groups: dict[tuple, list] = {}
    for r in rows:
        if r["permalink"] not in play_scope:
            continue
        for sgl in r["signals"]:
            if date.fromisoformat(sgl["date"]) < play_start:
                continue
            t = sgl["type"]
            if t == "funding":
                if not sgl.get("new_money"):
                    continue
                key = ("funding", funding_bucket(sgl.get("round", "")))
            elif t == "leadership":
                key = ("leadership", sgl.get("function") or "leadership")
            elif t == "prediction":
                if not sgl.get("newly"):
                    continue
                key = ("prediction", "newly predicted to raise")
            elif t == "acquisition":
                key = ("acquisition", "newly predicted to be acquired")
            else:
                key = (t, t)
            groups.setdefault(key, [])
            if r["permalink"] not in [x["permalink"] for x in groups[key]]:
                groups[key].append({"permalink": r["permalink"], "name": r["name"], "url": r["url"],
                                    "date": sgl["date"], "text": sgl["text"], "source": sgl.get("source")})
    # merge singleton subgroups of the same trigger into one group
    merged: dict[tuple, list] = {}
    for (t, sub), members in groups.items():
        if len(members) >= 2:
            merged[(t, sub)] = members
    for t in {k[0] for k in groups}:
        singles = [m for (tt, sub), ms in groups.items() if tt == t and len(ms) < 2 for m in ms]
        if not singles:
            continue
        pooled = {m["permalink"]: m for m in singles}
        for (tt, sub), ms in list(merged.items()):
            if tt == t:
                for m in ms:
                    pooled.pop(m["permalink"], None)
        if len(pooled) >= 2:
            generic = {"funding": "raised new money", "leadership": "leadership change", "launch": "launch",
                       "office": "office", "partnership": "partnership", "prediction": "newly predicted to raise",
                       "acquisition": "newly predicted to be acquired", "growth": "growth"}[t]
            merged[(t, generic)] = list(pooled.values())
    trigger_text = {
        "funding": lambda sub: ("closed a new fund" if sub.startswith("new fund") else
                                f"raised a {sub}" if sub not in ("raised new money", "funding round") else "raised new money"),
        "leadership": lambda sub: f"brought in a new {sub} leader" if sub not in ("leadership", "leadership change") else "had a leadership change",
        "launch": lambda sub: "launched a product",
        "office": lambda sub: "opened or expanded an office",
        "partnership": lambda sub: "announced a partnership",
        "prediction": lambda sub: "became newly predicted to raise within 0-5 months",
        "acquisition": lambda sub: "became newly predicted to be acquired",
        "growth": lambda sub: "showed customer, headcount or market growth",
    }
    plays = []
    for (t, sub), members in sorted(merged.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        members.sort(key=lambda m: m["date"], reverse=True)
        plays.append({"trigger": t, "group": sub, "count": len(members),
                      "headline": f"{len(members)} accounts {trigger_text[t](sub)} in the last {min(pw, lookback)} days",
                      "default_theme": PLAY_THEMES[t], "accounts": members})

    # ---- predicted-raise feed
    feed = []
    for perm, info in preds.items():
        if "prediction" not in signals:
            continue
        lt, pv = info["latest"], info["previous"]
        if not is_positive(lt):
            continue
        stale = bool(last_money.get(perm) and lt["generated_on"] < last_money[perm])
        if stale:
            continue
        if state and perm in state.get("predictions", {}):
            newly = not state["predictions"][perm].get("positive")
        else:
            newly = turned_positive(lt, pv)
        if not newly and not args.feed_all:
            continue
        acct = book[perm]
        key, wlabel, wprob = best_window(lt.get("ts") or {})
        prev_txt = ""
        if pv:
            _, pwl, _ = best_window(pv.get("ts") or {})
            prev_txt = f"{TIER_LABEL.get(pv.get('tier'), pv.get('tier'))}, most likely {pwl} ({pv['generated_on'].isoformat()})"
        reasons = [r for r in (lt.get("reasons") or []) if r]
        feed.append({
            "uuid": acct["uuid"], "company": acct["name"], "permalink": perm, "crunchbase_url": acct.get("url"),
            "website": acct.get("website_url"), "tier": acct.get("tier") or "",
            "newly_predicted": newly, "prediction_date": lt["generated_on"].isoformat(),
            "likelihood": TIER_LABEL.get(lt.get("tier"), lt.get("tier")),
            "probability_score": round(float(lt["score"]), 4) if isinstance(lt.get("score"), (int, float)) else None,
            "most_likely_window": wlabel, "previous": prev_txt,
            "reason": "; ".join(reasons[:3]),
            "last_funding_date": str(acct.get("last_funding_at") or "")[:10],
            "last_funding_type": acct.get("last_funding_type") or "",
            "last_new_money_date": last_money[perm].isoformat() if perm in last_money else "",
            "employees": acct.get("num_employees_enum") or "",
        })
    feed.sort(key=lambda f: (not f["newly_predicted"], f["likelihood"] != "Very Likely", f["prediction_date"], f["uuid"]), reverse=False)
    if not complete:
        feed = []
        plays = []
    feed_files = {}
    if args.feed_dir and complete:
        d = Path(args.feed_dir)
        d.mkdir(parents=True, exist_ok=True)
        stem = f"predicted-raises-{today.isoformat()}"
        cols = ["uuid", "company", "crunchbase_url", "website", "tier", "newly_predicted", "prediction_date", "likelihood",
                "probability_score", "most_likely_window", "previous", "reason", "last_funding_date",
                "last_funding_type", "last_new_money_date", "employees", "permalink"]
        with open(d / f"{stem}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for f in feed:
                w.writerow({k: safe_cell(v) for k, v in f.items()})
        (d / f"{stem}.json").write_text(json.dumps({"schema_version": "pulse-feed/v2", "as_of": today.isoformat(), "scope": scope, "coverage": coverage, "accounts": feed}, indent=2, allow_nan=False), encoding="utf-8")
        feed_files = {"csv": str((d / f"{stem}.csv").resolve()), "json": str((d / f"{stem}.json").resolve())}

    # ---- alerts (daily mode)
    alert_scope = parse_scope(args.alert_scope, accounts)
    if state and state.get("last_run"):
        since = date.fromisoformat(state["last_run"])
    elif args.since:
        since = date.fromisoformat(args.since)
    else:
        since = today - timedelta(days=1)
    if since > today:
        raise ValueError("since date cannot be after as-of")
    # without a state file, a prediction counts as new when it was made inside the window
    pred_since = since if (args.since and not state) else today - timedelta(days=7)
    max_age = max(ALERT_MAX_EVENT_AGE, (today - since).days)
    seen_before = set((state or {}).get("seen_events", {}))
    alerts = []
    for r in rows:
        if r["permalink"] not in alert_scope:
            continue
        items = []
        for ev in ev_by_org.get(r["permalink"], []):
            if ev["type"] in ("layoff", "partnership", "growth"):
                continue
            if ev["type"] == "funding" and not ev.get("new_money"):
                continue
            if ev["type"] == "leadership" and leadership_strength(ev.get("desc", "")) < 0.8:
                continue
            if ev.get("id") in seen_before:
                continue
            created = ev.get("created") or ev["date"]
            if created < since:
                continue
            if (today - ev["date"]).days > max_age:
                continue
            items.append({"type": ev["type"], "label": signal_label(ev["type"]), "date": ev["date"].isoformat(),
                          "date_text": fmt_day(ev["date"]), "text": describe_event(ev, r["name"]),
                          "source": ev.get("source"), "id": ev.get("id")})
        info = preds.get(r["permalink"])
        if "prediction" in signals and info and is_positive(info["latest"]):
            lt = info["latest"]
            stale = bool(last_money.get(r["permalink"]) and lt["generated_on"] < last_money[r["permalink"]])
            if state and r["permalink"] in state.get("predictions", {}):
                newly = not state["predictions"][r["permalink"]].get("positive")
            else:
                newly = turned_positive(lt, info["previous"]) and lt["generated_on"] >= pred_since
            if newly and not stale:
                _, wlabel, _ = best_window(lt.get("ts") or {})
                items.append({"type": "prediction", "label": "Predicted raise", "date": lt["generated_on"].isoformat(),
                              "date_text": fmt_day(lt["generated_on"]),
                              "text": f"Newly predicted to raise within {wlabel} ({TIER_LABEL.get(lt.get('tier'))})",
                              "likelihood": TIER_LABEL.get(lt.get("tier")), "reasons": (lt.get("reasons") or [])[:3],
                              "source": r["url"]})
        ainfo = acq.get(r["permalink"])
        aprev = ((state or {}).get("acq_predictions") or {}).get(r["permalink"])
        if "acquisition" in signals and acq_newly(ainfo, aprev) and (aprev is not None or ainfo[0][0] >= pred_since):
            items.append({"type": "acquisition", "label": "Predicted acquisition",
                          "date": ainfo[0][0].isoformat(), "date_text": fmt_day(ainfo[0][0]),
                          "text": f"Newly predicted to be acquired (Very Likely since {fmt_day(ainfo[0][0])})",
                          "likelihood": "Very Likely", "source": r["url"]})
        if items:
            alerts.append({"permalink": r["permalink"], "name": r["name"], "url": r["url"], "tier": r["tier"],
                           "items": items, "contact": r["contact"]})

    needs = {}
    shown = call_list + [r for r in with_signal[:25] if r not in call_list]
    missing_people = [r["permalink"] for r in shown if r["permalink"] not in people_by_org]
    if missing_people:
        needs["people_for"] = missing_people
    pos_without_reasons = [perm for perm, info in preds.items()
                           if is_positive(info["latest"]) and not info["latest"].get("reasons")]
    if pos_without_reasons:
        needs["prediction_reasons_for"] = pos_without_reasons
        needs["prediction_reasons_since"] = min(preds[p]["latest"]["generated_on"] for p in pos_without_reasons).isoformat()

    if args.list_csv:
        with open(args.list_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["schema_version", "as_of", "uuid", "score", "score_status", "rank", "company", "crunchbase_url", "tier", "signal", "signal_date", "what_happened", "source",
                        "contact_name", "contact_title", "contact_url"])
            for r in rows:
                s0 = r["signals"][0] if r["signals"] else {}
                c = r["contact"] or {}
                w.writerow([safe_cell(v) for v in ["pulse-ranked/v2", today.isoformat(), r["uuid"], r["score"], r["score_status"], r["rank"], r["name"], r["url"], r["tier"], s0.get("label", ""), s0.get("date", ""),
                            s0.get("text", ""), s0.get("source", ""), c.get("name") or "", c.get("title") or "", c.get("url") or ""]])

    # The first persistent run establishes a baseline, never retroactive alerts.
    if (args.state and state is None) or not complete:
        alerts = []
    state_out = str(Path(args.state).resolve()) if args.state and args.write_state else None
    result = {
        "schema_version": "pulse-result/v2", "as_of": today.isoformat(), "scope": scope,
        "coverage": coverage, "coverage_issues": coverage_issues, "rejected_observations": rejected,
        "complete": complete, "baseline": bool(args.state and state is None), "ranked": rows,
        "today": today.isoformat(), "lookback_days": lookback, "window_start": start.isoformat(),
        "signals": signals, "accounts_in_book": len(book),
        "accounts_with_signals": len(with_signal),
        "call_list": call_list,
        "flagged": [r for r in with_signal if r["score"] is not None][:25] if complete else [], "flagged_count": len(with_signal),
        "unranked_evidence": [r for r in with_signal if r["score"] is None],
        "plays": plays,
        "raise_feed": feed, "raise_feed_files": feed_files,
        "alerts": alerts, "alert_since": since.isoformat(), "state_found": bool(state),
        "state_commit_requested": state_out, "state_written": None,
        "needs": needs,
        "stats": {"events": len(events), "predictions_orgs": len(preds), "acquisition_prediction_orgs": len(acq),
                  "people": len(people)},
    }

    if state_out:
        st = new_state(state, today, events, preds, accounts, alerts, acq)
        st["scope_fingerprint"] = fingerprint
        st["scope"] = scope
        # Durable result first; failed output writes cannot advance the baseline.
        atomic_json(Path(args.out), result)
        atomic_json(Path(args.state), st)
        result["state_written"] = state_out
    return result


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("book")
    b.add_argument("file")
    b.add_argument("--out")
    m = sub.add_parser("match")
    m.add_argument("--book", required=True)
    m.add_argument("--orgs", nargs="+", required=True)
    m.add_argument("--resolved", help="JSON file mapping book names to Crunchbase permalinks")
    m.add_argument("--out")
    r = sub.add_parser("rank")
    r.add_argument("--accounts", required=True)
    r.add_argument("--data", nargs="*")
    r.add_argument("--today", required=True)
    r.add_argument("--coverage", required=True)
    r.add_argument("--lookback", default=90)
    r.add_argument("--signals")
    r.add_argument("--top", default=10)
    r.add_argument("--plays-window", default=60)
    r.add_argument("--plays-scope")
    r.add_argument("--alert-scope")
    r.add_argument("--focus")
    r.add_argument("--buyer-titles")
    r.add_argument("--state")
    r.add_argument("--write-state", action="store_true")
    r.add_argument("--since", help="alert window start (YYYY-MM-DD) when there is no state file")
    r.add_argument("--feed-dir")
    r.add_argument("--feed-all", action="store_true")
    r.add_argument("--list-csv")
    r.add_argument("--out")
    args = ap.parse_args()
    try:
        if args.cmd == "book":
            result = read_book(Path(args.file))
        elif args.cmd == "match":
            book = load_json_any(Path(args.book))
            if args.resolved:
                mapping = load_json_any(Path(args.resolved))
                for row in book["rows"]:
                    if not row.get("permalink") and row.get("name") in mapping and mapping[row["name"]]:
                        row["permalink"] = mapping[row["name"]]
            result = match_book(book, collect_orgs(args.orgs))
        else:
            result = run_rank(args)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(result, indent=2, ensure_ascii=False, default=str, allow_nan=False)
    if getattr(args, "out", None):
        if not (args.cmd == "rank" and args.write_state):
            atomic_json(Path(args.out), result)
        print(json.dumps({"written": str(Path(args.out).resolve()), "state_written": result.get("state_written"),
                          "summary": {k: (len(v) if isinstance(v, list) else v) for k, v in result.items()
                                      if k in ("accounts", "unmatched", "rows", "counts", "call_list", "plays", "raise_feed", "alerts", "needs")}},
                         indent=2, default=str))
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
