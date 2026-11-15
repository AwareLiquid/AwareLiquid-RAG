#!/usr/bin/env python3
"""Create the immutable A4 exact-only reasoning run."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/Users/aricredemption/Projects/AwareLiquid-M2")
RUN_ID = "a4-20260719T230000Z-terra-r1"
THREAD = "019f76af-976a-7012-b207-acefa2f456aa"
RUN = REPO / "docs" / "runs" / RUN_ID
TMP = Path("/tmp/awareliquid-verification") / RUN_ID
RULES = REPO / "reference" / "AFAC2026_OFFICIAL_RULES.md"
SPEC = REPO / "docs" / "AFAC2026_FINAL_EXECUTION_PROMPT.md"
MODEL = "gpt-5.6-terra"


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def obj_hash(value):
    return hashlib.sha256(canon(value)).hexdigest()


def raw_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def create_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def sidecar(path, digest):
    create_new(str(path) + ".sha256", f"{digest}  {Path(path).name}\n".encode())


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True, stderr=subprocess.STDOUT)


def inventory():
    rows = []
    for path in sorted(REPO.rglob("*")):
        if any(part in {".git", ".venv", ".pytest_cache"} or part.endswith(".egg-info") for part in path.parts):
            continue
        rel = path.relative_to(REPO).as_posix()
        if path.is_symlink():
            rows.append({"path": rel, "type": "symlink", "sha256": hashlib.sha256(os.readlink(path).encode()).hexdigest()})
        elif path.is_file():
            rows.append({"path": rel, "type": "file", "sha256": raw_hash(path)})
    return rows


def probe():
    config_path = Path("/Users/aricredemption/.codex/config.toml")
    cache_path = Path("/Users/aricredemption/.codex/models_cache.json")
    config_bytes, cache_bytes = config_path.read_bytes(), cache_path.read_bytes()
    config, cache = tomllib.loads(config_bytes.decode()), json.loads(cache_bytes)
    by_slug = {item.get("slug"): item for item in cache.get("models", []) if isinstance(item, dict)}
    models = {}
    for slug in ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"):
        item = by_slug.get(slug)
        models[slug] = {
            "present": bool(item),
            "visibility": item.get("visibility") if item else None,
            "supported_in_api": item.get("supported_in_api") if item else None,
            "model_hash": obj_hash(item) if item else None,
            "registry_eligible": bool(item and item.get("visibility") == "list" and item.get("supported_in_api") is True),
            "execution_available": slug == MODEL,
        }
    return {
        "probe_kind": "local-registry-plus-structured-execution-probe",
        "probe_timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cwd": str(REPO),
        "argv": ["multi_agent_v1.spawn_agent", "model=gpt-5.6-luna", "reasoning_effort=high", "message=availability-probe"],
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
        "models": models,
        "luna_execution_probe": {
            "agent_id": "019f78c8-0b62-7712-84b9-2c246884783c",
            "model": "gpt-5.6-luna",
            "result": "UNAVAILABLE",
            "error": "404 Not Found: Model gpt-5.6-luna is not supported by any configured account in this group",
            "request_id": "0fc47436-e9e3-48a4-a82a-d8bec9f11ee0",
        },
        "decision": "TERRA_SELECTED_AFTER_LUNA_EXECUTION_404",
        "exit_code": 0,
    }


def prompt(role, packet):
    return (
        f"You are independent {role} for A4 in AwareLiquid-M2. Use only the contract-selected model. Verify immutable artifacts before work. No Qwen/API/network/credentials, candidates/answer.csv, uploads, submissions, or accuracy claims. A4 scope only: Evidence context preserving exact original text/boundaries; Decimal arithmetic using an explicit safe structural whitelist with no eval/exec; option states supported/refuted/insufficient; deterministic exact-only locator. Locator can use only exact doc_id/title/section/clause/phrase/numbers/dates/percent/currency/table fields/original position, must return stable original doc/page/char order, and A queries must fail closed unless their nonempty doc_ids scope is supplied. Prohibit BM25, RRF, vector/dense/hybrid, embedding, rerank, semantic filtering/truncation, synonyms, rewriting, option filtering. Never derive semantics from real A material in tests. Return AC evidence with no real accuracy claim.\n\nBEGIN PACKET\n{json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\nEND PACKET\n"
    )


def command(identifier, role, writes, report, preflight):
    return {
        "id": identifier,
        "cwd": str(REPO),
        "argv": ["multi_agent_v1.spawn_agent", "model=gpt-5.6-terra", "reasoning_effort=high", "fork_context=false", "service_tier=priority", "message=stdin"],
        "env_inheritance": "none",
        "env_allow": {},
        "env_deny": ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"],
        "stdin": {"source": "absolute-file", "path": str(RUN / role / "prompt.md"), "sha256": raw_hash(RUN / role / "prompt.md")},
        "network_enforcement": {"mode": "actual-deny", "egress_allowlist": [], "preflight_argv": preflight, "verify_argv": preflight, "expected_preflight_exit": 0, "expected_verify_exit": 0},
        "credential_ref": None, "proxy_unset": True, "timeout_seconds": 600, "kill_grace_seconds": 5,
        "allowed_read_roots": [{"path": str(REPO), "type": "directory", "recursive": True, "access": "read"}],
        "allowed_writes": ([{"path": item, "type": "file", "recursive": False, "access": "write"} for item in writes] if writes else []) + [{"path": str(TMP), "type": "directory", "recursive": True, "access": "create"}],
        "expected_exit_codes": [0], "expected_artifacts": [str(report)],
    }


def main():
    if RUN.exists() or TMP.exists():
        raise SystemExit("existing A4 run")
    TMP.mkdir(parents=True)
    baseline = {"head": git("rev-parse", "HEAD").strip(), "status": git("status", "--porcelain=v1").splitlines(), "diff_stat": git("diff", "--stat"), "dirty_files": inventory()}
    model_probe = probe()
    probe_hash = obj_hash(model_probe)
    probe_path = RUN / "model-probe.json"
    create_new(probe_path, canon(model_probe) + b"\n")
    # sidecar = 磁盘字节哈希（sha256sum 语义）；probe_hash 对象哈希只进 *_sha256 字段
    sidecar(probe_path, raw_hash(probe_path))
    writes = [str(REPO / item) for item in ("awareliquid/formal_reasoning.py", "tests/test_formal_reasoning.py")]
    criteria = [
        "AC-A4-01: Evidence context preserves original text and all required boundaries/IDs without semantic transformation",
        "AC-A4-02: Decimal-only safe structural arithmetic binds every input to Evidence IDs and rejects eval/exec/unknown operations",
        "AC-A4-03: every option yields supported/refuted/insufficient with deterministic evidence-backed comparisons",
        "AC-A4-04: exact-only locator is stable doc/page/char ordered and fail-closed A-scoped; no B without official B data",
        "AC-A4-05: focused synthetic offline tests prove prohibited BM25/RRF/vector/dense/hybrid/embedding/rerank/synonym/rewrite/semantic behavior is absent",
    ]
    packet = {
        "packet_version": 1, "run_id": RUN_ID, "thread_id": THREAD, "stage": "A4", "role": "E/V/R-A4",
        "rules_source": "reference/AFAC2026_OFFICIAL_RULES.md", "rules_sha256": raw_hash(RULES),
        "model": MODEL, "model_hash": model_probe["models"][MODEL]["model_hash"], "model_probe": model_probe, "model_probe_snapshot": {"path": str(probe_path), "sha256": probe_hash},
        "hash_domain": {"canonical_json": "UTF-8/no BOM/recursive key sort/comma-colon/no final LF", "prompt": "complete UTF-8 bytes", "ordinary_files": "complete raw bytes"},
        "objective": "Offline Evidence context, Decimal-safe option validation, and deterministic exact-only locator.",
        "acceptance_criteria": criteria,
        "fail_conditions": ["Qwen/API/network/credential use", "candidate/answer.csv", "embedding/rerank/BM25/RRF/vector/dense/hybrid", "eval/exec", "semantic filtering/rewriting/synonyms", "write outside allowlist"],
        "stop_conditions": ["hash/model/scope mismatch", "unclassified path", "missing evidence boundary", "A query missing nonempty doc_ids"],
        "read_roots": [str(REPO)], "write_roots": writes + [str(TMP)],
        "forbidden": ["network", "Qwen API", "embedding", "rerank", "BM25", "RRF", "vector", "dense", "hybrid", "answer.csv", "upload", "submit", "git reset", "git clean"],
    }
    packet_hash = obj_hash(packet)
    prompts = {}
    for role in ("E-A4", "V-A4", "R-A4"):
        path = RUN / role / "prompt.md"
        create_new(path, (prompt(role, packet).rstrip() + "\n").encode())
        sidecar(path, raw_hash(path))
        prompts[role] = path
    reports = {role: TMP / f"A4-{role}.md" for role in prompts}
    preflight = [".venv/bin/python", "-B", "-c", "import awareliquid.formal_reasoning"]
    commands = [command("A4-E-CMD-01", "E-A4", writes, reports["E-A4"], preflight), command("A4-V-CMD-01", "V-A4", [], reports["V-A4"], preflight), command("A4-R-CMD-01", "R-A4", writes, reports["R-A4"], preflight)]
    contract = {
        "run_id": RUN_ID, "thread_id": THREAD, "stage": "A4", "rules_path": "reference/AFAC2026_OFFICIAL_RULES.md", "rules_sha256": raw_hash(RULES),
        "model_probe": model_probe, "model": MODEL, "model_hash": model_probe["models"][MODEL]["model_hash"], "decision": model_probe["decision"], "git": baseline,
        "inputs": [{"path": "docs/AFAC2026_FINAL_EXECUTION_PROMPT.md", "sha256": raw_hash(SPEC), "purpose": "execution spec"}, {"path": "reference/AFAC2026_OFFICIAL_RULES.md", "sha256": raw_hash(RULES), "purpose": "rules"}, {"path": str(probe_path), "sha256": probe_hash, "purpose": "probe"}],
        "packet_sha256": packet_hash, "commands": commands, "acceptance_criteria": criteria, "fail_conditions": packet["fail_conditions"], "stop_conditions": packet["stop_conditions"],
        "permissions": {"read": packet["read_roots"], "write": packet["write_roots"], "forbidden": packet["forbidden"]},
        "artifacts": [str(RUN / "stage-contract.json"), str(RUN / "packet.json"), str(RUN / "manifest.json"), str(probe_path), *map(str, reports.values())],
        "handoff": "E-A4 -> independent V-A4; only V FAIL permits new R-A4 -> new V-A4.",
    }
    contract_hash = obj_hash(contract)
    manifest = {
        "run_id": RUN_ID, "thread_id": THREAD, "stage": "A4", "rules_path": "reference/AFAC2026_OFFICIAL_RULES.md", "rules_sha256": raw_hash(RULES),
        "contract_sha256": contract_hash, "packet_sha256": packet_hash, "model": MODEL, "model_hash": model_probe["models"][MODEL]["model_hash"],
        "prompts": {role: {"path": str(path), "sha256": raw_hash(path)} for role, path in prompts.items()},
        "artifacts": contract["artifacts"] + list(map(str, prompts.values())),
    }
    manifest_hash = obj_hash(manifest)
    for name, value, digest in (("stage-contract.json", contract, contract_hash), ("packet.json", packet, packet_hash), ("manifest.json", manifest, manifest_hash)):
        path = RUN / name
        create_new(path, canon(value) + b"\n")
        # sidecar 必须是磁盘字节（含尾部 LF）；digest 只作对象哈希留档
        sidecar(path, raw_hash(path))
    print(json.dumps({"run_id": RUN_ID, "contract_sha256": contract_hash, "packet_sha256": packet_hash, "manifest_sha256": manifest_hash}, sort_keys=True))


if __name__ == "__main__":
    main()
