import json

from personal_document_vault.cli import generate, load_input
from personal_document_vault.core import build_result
from personal_document_vault.fixtures import expectations, fixture_records


def test_fixtures_labelled_synthetic(tmp_path):
    generate(tmp_path / "demo")
    files = list((tmp_path / "demo").rglob("*.json"))
    assert len(files) == 3
    for file in files:
        data = json.loads(file.read_text(encoding="utf-8"))
        assert data["synthetic"] is True
        assert "SYNTHETIC" in data["_label"]
        assert all(record["synthetic"] for record in data.get("records", []))
    assert load_input(tmp_path / "demo" / "tiny", "2026-09-30")["figures"]["total_records"] == 5


def test_fixture_ground_truth_matches_hand_computed():
    result, expected = build_result(fixture_records()), expectations()
    assert result["figures"] == expected["figures"]
    assert result["cases"] == expected["cases"]
    assert result["figures"]["declared_amount_total_gbp_pence"] == 50 * (100 + 200 + 300 + 400)


def test_fixture_generation_byte_identical(tmp_path):
    generate(tmp_path / "one")
    generate(tmp_path / "two")
    for path in (tmp_path / "one").rglob("*.json"):
        assert path.read_bytes() == (tmp_path / "two" / path.relative_to(tmp_path / "one")).read_bytes()
