"""Pure metadata validation, search, and expiry accounting. No file I/O."""

from collections import Counter
from datetime import date
import re


class VaultError(ValueError):
    """A named, user-actionable vault failure."""


def parse_date(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise VaultError(f"SchemaError: {field}: expected YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise VaultError(f"SchemaError: {field}: invalid calendar date") from exc


def validate_record(record, as_of):
    required = {"id", "title", "category", "path", "issued_on", "expires_on", "tags", "synthetic"}
    allowed = required | {"amount_minor"}
    if not isinstance(record, dict):
        raise VaultError("SchemaError: record: expected object")
    missing, unknown = required - record.keys(), record.keys() - allowed
    if missing or unknown:
        raise VaultError(f"SchemaError: fields: missing={sorted(missing)}, unknown={sorted(unknown)}")
    for field in ("id", "title", "category", "path"):
        value = record[field]
        limit = {"id": 128, "category": 128, "title": 10000, "path": 32768}[field]
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise VaultError(f"SchemaError: {field}: expected nonempty string of at most {limit} characters")
        if any(ord(c) < 32 for c in value) or "\u2014" in value:
            raise VaultError(f"SchemaError: {field}: control characters and U+2014 are forbidden")
    if type(record["synthetic"]) is not bool:
        raise VaultError("SchemaError: synthetic: expected boolean")
    tags = record["tags"]
    if not isinstance(tags, list) or len(tags) > 100:
        raise VaultError("SchemaError: tags: expected list with at most 100 tags")
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip() or len(tag) > 256 or any(ord(c) < 32 for c in tag) or "\u2014" in tag:
            raise VaultError("SchemaError: tags: invalid tag")
    if len(set(tags)) != len(tags):
        raise VaultError("SchemaError: tags: duplicate tags")
    issued = parse_date(record["issued_on"], "issued_on")
    if issued > as_of:
        raise VaultError("SchemaError: issued_on: future issue date")
    expiry = None if record["expires_on"] is None else parse_date(record["expires_on"], "expires_on")
    if expiry is not None and expiry < issued:
        raise VaultError("SchemaError: expires_on: precedes issued_on")
    amount = record.get("amount_minor")
    if amount is not None and (type(amount) is not int or not 0 <= amount <= 10**12):
        raise VaultError("SchemaError: amount_minor: expected integer GBP pence between 0 and 1000000000000")
    return {**record, "tags": sorted(tags)}


def build_result(records, as_of="2026-09-30", sources=None):
    reference = parse_date(as_of, "as_of")
    validated, seen = [], set()
    for record in records:
        item = validate_record(record, reference)
        if item["id"] in seen:
            raise VaultError(f"SchemaError: id: duplicate {item['id']!r}")
        seen.add(item["id"])
        validated.append(item)
    validated.sort(key=lambda r: r["id"])
    expired, upcoming, current, undated = [], [], [], []
    for item in validated:
        if item["expires_on"] is None:
            undated.append(item["id"])
        else:
            days = (parse_date(item["expires_on"], "expires_on") - reference).days
            (expired if days < 0 else upcoming if days <= 30 else current).append(item["id"])
    synthetic = sum(r["synthetic"] for r in validated)
    amounts = [r["amount_minor"] for r in validated if r.get("amount_minor") is not None]
    return {
        "schema_version": 1, "as_of": as_of, "upcoming_window_days": 30,
        "provenance": {"synthetic_records": synthetic, "real_records": len(validated) - synthetic,
                       "sources": sorted(sources or []),
                       "real_declaration": "Real inputs are user-declared Henry-entered data, not independently verified."},
        "figures": {"total_records": len(validated), "expired_count": len(expired),
                    "upcoming_count": len(upcoming), "current_count": len(current),
                    "no_expiry_count": len(undated), "amount_record_count": len(amounts),
                    "declared_amount_total_gbp_pence": sum(amounts),
                    "category_counts": dict(sorted(Counter(r["category"] for r in validated).items()))},
        "cases": {"expired_ids": expired, "upcoming_ids": upcoming, "current_ids": current, "no_expiry_ids": undated},
        "measurement": {"basis": "Computed exactly from supplied metadata; file contents and existence are not checked.",
                        "time_saved": "Unmeasured: no baseline supplied; no savings claimed.",
                        "money_saved": "Unmeasured: declared amounts are not savings; no savings claimed.",
                        "hypothetical_figures": "None. Hypothetical or illustrative figures would require explicit labels."},
        "records": validated,
    }


def search(records, query, category=None):
    """Case-insensitive literal substring matching on metadata, with exact category filter."""
    needle = query.casefold()
    return sorted((r for r in records if (category is None or r["category"].casefold() == category.casefold())
                   and needle in "\n".join([r["id"], r["title"], r["category"], r["path"], *r["tags"]]).casefold()),
                  key=lambda r: r["id"])
