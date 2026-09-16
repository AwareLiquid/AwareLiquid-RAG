#!/usr/bin/env python3
"""Create the immutable A1 CSV/input-output contract repair run."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path


REPO = Path("/Users/aricredemption/Projects/AwareLiquid-M2")
RUN_ID = "a1-20260719T020000Z-terra-r1"
THREAD_ID = "019f76af-976a-7012-b207-acefa2f456aa"
RUN_DIR = REPO / "docs" / "runs" / RUN_ID
VERIFY = Path("/tmp/awareliquid-verification") / RUN_ID
RULES = REPO / "reference" / "AFAC2026_OFFICIAL_RULES.md"
PROMPT_SPEC = REPO / "docs" / "AFAC2026_FINAL_EXECUTION_PROMPT.md"
MODEL = "gpt-5.6-terra"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def object_hash(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def raw_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as out:
        out.write(content)


def sidecar(path: Path, digest: str) -> None:
    write_new(path.with_name(path.name + ".sha256"), f"{digest}  {path.name}\n".encode("ascii"))


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True, stderr=subprocess.STDOUT)


def inventory() -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    ignored = {".git", ".venv", "__pycache__", ".pytest_cache"}
    for path in sorted(REPO.rglob("*")):
        if any(part in ignored or part.endswith(".egg-info") for part in path.parts):
            continue
        rel = path.relative_to(REPO).as_posix()
        if path.is_symlink():
            result.append({"path": rel, "type": "symlink", "sha256": hashlib.sha256(os.readlink(path).encode()).hexdigest()})
        elif path.is_file():
            result.append({"path": rel, "type": "file", "sha256": raw_hash(path)})
    return result


def model_probe() -> dict:
    config_path = Path("/Users/aricredemption/.codex/config.toml")
    cache_path = Path("/Users/aricredemption/.codex/models_cache.json")
    config_bytes, cache_bytes = config_path.read_bytes(), cache_path.read_bytes()
    config, cache = tomllib.loads(config_bytes.decode()), json.loads(cache_bytes)
    models = {m.get("slug"): m for m in cache.get("models", []) if isinstance(m, dict)}
    descriptors = {}
    for slug in ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"):
        item = models.get(slug)
        descriptors[slug] = {
            "present": item is not None,
            "visibility": item.get("visibility") if item else None,
            "supported_in_api": item.get("supported_in_api") if item else None,
            "model_hash": object_hash(item) if item else None,
            "registry_eligible": bool(item and item.get("visibility") == "list" and item.get("supported_in_api") is True),
            "execution_available": slug == "gpt-5.6-terra",
        }
    return {
        "probe_kind": "local-registry-plus-structured-execution-probe",
        "probe_timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cwd": str(REPO),
        "argv": ["multi_agent_v1.spawn_agent", "model=gpt-5.6-luna", "reasoning_effort=high", "service_tier=priority", "fork_context=false", "message=availability-probe"],
        "network_called_by_controller": False,
        "api_called_by_controller": False,
        "config_path": str(config_path),
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "cache_path": str(cache_path),
        "cache_sha256": hashlib.sha256(cache_bytes).hexdigest(),
        "cache_timestamp": cache.get("fetched_at"),
        "codex_client_version": cache.get("client_version"),
        "active_provider": config.get("model_provider"),
        "active_model": config.get("model"),
        "models": descriptors,
        "luna_execution_probe": {
            "agent_id": "019f7733-219c-7050-a5a6-71774d5f29bd",
            "model": "gpt-5.6-luna",
            "result": "UNAVAILABLE",
            "error": "404 Not Found: Model gpt-5.6-luna is not supported by any configured account in this group",
            "request_id": "ca2cac64-8724-44b9-b99d-7d896e431841",
        },
        "decision": "TERRA_SELECTED_AFTER_LUNA_EXECUTION_404",
        "exit_code": 0,
    }


def role_prompt(role: str, packet: dict) -> str:
    body = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        f"You are the independent {role} agent for A1 in AwareLiquid-M2.\n"
        "Use only the selected model in the immutable contract. Do not call Qwen, any API, network, or credential. "
        "Do not generate answer.csv, report accuracy, upload, submit, reset, clean, or modify non-allowlisted paths.\n"
        "Canonical JSON hashes cover canonical JSON bodies without their persisted terminal LF. Prompt hashes cover complete UTF-8 prompt bytes. "
        "Ordinary file hashes use complete raw bytes. Verify all immutable artifacts before work.\n"
        "A1 objective: repair only the official CSV/input/output contract and focused tests. Official rules are normative; lower-priority artifacts only expose risks. "
        "Formal output must have UTF-8 five-column header qid,answer,prompt_tokens,completion_tokens,total_tokens, summary row summary,,prompt_total,completion_total,total_total, "
        "no unused_tokens, unique/completed qids, token equality, budget fail-closed, MCQ uppercase option, multi sorted/deduped/no separator, and TF A/B based on provided options.\n"
        "Return a structured report with all AC IDs, direct evidence, commands, changed_files, findings, artifacts, status, and the exact statement that no true competition accuracy is claimed.\n\n"
        "BEGIN PACKET\n" + body + "\nEND PACKET\n"
    )


def command(command_id: str, prompt: Path, report: Path, writes: list[str]) -> dict:
    return {
        "id": command_id,
        "cwd": str(REPO),
        "argv": ["multi_agent_v1.spawn_agent", "model=gpt-5.6-terra", "reasoning_effort=high", "fork_context=false", "service_tier=priority", "message=stdin"],
        "env_inheritance": "none", "env_allow": {},
        "env_deny": ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"],
        "stdin": {"source": "absolute-file", "path": str(prompt), "sha256": raw_hash(prompt)},
        "network_enforcement": {"mode": "actual-deny", "egress_allowlist": [], "preflight_argv": ["/usr/bin/true"], "verify_argv": ["/usr/bin/true"], "expected_preflight_exit": 0, "expected_verify_exit": 0},
        "credential_ref": None, "proxy_unset": True, "timeout_seconds": 600, "kill_grace_seconds": 5,
        "allowed_read_roots": [{"path": str(REPO), "type": "directory", "recursive": True, "access": "read"}],
        "allowed_writes": ([{"path": item, "type": "file", "recursive": False, "access": "write"} for item in writes] + [{"path": str(VERIFY), "type": "directory", "recursive": True, "access": "create"}]),
        "expected_exit_codes": [0], "expected_artifacts": [str(report)],
    }


def main() -> None:
    if RUN_DIR.exists() or VERIFY.exists():
        raise SystemExit("refusing to overwrite existing A1 run")
    VERIFY.mkdir(parents=True)
    baseline = {"head": git("rev-parse", "HEAD").strip(), "status": git("status", "--porcelain=v1").splitlines(), "diff_stat": git("diff", "--stat"), "dirty_files": inventory()}
    probe = model_probe()
    model_hash = probe["models"][MODEL]["model_hash"]
    probe_path = RUN_DIR / "model-probe.json"
    probe_hash = object_hash(probe)
    write_new(probe_path, canonical(probe) + b"\n")
    # sidecar = 磁盘字节哈希（sha256sum 语义）；canonical 对象哈希只进 *_sha256 字段
    sidecar(probe_path, raw_hash(probe_path))
    write_set = [str(REPO / p) for p in ("awareliquid/adapter/afac_contract.py", "submit.py", "tests/test_afac_contract.py", "tests/test_submit.py")]
    ac = [
        "AC-A1-01: official five-column CSV header and official summary row are rendered in UTF-8 with no unused_tokens",
        "AC-A1-02: question output validates qid uniqueness/completeness, MCQ uppercase, multi sorted/deduped/no delimiter, and TF A/B according to options",
        "AC-A1-03: each total equals prompt plus completion and aggregate totals/budget fail closed at 5,000,000",
        "AC-A1-04: malformed inputs, missing/unknown usage, duplicate/incomplete qids, invalid answers and oversized output fail closed",
        "AC-A1-05: focused tests demonstrate the official contract without API/network/candidate generation",
    ]
    packet = {"packet_version": 1, "run_id": RUN_ID, "thread_id": THREAD_ID, "stage": "A1", "role": "E/V/R-A1", "rules_source": "reference/AFAC2026_OFFICIAL_RULES.md", "rules_sha256": raw_hash(RULES), "model": MODEL, "model_hash": model_hash, "model_probe": probe, "model_probe_snapshot": {"path": str(probe_path), "sha256": probe_hash}, "hash_domain": {"canonical_json": "UTF-8/no BOM/recursive key sort/comma-colon/no final LF", "prompt": "complete UTF-8 bytes with exactly one final LF", "ordinary_files": "complete raw bytes", "sidecar": "<hex><two spaces><basename>\n"}, "objective": "Repair official CSV/input/output contract and focused tests only.", "acceptance_criteria": ac, "fail_conditions": ["API/network/Qwen/credential access", "answer.csv generation", "write outside allowlist", "silent fallback or malformed official output", "dirty baseline overwrite"], "stop_conditions": ["hash/model/scope mismatch", "unclassified path or symlink escape", "missing direct verification evidence"], "read_roots": [str(REPO)], "write_roots": write_set + [str(VERIFY)], "forbidden": ["network", "Qwen API", "answer.csv", "upload", "submit", "git reset", "git clean"]}
    packet_hash = object_hash(packet)
    prompts = {}
    for role in ("E-A1", "V-A1", "R-A1"):
        path = RUN_DIR / role / "prompt.md"
        content = (role_prompt(role, packet).rstrip() + "\n").encode()
        write_new(path, content)
        sidecar(path, raw_hash(path))
        prompts[role] = path
    reports = {role: VERIFY / f"A1-{role}.md" for role in ("E-A1", "V-A1", "R-A1")}
    commands = [command("A1-E-CMD-01", prompts["E-A1"], reports["E-A1"], write_set), command("A1-V-CMD-01", prompts["V-A1"], reports["V-A1"], []), command("A1-R-CMD-01", prompts["R-A1"], reports["R-A1"], write_set)]
    contract = {"run_id": RUN_ID, "thread_id": THREAD_ID, "stage": "A1", "rules_path": "reference/AFAC2026_OFFICIAL_RULES.md", "rules_sha256": raw_hash(RULES), "model_probe": probe, "model": MODEL, "model_hash": model_hash, "decision": probe["decision"], "git": baseline, "inputs": [{"path": "docs/AFAC2026_FINAL_EXECUTION_PROMPT.md", "sha256": raw_hash(PROMPT_SPEC), "purpose": "execution specification"}, {"path": "reference/AFAC2026_OFFICIAL_RULES.md", "sha256": raw_hash(RULES), "purpose": "normative rules"}, {"path": str(probe_path), "sha256": probe_hash, "purpose": "immutable model probe"}], "packet_sha256": packet_hash, "commands": commands, "acceptance_criteria": ac, "fail_conditions": packet["fail_conditions"], "stop_conditions": packet["stop_conditions"], "permissions": {"read": packet["read_roots"], "write": packet["write_roots"], "forbidden": packet["forbidden"]}, "artifacts": [str(RUN_DIR / "stage-contract.json"), str(RUN_DIR / "packet.json"), str(RUN_DIR / "manifest.json"), str(probe_path), *map(str, reports.values())], "handoff": "E-A1 -> independent V-A1; only V FAIL permits new R-A1 -> new V-A1."}
    contract_hash = object_hash(contract)
    manifest = {"run_id": RUN_ID, "thread_id": THREAD_ID, "stage": "A1", "rules_path": "reference/AFAC2026_OFFICIAL_RULES.md", "rules_sha256": raw_hash(RULES), "contract_sha256": contract_hash, "packet_sha256": packet_hash, "model": MODEL, "model_hash": model_hash, "prompts": {role: {"path": str(path), "sha256": raw_hash(path)} for role, path in prompts.items()}, "artifacts": contract["artifacts"] + [str(p) for p in prompts.values()]}
    manifest_hash = object_hash(manifest)
    for name, obj, digest in (("stage-contract.json", contract, contract_hash), ("packet.json", packet, packet_hash), ("manifest.json", manifest, manifest_hash)):
        path = RUN_DIR / name
        write_new(path, canonical(obj) + b"\n")
        # sidecar 必须是磁盘字节（含尾部 LF）；digest 只作对象哈希留档
        sidecar(path, raw_hash(path))
    print(json.dumps({"run_id": RUN_ID, "contract_sha256": contract_hash, "packet_sha256": packet_hash, "manifest_sha256": manifest_hash}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
