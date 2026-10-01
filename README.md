# Personal Document Vault

`pdv` is a deterministic, CPU-only Python CLI for a local, structured document metadata store. It validates records, searches metadata, looks up documents, and reports expiry status, category counts, and optional declared amounts. It never opens the referenced documents or infers their contents. There are no runtime dependencies, databases, external network calls, or language-model calls.

Hypothesis: exact validation and deterministic accounting over explicit metadata can give Henry a trustworthy index for school, identity, finance, and application documents. Local synthetic acceptance tests support computational correctness. Actual usefulness and time savings remain unmeasured.

## Quickstart

Python 3.10 or newer and setuptools 68 or newer are required. Run from the project root. Installation is offline using the existing build tools:

```powershell
python -m pip install --no-index --no-deps --no-build-isolation -e .
# If pip warns that its Scripts directory is outside PATH:
$pdvScripts = python -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))"
$env:PATH = "$pdvScripts;$env:PATH"
pdv fixtures --out demo
pdv run --input demo
pdv report --format md
```

In a shell supporting `&&`, the requested demo is:

```powershell
pdv fixtures --out demo && pdv run --input demo && pdv report --format md
```

Fixtures require a new or empty output directory, so choose a fresh name for a second demo. `python -m personal_document_vault.cli` also works everywhere `pdv` appears here. To run the five hand-written records instead:

```powershell
pdv run --input demo/tiny
pdv report --format json
python -m pytest -q
```

`run` saves `.pdv/result.json` atomically; reports and searches use that snapshot. Rerun after editing inputs. `--state` selects an alternative snapshot on each consuming command. Keep snapshots outside the immediate input directory. Both snapshots and demo data are git-ignored because real records should never be shipped.

## Input format

Place UTF-8 JSON envelopes in one directory. Every immediate JSON file is loaded in filename order, except `expectations.json`, which is reserved for fixture verification and never used to compute results. Subdirectories are not traversed. Non-JSON immediate files cause a named format error; YAML, CSV, and JSONL are not supported in this version. An empty directory is a valid zero-record input.

This is a labelled synthetic example, not real data:

```json
{
  "_label": "SYNTHETIC example, invented metadata",
  "synthetic": true,
  "records": [
    {
      "id": "EXAMPLE-001",
      "title": "Synthetic passport",
      "category": "identity",
      "path": "C:\\Vault\\passport.pdf",
      "issued_on": "2020-01-01",
      "expires_on": "2026-10-15",
      "tags": ["travel"],
      "synthetic": true,
      "amount_minor": 100
    }
  ]
}
```

For real inputs, Henry enters his own metadata by hand and sets the envelope and each real record's `synthetic` to `false`. That is a user declaration, not verification that a file exists or belongs to him. A mixed envelope must use `synthetic: false`; each synthetic record still requires `synthetic: true` and a file `_label` containing `SYNTHETIC`. Trial results stay local and are not committed or published.

| Field | Rules |
| --- | --- |
| `id` | Required, unique across all input files, case sensitive, nonblank, up to 128 characters |
| `title` | Required nonblank string, up to 10,000 characters |
| `category` | Required nonblank string, up to 128 characters; free vocabulary |
| `path` | Required nonblank string, up to 32,768 characters; Windows and relative paths supported; never resolved or opened |
| `issued_on` | Required exact `YYYY-MM-DD`, valid date, no later than reference date |
| `expires_on` | Required date or `null`; cannot precede issue date; future expiry dates are expected |
| `tags` | Required list, up to 100 unique nonblank strings, each up to 256 characters |
| `synthetic` | Required JSON boolean on every record and envelope |
| `amount_minor` | Optional integer or `null`, GBP pence only, 0 through 1,000,000,000,000; no floats, booleans, or negative amounts |
| `_label` | Envelope-only optional string, required to label synthetic records, up to 10,000 characters |

Unknown fields, duplicate JSON keys, non-finite numbers, duplicate IDs, control characters in searchable strings, and U+2014 are rejected. No rows are silently dropped. Unicode is preserved. IDs are not normalized, so `A` and `a` are different IDs. The amount is an explicitly entered document-associated amount, not a inferred balance, cost, or saving. A missing amount remains unknown; the report counts supplied amounts separately and totals only supplied values using integer arithmetic.

The default reference date is fixed at `2026-09-30` for reproducibility. For current use, explicitly supply `--as-of YYYY-MM-DD`. Expired means expiry before that date. Upcoming means expiry from that date through 30 days later, inclusive. Current means a later expiry. No-expiry records have an unspecified expiry, which is not evidence that they never expire. These four groups partition all records exactly.

## Commands

Each subcommand has `--help` with an example.

| Command | Purpose | Example |
| --- | --- | --- |
| `fixtures` | Generate 200 synthetic records, independent expectations, and a five-record input | `pdv fixtures --out demo` |
| `run` | Validate all inputs and compute the snapshot | `pdv run --input my-input --as-of 2026-10-01` |
| `report` | Render Markdown or JSON, optionally atomically to a file | `pdv report --format json --out report.json` |
| `search` | Case-insensitive literal substring in ID, title, category, path, or tags | `pdv search --query passport --category identity` |
| `show` | Exact, case-sensitive ID lookup | `pdv show --id DOC-001` |

Search is metadata-only, uses no regular expressions, and can filter category by a case-insensitive exact match. Empty query lists all records. Output is deterministic JSON sorted by ID. `show` returns a named error when the ID does not exist. Reports include source filenames, the reference date, exact case IDs, and a document index for tracing each figure. Saved derived counts are recomputed from snapshot records when read, so editing a cached total cannot forge a reported total.

## Architecture

```text
UTF-8 JSON envelopes
        |
        v
cli.py: parse, validate envelopes, name errors
        |
        v
core.py: pure schema validation, expiry groups, totals, search
        |
        v
cli.py: atomic local snapshot
        |
        +--> search / show: metadata lookup with provenance
        |
        v
report.py: deterministic Markdown / JSON with provenance

fixtures.py --> labelled 200-record fixture + independent expectations
            --> hand-written five-record example
tests/      --> planted ground truth, boundaries, adversarial inputs
```

There is no random generator and no seed to configure. Filenames, records, tags, and categories are sorted; no timestamps, elapsed times, or absolute input paths are added to reports. Identical input content, source filenames, and reference date yield byte-identical snapshots and reports. Recorded performance timings are measurements in the build evidence, not fields added to the deterministic report.

## Honesty boundary and fixture policy

Every report and lookup carries a provenance banner splitting synthetic fixture records and user-declared real records. Real data means Henry's own data entered by him, not an independent ownership check. Counts and expiry states are computed from metadata only. Paths are pointers, not proof of a document's existence, validity, or authenticity. This tool does not extract text, verify documents, discover missing files, predict outcomes, or estimate savings.

Time saved and money saved are explicitly **unmeasured**. No baseline has been provided and no savings are claimed. Hypothetical or illustrative figures would require explicit labels in code, output, and docs. The shipped tool reports none. Optional declared GBP amounts are measured input totals and never described as money saved.

JSON cannot carry header comments, so each synthetic fixture file has a top-level `_label` starting with `SYNTHETIC FIXTURE` and `synthetic: true`. Every fixture record also has `synthetic: true`. The tiny example follows the same policy. No other fixture file formats are emitted. Expectations contain independently specified hand-counted blocks: 20 expired, 20 upcoming, 40 current, 120 unspecified; four categories of 50 each; 50 repetitions of 100 + 200 + 300 + 400 pence give 50,000 pence. All 200 cases are enumerated in the expectations file. Changing records changes reports, even if the expectations file remains unchanged or is deliberately wrong.

## Failure modes and limits

| Condition | Behavior |
| --- | --- |
| Missing input directory | `MissingInput`, usage hint, exit 2 |
| Malformed JSON | `ParseError`, filename, line and column for syntax errors, exit 2 |
| Duplicate keys, non-finite values, invalid encoding | `ParseError`, filename; line 1 for whole-file semantic or decoding failures |
| Excessive nesting | Named `ParseError` if the decoder limit is exceeded, otherwise `SchemaError` for an invalid envelope |
| Schema drift or invalid record | `SchemaError`, offending field, filename and record position, exit 2 |
| Duplicate ID or invalid value | Entire run fails; last good snapshot is preserved |
| Missing snapshot | `MissingState`, run hint, exit 2 |
| Missing document ID | `DocumentNotFound`, search hint, exit 2 |
| Bad output path | `WriteError`, exit 2; temporary file removed and previous output preserved |
| Existing fixture directory containing files | Refuse overwrite with `WriteError` |
| Empty input directory | Valid zero report, exit 0 |

There is no encryption or access-control layer. Keep the local inputs and snapshots in a private directory protected by the operating system. The CLI provides structured indexing, not secure document storage. Do not commit personal files. No claim is made about scale beyond the tested 200-record fixture. Concurrent writers to the same snapshot use last successful atomic replacement; use distinct `--state` paths for separate workflows. A report write failure does not invalidate the existing snapshot.

## Evidence, improvement hook, and verdict

See `EVIDENCE.md` for local test and demo measurements and `BUILD-DONE.txt` for the tested implementation commit. The acceptance checks cover exact reconciliation, zero false positives, determinism, malformed inputs, Unicode, long strings, and changed ground truth. They demonstrate the synthetic fixture outcome, not real-world accuracy or time saved.

After the first real-use day, use a two-week evidence window. Record dates of actual runs privately and hand-check at least 20 real records (or every record if fewer). The primary metric is the percentage of checked records whose ID, category, expiry status, and entered amount disagree with the hand-checked source. Count each record with any discrepancy once. Record numerator and denominator; no sample means **unmeasured**, not 0 percent. Also record whether Henry actually used the tool. Optional timing against a named manual baseline can support measured time savings; until then savings remain unmeasured.

If error rate exceeds 10 percent, fix the single largest observed cause and retest the sample, or kill the project with the reason recorded. If the tool is never used, kill it rather than keep unused decoration. Do not invent a trial. `VERDICT.md` records a provisional **maintain** verdict based solely on the local acceptance evidence; the final real-use verdict is pending the two-week window. At that point: expand for daily use or revenue; integrate for heavy overlap with a sibling; commercialise if a buyer would pay as-is; maintain as portfolio evidence if justified; kill for non-use or inability to meet acceptance criteria.

## Publication

This build is local only. Publishing to the public target `ANKOHR/personal-document-vault` is authorised but handled by a separate verification step. No GitHub repository or remote has been created by this build.
