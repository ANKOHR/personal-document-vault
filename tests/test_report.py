import json

from personal_document_vault.core import build_result
from personal_document_vault.fixtures import expectations, fixture_records, tiny_records
from personal_document_vault.report import render


def test_report_matches_ground_truth_exact():
    report = json.loads(render(build_result(fixture_records()), "json"))
    assert report["figures"] == expectations()["figures"]
    assert report["cases"] == expectations()["cases"]


def test_report_zero_false_positives():
    report = json.loads(render(build_result(fixture_records()), "json"))
    for field in ("expired_ids", "upcoming_ids"):
        actual, expected = set(report["cases"][field]), set(expectations()["cases"][field])
        assert actual - expected == set()
        assert expected - actual == set()


def test_report_carries_provenance_banner():
    records = tiny_records()
    records[-1]["synthetic"] = False
    for format in ("md", "json"):
        text = render(build_result(records, sources=["records.json"]), format)
        assert "DATA PROVENANCE: 4 synthetic fixture records; 1 user-declared real records" in text
        assert "Henry" in text and "records.json" in text


def test_hypothetical_figures_labelled():
    for format in ("md", "json"):
        text = render(build_result([]), format)
        assert "Unmeasured" in text
        assert "Hypothetical or illustrative figures would require explicit labels" in text
        assert "no savings claimed" in text


def test_no_em_dashes_in_outputs():
    for format in ("md", "json"):
        assert "\u2014" not in render(build_result(fixture_records()), format)


def test_markdown_escapes_untrusted_metadata():
    record = tiny_records()[0]
    record["title"] = "<script>alert(1)</script>|[click](url)"
    text = render(build_result([record]))
    assert "<script>" not in text
    assert "&#124;" in text and "&#91;click&#93;" in text


def test_empty_report():
    assert "total_records | 0" in render(build_result([]))
