"""Measure the installed local CLI, check independent expectations, save synthetic reports."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sysconfig
import tempfile
import time


def main():
    root = Path(__file__).resolve().parents[1]
    executable = shutil.which("pdv")
    if executable is None:
        scripts = Path(sysconfig.get_path("scripts", scheme="nt_user" if os.name == "nt" else "posix_user"))
        executable = str(scripts / ("pdv.exe" if os.name == "nt" else "pdv"))
    evidence = root / "evidence"
    evidence.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pdv-demo-") as temporary:
        working = Path(temporary)
        def call(*args):
            output = subprocess.run([executable, *args], cwd=working, capture_output=True, check=True)
            return output.stdout.decode("utf-8")
        start = time.perf_counter()
        call("fixtures", "--out", "demo")
        call("run", "--input", "demo")
        report_start = time.perf_counter()
        markdown = call("report", "--format", "md")
        report_seconds = time.perf_counter() - report_start
        full_seconds = time.perf_counter() - start
        report_json = call("report", "--format", "json")
        actual = json.loads(report_json)
        expected = json.loads((working / "demo" / "expectations.json").read_text(encoding="utf-8"))
        assert actual["figures"] == expected["figures"]
        assert actual["cases"] == expected["cases"]
        assert actual["provenance"]["synthetic_records"] == 200
        assert full_seconds < 5 and report_seconds < 5
        first_snapshot = (working / ".pdv" / "result.json").read_bytes()
        call("run", "--input", "demo")
        assert (working / ".pdv" / "result.json").read_bytes() == first_snapshot
        assert call("report", "--format", "md") == markdown
        assert call("report", "--format", "json") == report_json
        for format, text in (("md", markdown), ("json", report_json)):
            with (evidence / f"synthetic-report.{format}").open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
        measurements = {"_label": "SYNTHETIC INPUT BENCHMARK: timings measured locally, no real-use or savings claims.",
                        "synthetic": True, "measured_on": "2026-10-01", "records": 200,
                        "report_seconds_measured": report_seconds, "full_demo_seconds_measured": full_seconds,
                        "exact_figures_match": True, "exact_case_sets_match": True,
                        "false_positives": 0, "false_negatives": 0, "byte_identical_repeat": True,
                        "timing_scope": "Installed pdv process startup, fixtures, run, Markdown report; JSON and repeat checks excluded.",
                        "savings": "Unmeasured; no baseline and no savings claimed."}
        with (evidence / "measurements.json").open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(measurements, indent=2, sort_keys=True) + "\n")
        print(json.dumps(measurements, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
