"""Deterministic rendering with an explicit provenance banner."""

import json


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"


def provenance_banner(result):
    p = result["provenance"]
    return (f"DATA PROVENANCE: {p['synthetic_records']} synthetic fixture records; "
            f"{p['real_records']} user-declared real records (Henry's own data entered by him). "
            "Real declarations are not independently verified.")


def escape(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("`", "&#96;").replace("*", "&#42;").replace("_", "&#95;").replace("[", "&#91;").replace("]", "&#93;")


def render(result, format="md"):
    if format == "json":
        return json_text({"banner": provenance_banner(result), **result})
    if format != "md":
        raise ValueError("format must be md or json")
    lines = ["# Personal Document Vault", "", provenance_banner(result), "",
             f"Reference date: {result['as_of']}. Upcoming window: 0 to 30 days inclusive.", "",
             "Inputs: " + (", ".join(escape(s) for s in result["provenance"]["sources"]) or "none"), "",
             "## Computed figures", "", "| Figure | Value |", "| --- | ---: |"]
    for key, value in result["figures"].items():
        if key != "category_counts":
            lines.append(f"| {key} | {value} |")
    lines.extend(["", "Category counts: " + escape(json.dumps(result["figures"]["category_counts"], ensure_ascii=False, sort_keys=True)), "",
                  "Declared amount total is GBP pence from explicit metadata only. Missing amounts are unknown, not measured zero amounts.", "",
                  "## Honesty boundary", ""])
    lines.extend(result["measurement"].values())
    lines.extend(["", "## Traceable cases", ""])
    for key, ids in result["cases"].items():
        lines.append(f"{key}: " + (", ".join(escape(i) for i in ids) or "none"))
    lines.extend(["", "## Document index", "", "| ID | Title | Category | Expiry | Path | Provenance |", "| --- | --- | --- | --- | --- | --- |"])
    for r in result["records"]:
        values = [r["id"], r["title"], r["category"], r["expires_on"] or "unspecified", r["path"], "synthetic" if r["synthetic"] else "user-declared real"]
        lines.append("| " + " | ".join(escape(v) for v in values) + " |")
    return "\n".join(lines) + "\n"
