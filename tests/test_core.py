from copy import deepcopy

import pytest

from personal_document_vault.core import VaultError, build_result, search
from personal_document_vault.fixtures import fixture_records, tiny_records


def test_empty_input_renders_without_traceback():
    result = build_result([])
    assert result["figures"]["total_records"] == 0
    assert result["figures"]["declared_amount_total_gbp_pence"] == 0


@pytest.mark.parametrize("field,value", [
    ("amount_minor", -1), ("amount_minor", True), ("amount_minor", 1.5),
    ("amount_minor", 10**12 + 1), ("issued_on", "2099-01-01"),
    ("issued_on", "2026-02-30"), ("expires_on", "2019-01-01"),
    ("title", "x" * 10001), ("id", ""), ("synthetic", "true"),
    ("tags", ["ok", "ok"]), ("tags", [None]), ("title", "bad\u2014title"),
    ("title", "bad\ncontrol"), ("unknown", 1),
])
def test_rejects_adversarial_values(field, value):
    record = deepcopy(tiny_records()[0])
    record[field] = value
    with pytest.raises(VaultError, match="SchemaError"):
        build_result([record])


def test_duplicate_ids_rejected():
    with pytest.raises(VaultError, match="duplicate"):
        build_result([tiny_records()[0]] * 2)


def test_handles_unicode_and_long_inputs():
    record = tiny_records()[-1]
    record["title"] = "文件 café " * 1000
    record["path"] = "C:\\Henry's Documents\\文件.pdf"
    result = build_result([record])
    assert search(result["records"], "CAFÉ") == result["records"]
    assert search(result["records"], "文件", "SCHOOL") == result["records"]
    assert not search(result["records"], "finance")


def test_expiry_boundaries_and_count_reconciliation():
    dates = ["2026-09-29", "2026-09-30", "2026-10-30", "2026-10-31", None]
    records = tiny_records()
    for record, expiry in zip(records, dates):
        record["expires_on"] = expiry
    figures = build_result(records)["figures"]
    assert [figures[key] for key in ("expired_count", "upcoming_count", "current_count", "no_expiry_count")] == [1, 2, 1, 1]
    assert sum(figures[key] for key in ("expired_count", "upcoming_count", "current_count", "no_expiry_count")) == 5


def test_corrupted_fixture_changes_computed_figures():
    original = fixture_records()
    changed = deepcopy(original)
    changed[0]["expires_on"] = None
    changed[0]["amount_minor"] += 7
    before, after = build_result(original), build_result(changed)
    assert after["figures"]["expired_count"] == before["figures"]["expired_count"] - 1
    assert after["figures"]["declared_amount_total_gbp_pence"] == before["figures"]["declared_amount_total_gbp_pence"] + 7
    assert "DOC-001" not in after["cases"]["expired_ids"]


def test_core_does_not_mutate_inputs():
    records = tiny_records()
    copy = deepcopy(records)
    build_result(records)
    assert records == copy
