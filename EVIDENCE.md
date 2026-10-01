# Local build evidence

Measured on 2026-10-01 with Python 3.12.10 on this Windows workstation. All inputs in this evidence are synthetic. No real document trial or savings baseline was used.

The installed `pdv` executable ran fixtures, run, and Markdown report as three fresh local processes. Full demo elapsed time was **0.756032 seconds**, including process startup and output capture. The report process alone took **0.232288 seconds**. Both are below the five-second acceptance limit. This is one measured run on this machine, not a guarantee for other hardware or large inputs.

`scripts/verify_demo.py` reproduced the exact fixture figures and all four case sets from the independent expectations file. There were zero false positives and zero false negatives for expiry flags. All 200 records reconcile: 20 expired + 20 upcoming + 40 current + 120 unspecified. Each category has 50 records, and the declared input amount total is 50,000 GBP pence. This total is not money saved. Repeated run snapshots and both report formats were byte-identical.

The pytest suite has **50 passing cases**. It covers the required acceptance tests and additional boundaries, non-finite JSON, duplicate keys, duplicate IDs, negative and extreme amounts, invalid and future issue dates, long Unicode metadata, Windows paths, preserved snapshots on failed runs, atomic write failure, provenance for mixed and real declarations, Markdown escaping, and modified fixture inputs. A deep-nesting case verifies a named failure without a traceback across decoder implementations.

Artifacts:

- `evidence/measurements.json`: measured timings and verification outcomes, explicitly labelled synthetic input benchmark.
- `evidence/synthetic-report.md`: full computed report, synthetic provenance banner, exact flags and document index.
- `evidence/synthetic-report.json`: full computed metadata and figures with the same provenance.

Reproduce after offline editable installation:

```powershell
python -m pytest -q
python scripts/verify_demo.py
```

The benchmark regenerates only synthetic evidence artifacts; its measured elapsed times naturally vary. Production outputs contain no timing fields and remain deterministic. Build history and `BUILD-DONE.txt` identify the tested local implementation. Publishing is delegated to the separate verification step and was not performed here.
