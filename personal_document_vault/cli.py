"""Local-only CLI. JSON input, atomic writes, and named failures."""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from .core import VaultError, build_result, search, validate_record, parse_date
from .fixtures import LABEL, expectations, fixture_records, tiny_records
from .report import json_text, render, provenance_banner


def read_json(path):
    try:
        text = path.read_text(encoding="utf-8-sig")
        return json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite number {value}")),
                          object_pairs_hook=unique_keys)
    except json.JSONDecodeError as exc:
        raise VaultError(f"ParseError: {path.name}: line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise VaultError(f"ParseError: {path.name}: line 1: {exc}") from exc
    except OSError as exc:
        raise VaultError(f"ReadError: {path}: {exc.strerror}") from exc


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def load_input(directory, as_of):
    root = Path(directory)
    if not root.is_dir():
        raise VaultError(f"MissingInput: {root}: directory not found; use pdv fixtures --out demo or supply --input <dir>")
    records, sources, seen = [], [], set()
    reference = parse_date(as_of, "as_of")
    try:
        paths = sorted(root.iterdir(), key=lambda p: p.name)
    except OSError as exc:
        raise VaultError(f"ReadError: {root}: {exc.strerror}") from exc
    for path in paths:
        if not path.is_file() or path.name == "expectations.json":
            continue
        if "\u2014" in path.name or any(ord(c) < 32 for c in path.name):
            raise VaultError("SchemaError: source filename: control characters and U+2014 are forbidden")
        if path.suffix.lower() != ".json":
            raise VaultError(f"SchemaError: {path.name}: field file_format: only JSON input is supported")
        envelope = read_json(path)
        if not isinstance(envelope, dict) or set(envelope) - {"_label", "synthetic", "records"} or not {"synthetic", "records"} <= envelope.keys():
            raise VaultError(f"SchemaError: {path.name}: fields: expected synthetic, records, optional _label")
        if type(envelope["synthetic"]) is not bool or not isinstance(envelope["records"], list):
            raise VaultError(f"SchemaError: {path.name}: fields synthetic/records: expected boolean/list")
        label = envelope.get("_label", "")
        if not isinstance(label, str) or len(label) > 10000 or "\u2014" in label:
            raise VaultError(f"SchemaError: {path.name}: field _label: invalid label")
        for index, record in enumerate(envelope["records"], 1):
            try:
                item = validate_record(record, reference)
                if envelope["synthetic"] and not item["synthetic"]:
                    raise VaultError("SchemaError: synthetic: real record inside synthetic file")
                if item["synthetic"] and "synthetic" not in label.casefold():
                    raise VaultError("SchemaError: _label: synthetic records require a SYNTHETIC file label")
                if item["id"] in seen:
                    raise VaultError(f"SchemaError: id: duplicate {item['id']!r}")
                seen.add(item["id"])
                records.append(item)
            except VaultError as exc:
                raise VaultError(f"{exc} (file {path.name}, record {index})") from exc
        sources.append(path.name)
    return build_result(records, as_of, sources)


def atomic_write(path, text):
    destination = Path(path)
    temporary = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=destination.parent,
                                         prefix=".pdv-write-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, destination)
    except OSError as exc:
        raise VaultError(f"WriteError: {destination}: {exc.strerror}; no partial output retained") from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def generate(directory):
    destination = Path(directory).resolve()
    staging = None
    try:
        if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
            raise VaultError(f"WriteError: {destination}: fixtures require a new or empty directory")
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".pdv-fixtures-", dir=destination.parent)).resolve()
        atomic_write(staging / "records.json", json_text({"_label": LABEL, "synthetic": True, "records": fixture_records()}))
        atomic_write(staging / "expectations.json", json_text(expectations()))
        atomic_write(staging / "tiny" / "records.json", json_text({"_label": LABEL, "synthetic": True, "records": tiny_records()}))
        if destination.exists():
            destination.rmdir()  # Already verified empty; never replace user data.
        os.replace(staging, destination)
    except OSError as exc:
        raise VaultError(f"WriteError: {destination}: {exc.strerror}") from exc
    finally:
        if staging is not None and staging.exists() and staging.parent == destination.parent and staging.name.startswith(".pdv-fixtures-"):
            shutil.rmtree(staging)


def load_state(path):
    if not Path(path).is_file():
        raise VaultError(f"MissingState: {path}: run pdv run --input <dir> first")
    state = read_json(Path(path))
    try:
        if state["schema_version"] != 1:
            raise VaultError("SchemaError: state.schema_version: expected 1")
        sources = state["provenance"]["sources"]
        if not isinstance(sources, list) or any(not isinstance(s, str) or "\u2014" in s or any(ord(c) < 32 for c in s) for s in sources):
            raise VaultError("SchemaError: state.sources: invalid source names")
        return build_result(state["records"], state["as_of"], sources)
    except (KeyError, TypeError) as exc:
        raise VaultError("SchemaError: state: missing or invalid required fields; rerun pdv run") from exc


def parser():
    p = argparse.ArgumentParser(prog="pdv", description="Search local document metadata and compute exact expiry reports. No file-content scanning.")
    subs = p.add_subparsers(dest="command", required=True)
    f = subs.add_parser("fixtures", help="Generate 200 labelled synthetic records and a five-record example", epilog="Example: pdv fixtures --out demo")
    f.add_argument("--out", required=True)
    r = subs.add_parser("run", help="Validate JSON metadata and save a computed snapshot", epilog="Example: pdv run --input demo --as-of 2026-09-30")
    r.add_argument("--input", required=True)
    r.add_argument("--as-of", default="2026-09-30", help="Explicit reference date; reproducible default: 2026-09-30, never today's date")
    rp = subs.add_parser("report", help="Render a snapshot with provenance and traceable counts", epilog="Example: pdv report --format md --out report.md")
    rp.add_argument("--format", choices=["md", "json"], default="md")
    rp.add_argument("--out", help="Optional atomically written report file; otherwise stdout")
    s = subs.add_parser("search", help="Find literal substrings in document metadata", epilog='Example: pdv search --query passport --category identity')
    s.add_argument("--query", required=True)
    s.add_argument("--category", help="Optional exact category filter, case insensitive")
    show = subs.add_parser("show", help="Look up one document by exact ID", epilog="Example: pdv show --id DOC-001")
    show.add_argument("--id", required=True)
    for sub in (r, rp, s, show):
        sub.add_argument("--state", default=".pdv/result.json", help="Local snapshot path (default: .pdv/result.json)")
    return p


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", newline="\n")
    args = parser().parse_args(argv)
    try:
        if any(isinstance(value, str) and "\u2014" in value for value in vars(args).values()):
            raise VaultError("SchemaError: CLI arguments: U+2014 is forbidden")
        if args.command == "fixtures":
            generate(args.out)
            print("Generated 200 SYNTHETIC records and hand-computed expectations; tiny/ contains five SYNTHETIC records.")
        elif args.command == "run":
            result = load_input(args.input, args.as_of)
            atomic_write(args.state, json_text(result))
            print(provenance_banner(result))
            print(f"Computed {result['figures']['total_records']} records as of {args.as_of}. Snapshot: {args.state}")
            print("Time saved and money saved: unmeasured; no savings claimed.")
        else:
            result = load_state(args.state)
            if args.command == "report":
                output = render(result, args.format)
                if args.out:
                    atomic_write(args.out, output)
                    print(f"Report written: {args.out}")
                    print(provenance_banner(result))
                else:
                    sys.stdout.write(output)
            else:
                if args.command == "search":
                    matches = search(result["records"], args.query, args.category)
                else:
                    matches = [r for r in result["records"] if r["id"] == args.id]
                    if not matches:
                        raise VaultError(f"DocumentNotFound: id {args.id!r}; use pdv search --query <text>")
                sys.stdout.write(json_text({"banner": provenance_banner(result), "match_count": len(matches), "records": matches}))
        return 0
    except VaultError as exc:
        # Keep every error surface free of U+2014 even when user filenames contain it.
        print(str(exc).replace("\u2014", "[U+2014]"), file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as exc:
        print(f"IOError: {exc}".replace("\u2014", "[U+2014]"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
