import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from personal_document_vault.cli import atomic_write, generate, main
from personal_document_vault.core import VaultError
from personal_document_vault.fixtures import LABEL, tiny_records
from personal_document_vault.report import json_text


def setup_demo(tmp_path):
    demo, state = tmp_path / "demo", tmp_path / "state.json"
    generate(demo)
    assert main(["run", "--input", str(demo), "--state", str(state)]) == 0
    return demo, state


def test_run_completes_on_fixture(tmp_path, capsys):
    start = time.perf_counter()
    _, state = setup_demo(tmp_path)
    assert main(["report", "--format", "md", "--state", str(state)]) == 0
    assert time.perf_counter() - start < 5
    assert "DATA PROVENANCE" in capsys.readouterr().out


def test_cli_smoke_all_subcommands(tmp_path, capsys):
    demo, state = tmp_path / "demo", tmp_path / "state.json"
    assert main(["fixtures", "--out", str(demo)]) == 0
    assert main(["run", "--input", str(demo), "--state", str(state)]) == 0
    capsys.readouterr()
    for format in ("md", "json"):
        assert main(["report", "--format", format, "--state", str(state)]) == 0
        capsys.readouterr()
    assert main(["search", "--query", "renewal", "--state", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["match_count"] == 40
    assert main(["show", "--id", "DOC-001", "--state", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["records"][0]["id"] == "DOC-001"
    for command in ("fixtures", "run", "report", "search", "show"):
        with pytest.raises(SystemExit) as exit_info:
            main([command, "--help"])
        assert exit_info.value.code == 0
        assert "Example:" in capsys.readouterr().out


def test_determinism_byte_identical(tmp_path, capsys):
    demo, state = setup_demo(tmp_path)
    before = state.read_bytes()
    capsys.readouterr()
    assert main(["report", "--format", "json", "--state", str(state)]) == 0
    report = capsys.readouterr().out
    assert main(["run", "--input", str(demo), "--state", str(state)]) == 0
    assert state.read_bytes() == before
    capsys.readouterr()
    assert main(["report", "--format", "json", "--state", str(state)]) == 0
    assert capsys.readouterr().out == report


def test_malformed_input_named_error(tmp_path, capsys):
    (tmp_path / "bad.json").write_text('{\n "records": broken\n}', encoding="utf-8")
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "ParseError: bad.json: line 2" in error
    assert "Traceback" not in error


def test_empty_directory_cli(tmp_path, capsys):
    state = tmp_path / "cache" / "state.json"
    assert main(["run", "--input", str(tmp_path), "--state", str(state)]) == 0
    assert main(["report", "--state", str(state)]) == 0
    assert "total_records | 0" in capsys.readouterr().out


def test_missing_input_and_state(tmp_path, capsys):
    assert main(["run", "--input", str(tmp_path / "missing")]) == 2
    assert "MissingInput" in capsys.readouterr().err
    assert main(["report", "--state", str(tmp_path / "missing")]) == 2
    assert "MissingState" in capsys.readouterr().err


def test_schema_error_names_file_and_field(tmp_path, capsys):
    record = tiny_records()[0]
    del record["category"]
    (tmp_path / "records.json").write_text(json_text({"_label": LABEL, "synthetic": True, "records": [record]}), encoding="utf-8")
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "SchemaError" in error and "records.json" in error and "category" in error


def test_report_write_failure_no_partial_files(tmp_path, capsys):
    _, state = setup_demo(tmp_path)
    destination = tmp_path / "existing-directory"
    destination.mkdir()
    assert main(["report", "--state", str(state), "--out", str(destination)]) == 2
    assert "WriteError" in capsys.readouterr().err
    assert not list(tmp_path.glob(".pdv-write-*.tmp"))
    assert not list(destination.iterdir())


def test_failed_run_preserves_last_good_snapshot(tmp_path, capsys):
    demo, state = setup_demo(tmp_path)
    before = state.read_bytes()
    (demo / "bad.json").write_text("{", encoding="utf-8")
    assert main(["run", "--input", str(demo), "--state", str(state)]) == 2
    assert before == state.read_bytes()


def test_cli_computes_from_modified_input_not_expectations(tmp_path, capsys):
    demo, state = setup_demo(tmp_path)
    file = demo / "records.json"
    data = json.loads(file.read_text(encoding="utf-8"))
    data["records"][0]["expires_on"] = None
    file.write_text(json_text(data), encoding="utf-8")
    (demo / "expectations.json").write_text('{"fake": 999999}', encoding="utf-8")
    assert main(["run", "--input", str(demo), "--state", str(state)]) == 0
    capsys.readouterr()
    assert main(["report", "--format", "json", "--state", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["figures"]["expired_count"] == 19


@pytest.mark.parametrize("text", ['{"synthetic": true, "synthetic": false, "records": []}', '{"synthetic": true, "records": [NaN]}'])
def test_ambiguous_json_rejected(tmp_path, capsys, text):
    (tmp_path / "bad.json").write_text(text, encoding="utf-8")
    assert main(["run", "--input", str(tmp_path)]) == 2
    assert "ParseError" in capsys.readouterr().err


def test_subprocess_entrypoint(tmp_path):
    project = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-m", "personal_document_vault.cli", "fixtures", "--out", str(tmp_path / "demo")], cwd=project, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "SYNTHETIC" in result.stdout


def test_real_input_provenance(tmp_path, capsys):
    record = tiny_records()[0]
    record["synthetic"] = False
    (tmp_path / "records.json").write_text(json_text({"synthetic": False, "records": [record]}), encoding="utf-8")
    state = tmp_path / "state" / "result.json"
    assert main(["run", "--input", str(tmp_path), "--state", str(state)]) == 0
    assert "0 synthetic fixture records; 1 user-declared real records" in capsys.readouterr().out


def test_deeply_nested_json_named_error(tmp_path, capsys):
    (tmp_path / "nested.json").write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "nested.json" in error and "Error:" in error and "Traceback" not in error


def test_snapshot_totals_cannot_override_records(tmp_path, capsys):
    _, state = setup_demo(tmp_path)
    data = json.loads(state.read_text(encoding="utf-8"))
    data["figures"]["expired_count"] = 999
    state.write_text(json_text(data), encoding="utf-8")
    capsys.readouterr()
    assert main(["report", "--format", "json", "--state", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["figures"]["expired_count"] == 20


def test_atomic_write_preserves_previous_file_on_failure(tmp_path, monkeypatch):
    destination = tmp_path / "report.md"
    destination.write_text("old report", encoding="utf-8")
    def fail_replace(*args):
        raise PermissionError(13, "permission denied")
    monkeypatch.setattr("personal_document_vault.cli.os.replace", fail_replace)
    with pytest.raises(VaultError, match="WriteError"):
        atomic_write(destination, "new report")
    assert destination.read_text(encoding="utf-8") == "old report"
    assert not list(tmp_path.glob(".pdv-write-*.tmp"))


def test_cli_unicode_subprocess_roundtrip(tmp_path):
    project = Path(__file__).resolve().parents[1]
    generate(tmp_path / "demo")
    state = tmp_path / "state.json"
    prefix = [sys.executable, "-m", "personal_document_vault.cli"]
    run = subprocess.run(prefix + ["run", "--input", str(tmp_path / "demo" / "tiny"), "--state", str(state)], cwd=project, capture_output=True)
    assert run.returncode == 0, run.stderr
    shown = subprocess.run(prefix + ["show", "--id", "T5", "--state", str(state)], cwd=project, capture_output=True)
    assert shown.returncode == 0, shown.stderr
    assert json.loads(shown.stdout.decode("utf-8"))["records"][0]["title"] == "Synthetic café 文件"


def test_fixture_overwrite_refused(tmp_path, capsys):
    destination = tmp_path / "existing"
    destination.mkdir()
    original = destination / "mine.txt"
    original.write_text("keep me", encoding="utf-8")
    assert main(["fixtures", "--out", str(destination)]) == 2
    assert "WriteError" in capsys.readouterr().err
    assert original.read_text(encoding="utf-8") == "keep me"
