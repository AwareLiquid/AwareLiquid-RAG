"""Tests for scripts/check_results_refs.py (the RESULTS.md evidence gate).

The script is loaded by file path (scripts/ is not a package); every test
builds a fake repository under ``tmp_path`` so the checks stay hermetic and
offline.
"""

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO_ROOT / "scripts" / "check_results_refs.py"

_spec = importlib.util.spec_from_file_location("check_results_refs", _SCRIPT)
check_results_refs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_results_refs)


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(tmp_path: Path, results_text: str, extra_files=None):
    """Build a fake repo with RESULTS.md and run the checks against it."""
    _write(tmp_path / "docs" / "RESULTS.md", results_text)
    for rel, content in (extra_files or {}).items():
        _write(tmp_path / rel, content)
    return check_results_refs.run_checks(tmp_path / "docs" / "RESULTS.md", tmp_path)


def test_pass_when_all_evidence_present(tmp_path):
    packet_rel = "docs/runs/run-1/packet.json"
    packet = _write(tmp_path / packet_rel, '{"ok": true}\n')
    _write(tmp_path / "docs/runs/run-1/model-probe.json", "{}\n")
    _write(tmp_path / "docs/runs/run-1/E-1/prompt.md", "prompt text\n")
    _write(
        tmp_path / "docs/runs/run-1/packet.json.sha256",
        "{}  packet.json\n".format(_sha256_of(packet)),
    )
    manifest = {
        "artifacts": [
            packet_rel,
            str(tmp_path / "docs/runs/run-1/model-probe.json"),  # absolute, inside repo
            "/tmp/awareliquid-verification/run-1/A-1.md",  # outside repo -> skipped
        ],
        "prompts": {"E-1": {"path": "docs/runs/run-1/E-1/prompt.md"}},
    }
    _write(tmp_path / "docs/runs/run-1/manifest.json", json.dumps(manifest))

    results_text = "\n".join(
        [
            "# Results",
            "See `README.md` and `docs/RESULTS.md` (self) and `pyproject.toml`.",
            "Data: `benchmarks/results/summary.csv:12-20`.",
            "Rerun with `python scripts/check_results_refs.py`.",
            "Bare name: `RESULTS.md`.",
        ]
    )
    code, report = _run(
        tmp_path,
        results_text,
        extra_files={
            "README.md": "# demo\n",
            "pyproject.toml": "[project]\n",
            "benchmarks/results/summary.csv": "metric,value\n",
            "scripts/check_results_refs.py": "# fake\n",
        },
    )

    assert code == 0
    assert report.rstrip().endswith("PASS")
    assert "FAIL" not in report
    assert "SKIP" in report  # /tmp artifact reported as skipped, not failed
    assert "resolved by basename" in report  # bare `RESULTS.md` -> docs/RESULTS.md


def test_missing_reference_fails_and_lists_path(tmp_path):
    code, report = _run(
        tmp_path,
        "See `benchmarks/results/missing.csv` and the typo `RESULT.md`.\n",
        extra_files={"docs/plans/note.md": "x\n"},  # so the basename index is non-trivial
    )

    assert code == 1
    assert "FAIL: 2 problems" in report
    assert "benchmarks/results/missing.csv" in report
    assert "`RESULT.md`" in report


def test_missing_results_document_exit_2(tmp_path):
    code, report = check_results_refs.run_checks(tmp_path / "docs" / "RESULTS.md", tmp_path)

    assert code == 2
    assert "not found" in report
    assert "FAIL" not in report and "PASS" not in report


def test_sidecar_hash_mismatch_fails(tmp_path):
    packet = _write(tmp_path / "docs/runs/run-1/packet.json", '{"ok": true}\n')
    assert _sha256_of(packet) != "0" * 64
    _write(tmp_path / "docs/runs/run-1/packet.json.sha256", "{}  packet.json\n".format("0" * 64))

    code, report = _run(tmp_path, "Evidence: `docs/runs/run-1/packet.json`.\n")

    assert code == 1
    assert "sha256 mismatch" in report
    assert "FAIL: 1 problems" in report


def test_sidecar_with_missing_target_fails(tmp_path):
    _write(tmp_path / "docs/runs/run-1/packet.json.sha256", "{}  packet.json\n".format("0" * 64))

    code, report = _run(tmp_path, "Evidence: `docs/runs/run-1/packet.json.sha256`.\n")

    assert code == 1
    assert "target file missing" in report


def test_manifest_missing_artifact_fails(tmp_path):
    manifest = {
        "artifacts": ["docs/runs/run-1/gone.json"],
        "prompts": {"E-1": {"path": "docs/runs/run-1/E-1/ghost-prompt.md"}},
    }
    _write(tmp_path / "docs/runs/run-1/manifest.json", json.dumps(manifest))

    code, report = _run(tmp_path, "Run 1 evidence in `docs/runs/run-1/manifest.json`.\n")

    assert code == 1
    assert "gone.json" in report
    assert "ghost-prompt.md" in report
    assert "FAIL: 2 problems" in report


def test_run_dir_without_manifest_is_listed_not_silent(tmp_path):
    _write(tmp_path / "docs/runs/run-stray/baseline.txt", "stray\n")

    code, report = _run(tmp_path, "No runs cited here.\n")

    assert code == 0
    assert "run-stray" in report
    assert "no manifest.json" in report
    assert "SKIP" in report


def test_ambiguous_bare_name_fails_instead_of_silent_match(tmp_path):
    _write(tmp_path / "docs/plans/note.md", "one\n")
    _write(tmp_path / "docs/runs/elsewhere/note.md", "two\n")

    code, report = _run(tmp_path, "Cites bare `note.md`.\n")

    assert code == 1
    assert "ambiguous bare name" in report
    assert "docs/plans/note.md" in report and "docs/runs/elsewhere/note.md" in report


def test_line_number_suffix_is_stripped(tmp_path):
    code, report = _run(
        tmp_path,
        "Config: `pyproject.toml:42` and range `pyproject.toml:1,4-9`.\n",
        extra_files={"pyproject.toml": "[project]\n"},
    )

    assert code == 0
    assert report.rstrip().endswith("PASS")
    assert "checked as pyproject.toml" in report


def test_cli_exit_2_when_results_missing(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(tmp_path / "nope" / "RESULTS.md")],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 2
    assert "not found" in proc.stdout
