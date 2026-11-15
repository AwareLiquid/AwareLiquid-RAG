#!/usr/bin/env python3
"""Machine-check the evidence references in docs/RESULTS.md.

docs/RESULTS.md is the single source of truth for experiment evidence. This
script (pure standard library, python>=3.9, offline) makes those claims
machine-checkable instead of "governance by self-discipline":

1. Every backtick token in RESULTS.md that looks like a repository-relative
   path (known extension, optional ``:LINE`` suffix such as ``file.md:12-20``)
   must exist at the repository root. Tokens shaped like commands (e.g.
   ``python scripts/check_results_refs.py``) are judged by their path
   component; bare filenames (e.g. ``README.md``) are checked at the root and
   otherwise resolved by basename search — which must be **unique**: an
   ambiguous bare name is reported as a failure, not silently matched.
2. Every run directory under ``docs/runs/``:
   a. ``manifest.json``: every ``artifacts`` entry that lives inside the
      repository must exist (paths outside the repo, e.g. ``/tmp/...``, are
      skipped with a note); every ``prompts[*].path`` must exist too.
   b. every ``*.sha256`` sidecar (sha256sum "HEX<SP><SP>name" format) must
      match the actual sha256 of its target file.

Exit codes: 0 = PASS, 1 = FAIL (problems listed), 2 = results document
missing or bad usage. There are no exceptions/allowlists: any referenced path
that cannot be found is reported as a failure.

Usage::

    python scripts/check_results_refs.py [path-to-results-md]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

DEFAULT_RESULTS_RELATIVE = "docs/RESULTS.md"
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]

KNOWN_EXTENSIONS = (
    ".md",
    ".py",
    ".json",
    ".jsonl",
    ".csv",
    ".log",
    ".txt",
    ".toml",
    ".sh",
    ".yml",
    ".yaml",
)

# A backtick-delimited span on a single line.
_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
# Token body: repo-path characters, optionally followed by a ":N" line-number
# suffix (ranges/lists such as ":12-20" or ":1,4,9" are tolerated too).
_TOKEN_BODY_RE = re.compile(r"^[A-Za-z0-9_\-./ ]+(?::\d[\d,\-]*)?$")
_LINE_SUFFIX_RE = re.compile(r":\d[\d,\-]*$")
# sha256sum sidecar line: "<64 hex digits><ws><[*]name>".
_SIDECAR_LINE_RE = re.compile(r"^([0-9a-fA-F]{64})[ \t]+\*?(.+?)\s*$")

# Directories never descended into when building the basename index used to
# resolve bare filenames. Direct path checks never use this index, so these
# exclusions cannot hide a genuinely missing referenced file.
_INDEX_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".idea",
    ".vscode",
    "node_modules",
    "downloads",
    "output",
}


def _sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _show_candidates(candidates: List[str]) -> str:
    shown = "; ".join(sorted(candidates)[:4])
    if len(candidates) > 4:
        shown += "; ..."
    return shown


def iter_reference_tokens(text: str) -> Iterable[Tuple[str, str]]:
    """Yield ``(raw_token, path)`` pairs for every repo-path-like backtick token.

    ``raw_token`` is the untouched backtick content (for reporting), ``path``
    is the token after stripping the ``:N`` line-number suffix and rejecting
    absolute paths / URLs / unknown extensions.
    """
    seen = set()
    for match in _BACKTICK_RE.finditer(text):
        raw = match.group(1).strip()
        if not raw or not _TOKEN_BODY_RE.fullmatch(raw):
            continue
        path = _LINE_SUFFIX_RE.sub("", raw).strip()
        if not path or path.startswith("/") or "://" in path:
            continue
        if not path.lower().endswith(KNOWN_EXTENSIONS):
            continue
        if path in seen:
            continue
        seen.add(path)
        yield raw, path


def resolve_manifest_entry(raw: str, repo_root: Path) -> Tuple[Optional[Path], str]:
    """Map a manifest path onto the local checkout.

    Returns ``(path, note)``. ``path`` is None when the entry cannot be
    verified here (outside the repository, e.g. ``/tmp/...``); ``note`` then
    says why. Absolute paths that embed the repository directory name are
    remapped onto the local checkout so the gate still works when CI checks
    the repo out at a different location.
    """
    p = raw.strip()
    if not p:
        return None, "empty path"
    candidate = Path(p)
    if not candidate.is_absolute():
        return repo_root / candidate, ""
    try:
        candidate.resolve().relative_to(repo_root)
        return candidate, ""
    except ValueError:
        pass
    parts = candidate.parts
    if repo_root.name in parts:
        i = len(parts) - 1 - parts[::-1].index(repo_root.name)
        tail = parts[i + 1 :]
        if tail:
            return repo_root.joinpath(*tail), "remapped"
        return None, "outside repository"
    return None, "outside repository"


class Checker:
    """Accumulates OK/FAIL/SKIP lines and counts problems."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.problems = 0
        self.lines: List[str] = []
        self.n_refs = 0
        self.n_manifest_paths = 0
        self.n_sidecar_entries = 0
        self._basename_index: Optional[Dict[str, List[str]]] = None

    # ------------------------------------------------------------------ #
    # report helpers
    # ------------------------------------------------------------------ #
    def _add(self, status: str, label: str, detail: str = "") -> None:
        line = "%-4s %s" % (status, label)
        if detail:
            line += "  ({})".format(detail)
        self.lines.append(line)

    def ok(self, label: str, detail: str = "") -> None:
        self._add("OK", label, detail)

    def skip(self, label: str, detail: str = "") -> None:
        self._add("SKIP", label, detail)

    def fail(self, label: str, detail: str = "") -> None:
        self.problems += 1
        self._add("FAIL", label, detail)

    def _rel(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.repo_root))
        except ValueError:
            return str(path)

    # ------------------------------------------------------------------ #
    # 1. references inside the results document
    # ------------------------------------------------------------------ #
    def check_results_references(self, results_path: Path) -> None:
        self.lines.append("== evidence references in {} ==".format(self._rel(results_path)))
        text = results_path.read_text(encoding="utf-8", errors="replace")
        tokens = list(iter_reference_tokens(text))
        for token, path in tokens:
            self.check_reference(token, path)
        if not tokens:
            self.skip(
                "(no repository-path tokens found)",
                "the results document contains no checkable path references",
            )

    def check_reference(self, token: str, path: str) -> None:
        self.n_refs += 1
        resolved, detail = self._locate(path)
        if resolved is None:
            self.fail("`{}`".format(token), detail or "referenced path not found in repository")
            return
        if detail is None:
            detail = "" if token == path else "checked as {}".format(path)
        self.ok("`{}`".format(token), detail)

    def _locate(self, path: str) -> Tuple[Optional[str], Optional[str]]:
        """Resolve one reference; returns ``(checked_path_or_None, detail)``.

        Tried in order: the verbatim path; the last whitespace-separated
        component of command-shaped tokens (``python scripts/x.py``); a
        basename search for bare filenames (``README.md``). A bare name is
        only accepted when it is **unique** in the repository — an ambiguous
        bare name returns ``None`` with an "ambiguous" detail so the caller
        reports a failure instead of silently checking an arbitrary match.
        """
        if (self.repo_root / path).exists():
            return path, None
        if " " in path:
            tail = path.split()[-1]
            if tail and tail != path:
                if (self.repo_root / tail).exists():
                    return tail, "command token; checked as {}".format(tail)
                if "/" not in tail:
                    candidates = self._resolve_bare_name(tail)
                    if len(candidates) == 1:
                        return candidates[0], "command token; resolved by basename: {}".format(
                            candidates[0]
                        )
                    if candidates:
                        return None, "ambiguous bare name in command token: {}".format(
                            _show_candidates(candidates)
                        )
        if "/" not in path:
            candidates = self._resolve_bare_name(path)
            if len(candidates) == 1:
                return candidates[0], "resolved by basename: {}".format(candidates[0])
            if candidates:
                return None, "ambiguous bare name ({} matches): {}".format(
                    len(candidates), _show_candidates(candidates)
                )
        return None, None

    def _resolve_bare_name(self, name: str) -> List[str]:
        index = self._basename_index
        if index is None:
            index = self._basename_index = self._build_basename_index()
        return sorted(index.get(name, []))

    def _build_basename_index(self) -> Dict[str, List[str]]:
        index: Dict[str, List[str]] = {}
        for dirpath, dirnames, filenames in os.walk(self.repo_root):
            dirnames[:] = sorted(
                d
                for d in dirnames
                if d not in _INDEX_EXCLUDED_DIRS and not d.endswith(".egg-info")
            )
            for filename in filenames:
                rel = os.path.relpath(os.path.join(dirpath, filename), self.repo_root)
                index.setdefault(filename, []).append(rel)
        return index

    # ------------------------------------------------------------------ #
    # 2. docs/runs/ manifests + sha256 sidecars
    # ------------------------------------------------------------------ #
    def check_runs(self) -> None:
        self.lines.append("")
        self.lines.append("== docs/runs/: manifest paths & sha256 sidecars ==")
        runs_root = self.repo_root / "docs" / "runs"
        if not runs_root.is_dir():
            self.skip("docs/runs/", "directory not present")
            return
        run_dirs = sorted(p for p in runs_root.iterdir() if p.is_dir())
        for run_dir in run_dirs:
            if (run_dir / "manifest.json").is_file():
                self.check_manifest(run_dir)
            else:
                # 显式列出而非静默跳过：门禁绿灯的覆盖范围必须可从输出读出
                self.skip(
                    "[{}] no manifest.json".format(run_dir.name),
                    "run directory without a manifest is not machine-checkable",
                )
            for sidecar in sorted(run_dir.rglob("*.sha256")):
                self.check_sidecar(sidecar)

    def check_manifest(self, run_dir: Path) -> None:
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.is_file():
            return
        run_label = "[{}]".format(run_dir.name)
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            self.fail("{} manifest.json".format(run_label), "cannot read/parse: {}".format(exc))
            return
        if not isinstance(manifest, dict):
            self.fail("{} manifest.json".format(run_label), "top-level JSON is not an object")
            return

        artifacts = manifest.get("artifacts", [])
        if not isinstance(artifacts, list):
            self.fail("{} manifest.json".format(run_label), "'artifacts' is not a list")
            artifacts = []
        for raw in artifacts:
            if not isinstance(raw, str):
                self.fail("{} artifact".format(run_label), "non-string artifact path")
                continue
            self.n_manifest_paths += 1
            path, note = resolve_manifest_entry(raw, self.repo_root)
            if path is None:
                self.skip("{} artifact {}".format(run_label, raw), note)
                continue
            display = self._rel(path)
            if path.exists():
                self.ok("{} artifact".format(run_label), display)
            else:
                self.fail("{} artifact".format(run_label), "missing: {}".format(display))

        prompts = manifest.get("prompts", {})
        if not isinstance(prompts, dict):
            self.fail("{} manifest.json".format(run_label), "'prompts' is not an object")
            prompts = {}
        for key in sorted(prompts):
            entry = prompts[key]
            self.n_manifest_paths += 1
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                self.fail(
                    "{} prompt {}".format(run_label, key),
                    "prompt entry has no string 'path'",
                )
                continue
            path, note = resolve_manifest_entry(entry["path"], self.repo_root)
            if path is None:
                self.skip(
                    "{} prompt {}: {}".format(run_label, key, entry["path"]), note
                )
                continue
            display = self._rel(path)
            if path.exists():
                self.ok("{} prompt {}".format(run_label, key), display)
            else:
                self.fail("{} prompt {}".format(run_label, key), "missing: {}".format(display))

    def check_sidecar(self, sidecar: Path) -> None:
        label = self._rel(sidecar)
        try:
            text = sidecar.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self.fail(label, "cannot read: {}".format(exc))
            return
        entries = 0
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            entries += 1
            match = _SIDECAR_LINE_RE.match(line)
            if match is None:
                self.fail(label, "malformed line: {!r}".format(line[:80]))
                continue
            expected, name = match.group(1).lower(), match.group(2).strip()
            target = Path(name)
            if not target.is_absolute():
                target = sidecar.parent / target
            if not target.is_file():
                self.fail("{} -> {}".format(label, name), "target file missing")
                continue
            actual = _sha256_of_file(target)
            if actual == expected:
                self.ok("{} -> {}".format(label, name))
            else:
                self.fail(
                    "{} -> {}".format(label, name),
                    "sha256 mismatch: expected {}, got {}".format(expected, actual),
                )
        self.n_sidecar_entries += entries
        if entries == 0:
            self.fail(label, "no checksum entries found")


def run_checks(results_path, repo_root=None) -> Tuple[int, str]:
    """Run every check; returns ``(exit_code, report_text)``.

    Exit codes: 0 PASS, 1 FAIL, 2 results document missing.
    """
    root = Path(repo_root).resolve() if repo_root is not None else DEFAULT_REPO_ROOT
    results = Path(results_path)
    if not results.is_file():
        report = "\n".join(
            [
                "ERROR: results document not found: {}".format(results),
                "Expected the single source of truth at '{}' relative to the repository".format(
                    DEFAULT_RESULTS_RELATIVE
                ),
                "root, or pass an explicit path: python scripts/check_results_refs.py <path>",
            ]
        )
        return 2, report

    checker = Checker(root)
    checker.check_results_references(results)
    checker.check_runs()
    summary = "checked: {} references, {} manifest paths, {} sidecar entries".format(
        checker.n_refs, checker.n_manifest_paths, checker.n_sidecar_entries
    )
    if checker.problems:
        return 1, "\n".join(checker.lines + [summary, "FAIL: {} problems".format(checker.problems)])
    return 0, "\n".join(checker.lines + [summary, "PASS"])


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_results_refs.py",
        description="Machine-check evidence references in docs/RESULTS.md (stdlib only, offline).",
    )
    parser.add_argument(
        "results",
        nargs="?",
        default=None,
        help="path to the results document (default: {})".format(DEFAULT_RESULTS_RELATIVE),
    )
    args = parser.parse_args(argv)
    results_path = (
        Path(args.results) if args.results else DEFAULT_REPO_ROOT / DEFAULT_RESULTS_RELATIVE
    )
    code, report = run_checks(results_path, DEFAULT_REPO_ROOT)
    print(report)
    return code


if __name__ == "__main__":
    sys.exit(main())
