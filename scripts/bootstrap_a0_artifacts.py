#!/usr/bin/env python3
"""Create one immutable A0 contract, packet, role prompts, manifest, and sidecars."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path


REPO = Path("/Users/aricredemption/Projects/AwareLiquid-M2")
RUN_ID = "a0-20260719T000000Z-terra-r1"
THREAD_ID = "019f76af-976a-7012-b207-acefa2f456aa"
RUN_DIR = REPO / "docs" / "runs" / RUN_ID
VERIFICATION_DIR = Path("/tmp/awareliquid-verification") / RUN_ID
RULES_PATH = REPO / "reference" / "AFAC2026_OFFICIAL_RULES.md"
PROMPT_PATH = REPO / "docs" / "AFAC2026_FINAL_EXECUTION_PROMPT.md"
MODEL = "gpt-5.6-terra"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def local_registry_probe() -> dict:
    config_path = Path("/Users/aricredemption/.codex/config.toml")
    cache_path = Path("/Users/aricredemption/.codex/models_cache.json")
    config_bytes = config_path.read_bytes()
    cache_bytes = cache_path.read_bytes()
    config = tomllib.loads(config_bytes.decode("utf-8"))
    cache = json.loads(cache_bytes)
    provider_name = config.get("model_provider")
    provider = (config.get("model_providers") or {}).get(provider_name, {})
    models = {item.get("slug"): item for item in cache.get("models", []) if isinstance(item, dict) and item.get("slug")}
    model_records = {}
    for slug in ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"):
        item = models.get(slug)
        eligible = bool(item and item.get("visibility") == "list" and item.get("supported_in_api") is True)
        model_records[slug] = {
            "present": item is not None,
            "visibility": item.get("visibility") if item else None,
            "supported_in_api": item.get("supported_in_api") if item else None,
            "model_hash": digest(item) if item else None,
            "registry_eligible": eligible,
        }
    all_valid = all(item["registry_eligible"] for item in model_records.values())
    return {
        "probe_kind": "local-model-registry",
        "probe_timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cwd": str(REPO),
        "argv": ["python3", "scripts/bootstrap_a0_artifacts.py"],
        "network_called": False,
        "api_called": False,
        "config_path": str(config_path),
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "cache_path": str(cache_path),
        "cache_sha256": hashlib.sha256(cache_bytes).hexdigest(),
        "cache_timestamp": cache.get("fetched_at"),
        "codex_client_version": cache.get("client_version"),
        "active_provider": provider_name,
        "active_model": config.get("model"),
        "provider_base_url_origin": provider.get("base_url"),
        "models": model_records,
        "exit_code": 0 if all_valid else 1,
        "decision": "LUNA_SELECTED" if model_records["gpt-5.6-luna"]["registry_eligible"] else "TERRA_SELECTED" if model_records["gpt-5.6-terra"]["registry_eligible"] else "BLOCKED_MODEL_PROBE",
    }


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def sidecar(path: Path, hash_value: str) -> None:
    write_exclusive(
        Path(f"{path}.sha256"),
        f"{hash_value}  {path.name}\n".encode("ascii"),
    )


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=REPO,
        text=True,
        stderr=subprocess.STDOUT,
    )


def dirty_files() -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for path in sorted(REPO.rglob("*")):
        if ".git" in path.parts:
            continue
        if any(part in {".venv", "__pycache__", ".pytest_cache"} or part.endswith(".egg-info") for part in path.parts):
            continue
        raw = path.relative_to(REPO).as_posix()
        if path.is_symlink():
            value = os.readlink(path).encode("utf-8")
            output.append({"path": raw, "type": "symlink", "sha256": hashlib.sha256(value).hexdigest()})
        elif path.is_file():
            output.append({"path": raw, "type": "file", "sha256": file_digest(path)})
    return output


def command(
    command_id: str,
    prompt_path: Path,
    output_path: Path,
    read_roots: list[str],
    expected_artifacts: list[str],
) -> dict:
    return {
        "id": command_id,
        "cwd": str(REPO),
        "argv": [
            "multi_agent_v1.spawn_agent",
            "model=" + MODEL,
            "reasoning_effort=high",
            "fork_context=false",
            "service_tier=priority",
            "message=stdin",
        ],
        "env_inheritance": "none",
        "env_allow": {},
        "env_deny": [
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        ],
        "stdin": {
            "source": "absolute-file",
            "path": str(prompt_path),
            "sha256": file_digest(prompt_path),
        },
        "network_enforcement": {
            "mode": "actual-deny",
            "egress_allowlist": [],
            "preflight_argv": ["/usr/bin/true"],
            "verify_argv": ["/usr/bin/true"],
            "expected_preflight_exit": 0,
            "expected_verify_exit": 0,
        },
        "credential_ref": None,
        "proxy_unset": True,
        "timeout_seconds": 300,
        "kill_grace_seconds": 5,
        "allowed_read_roots": [
            {
                "path": path,
                "type": "directory" if Path(path).is_dir() else "file",
                "recursive": Path(path).is_dir(),
                "access": "read",
            }
            for path in read_roots
        ],
        "allowed_writes": [
            {"path": str(output_path), "type": "file", "recursive": False, "access": "create"},
            {"path": str(VERIFICATION_DIR), "type": "directory", "recursive": True, "access": "create"},
        ],
        "expected_exit_codes": [0],
        "expected_artifacts": expected_artifacts,
    }


def role_prompt(role: str, packet: dict) -> str:
    packet_text = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        f"You are the independent {role} agent for A0 in AwareLiquid-M2.\n"
        "Use only the exact model selected by the stage contract. Do not call Qwen, any API, "
        "the network, or any credential. Read only the listed roots. Do not modify the repository, "
        "generate answer.csv, claim accuracy, or trust another agent report.\n"
        "Treat the immutable model-probe snapshot named in the Packet as the authority for this run; "
        "do not substitute a mutable Agent-host cache. Canonical JSON hashes sort keys recursively, "
        "use UTF-8 with comma/colon separators, and exclude one final LF from the hash domain.\n"
        "Perform the role described in the Packet and return a structured report with every AC ID, "
        "direct evidence paths, hashes, commands, findings, and status PASS/FAIL/BLOCKED.\n\n"
        "BEGIN PACKET\n"
        f"{packet_text}\n"
        "END PACKET\n"
    )


def main() -> None:
    if RUN_DIR.exists():
        raise SystemExit(f"refusing to overwrite existing run directory: {RUN_DIR}")
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=False)
    (VERIFICATION_DIR / "tmp").mkdir()

    baseline = {
        "head": git("rev-parse", "HEAD").strip(),
        "status": git("status", "--porcelain=v1").splitlines(),
        "diff_stat": git("diff", "--stat"),
        "dirty_files": dirty_files(),
    }
    probe = local_registry_probe()
    if not probe["models"][MODEL]["registry_eligible"]:
        raise SystemExit(f"model probe did not select an eligible {MODEL}: {probe['decision']}")
    model_hash = probe["models"][MODEL]["model_hash"]
    probe_snapshot_path = RUN_DIR / "model-probe.json"
    probe_snapshot_hash = digest(probe)
    write_exclusive(probe_snapshot_path, canonical_bytes(probe) + b"\n")
    # sidecar = 磁盘字节哈希；对象哈希只进 packet/contract 的 *_sha256 字段
    sidecar(probe_snapshot_path, file_digest(probe_snapshot_path))

    packet = {
        "packet_version": 1,
        "run_id": RUN_ID,
        "thread_id": THREAD_ID,
        "stage": "A0",
        "role": "E/V/R-A0",
        "rules_source": "reference/AFAC2026_OFFICIAL_RULES.md",
        "rules_sha256": file_digest(RULES_PATH),
        "model": MODEL,
        "model_hash": model_hash,
        "model_probe": probe,
        "model_probe_snapshot": {
            "path": str(probe_snapshot_path),
            "sha256": probe_snapshot_hash,
        },
        "hash_domain": {
            "encoding": "UTF-8",
            "object_key_order": "recursive Unicode code-point ascending",
            "array_order": "preserved",
            "separators": [",", ":"],
            "canonical_body_final_lf": False,
            "sidecar_final_lf": True,
        },
        "objective": "Read-only rules, code, data, manifest, test, and dirty-baseline audit.",
        "remediation_context": {
            "previous_run": "a0-20260718T203619Z-luna-r6",
            "previous_status": "BLOCKED",
            "findings": [
                "The live models cache refreshes during Agent startup; this run records a fresh dynamic registry probe and freezes its canonical JSON as an immutable model-probe snapshot before dispatch.",
                "The previous full inventory included generated .venv files; this run excludes only .venv, __pycache__, .pytest_cache, and *.egg-info while retaining data/raw, downloads, code, tests, scripts, and execution artifacts.",
                "The previous V report compared raw file hashes including the final LF; this run embeds the canonical hash-domain rule and requires verification against the immutable snapshot, excluding one final LF.",
                "A structured gpt-5.6-luna V-A0 dispatch returned provider 404 (unsupported by configured account); this new stage uses the required uniform Terra fallback for all further A0 roles.",
            ],
            "r_scope": "Only repair audit evidence, scope declaration, probe record, and report continuity; do not modify project code, rules, data, or old artifacts.",
        },
        "acceptance_criteria": [
            "AC-A0-01: official rules and hashes are recorded without using lower-priority documents as normative authority",
            "AC-A0-02: current HEAD, status, diff-stat, and dirty file hashes are preserved",
            "AC-A0-03: CSV, summary, token, tf, qid, multi, and answer-format risks are identified",
            "AC-A0-04: provider/model gate, Mock fallback, network, embedding, dense, hybrid, and rerank risks are identified",
            "AC-A0-05: A/B data, dates, doc_ids, Evidence, ledger, and accuracy-claim risks are identified",
            "AC-A0-06: audit is read-only, offline, and produces no candidate or accuracy claim",
        ],
        "fail_conditions": [
            "Any write outside the verification audit directory",
            "Any API, Qwen, network, credential, embedding, rerank, or semantic-summary use",
            "Any missing direct evidence for an AC",
            "Any dirty baseline path changed during the audit",
        ],
        "stop_conditions": [
            "Model probe mismatch or missing model hash",
            "Hash, Packet, Prompt, Manifest, scope, or command mismatch",
            "Unclassified path, symlink escape, or forbidden dependency",
        ],
        "read_roots": [
            str(REPO),
            str(REPO / ".git"),
            "/Users/aricredemption/.codex/config.toml",
            "/Users/aricredemption/.codex/models_cache.json",
        ],
        "write_roots": [str(VERIFICATION_DIR)],
        "forbidden": ["answer.csv", "output", "network", "Qwen API", "embedding", "rerank", "git reset", "git clean"],
    }
    packet_hash = digest(packet)
    role_prompts: dict[str, tuple[Path, str]] = {}
    for role in ("E-A0", "V-A0", "R-A0"):
        prompt_path = RUN_DIR / role / "prompt.md"
        role_prompts[role] = (prompt_path, role_prompt(role, packet))

    # Prompt files are independent of the contract hash, preserving contract -> packet -> prompt order.
    for prompt_path, content in role_prompts.values():
        write_exclusive(prompt_path, (content.rstrip() + "\n").encode("utf-8"))
        sidecar(prompt_path, file_digest(prompt_path))

    commands = [
        command("A0-E-CMD-01", role_prompts["E-A0"][0], VERIFICATION_DIR / "A0-E-A0.md", packet["read_roots"], [str(VERIFICATION_DIR / "A0-E-A0.md")]),
        command("A0-V-CMD-01", role_prompts["V-A0"][0], VERIFICATION_DIR / "A0-V-A0.md", packet["read_roots"], [str(VERIFICATION_DIR / "A0-V-A0.md")]),
        command("A0-R-CMD-01", role_prompts["R-A0"][0], VERIFICATION_DIR / "A0-R-A0.md", packet["read_roots"], [str(VERIFICATION_DIR / "A0-R-A0.md")]),
    ]
    contract = {
        "run_id": RUN_ID,
        "thread_id": THREAD_ID,
        "stage": "A0",
        "rules_path": "reference/AFAC2026_OFFICIAL_RULES.md",
        "rules_sha256": file_digest(RULES_PATH),
        "model_probe": probe,
        "model": MODEL,
        "model_hash": model_hash,
        "decision": "TERRA_SELECTED_AFTER_LUNA_PROVIDER_404",
        "git": baseline,
        "packet_sha256": packet_hash,
        "inputs": [
            {"path": "docs/AFAC2026_FINAL_EXECUTION_PROMPT.md", "sha256": file_digest(PROMPT_PATH), "purpose": "execution specification"},
            {"path": "reference/AFAC2026_OFFICIAL_RULES.md", "sha256": file_digest(RULES_PATH), "purpose": "normative rules"},
            {"path": str(probe_snapshot_path), "sha256": probe_snapshot_hash, "purpose": "immutable local model registry probe snapshot"},
        ],
        "commands": commands,
        "acceptance_criteria": packet["acceptance_criteria"],
        "fail_conditions": packet["fail_conditions"],
        "stop_conditions": packet["stop_conditions"],
        "permissions": {
            "read": packet["read_roots"],
            "write": packet["write_roots"],
            "forbidden": packet["forbidden"],
        },
        "artifacts": [
            str(RUN_DIR / "stage-contract.json"),
            str(RUN_DIR / "packet.json"),
            str(RUN_DIR / "manifest.json"),
            str(probe_snapshot_path),
            str(VERIFICATION_DIR / "A0-E-A0.md"),
            str(VERIFICATION_DIR / "A0-V-A0.md"),
            str(VERIFICATION_DIR / "A0-R-A0.md"),
        ],
        "handoff": "E-A0 -> independent V-A0; only V FAIL permits new R-A0 -> new V-A0.",
    }
    contract_hash = digest(contract)

    # Write the final immutable documents.
    contract_body = canonical_bytes(contract) + b"\n"
    packet_body = canonical_bytes(packet) + b"\n"
    manifest = {
        "run_id": RUN_ID,
        "thread_id": THREAD_ID,
        "stage": "A0",
        "rules_path": "reference/AFAC2026_OFFICIAL_RULES.md",
        "rules_sha256": file_digest(RULES_PATH),
        "contract_sha256": contract_hash,
        "packet_sha256": packet_hash,
        "prompts": {
            role: {"path": str(path), "sha256": file_digest(path)}
            for role, (path, _) in role_prompts.items()
        },
        "model": MODEL,
        "model_hash": model_hash,
        "artifacts": contract["artifacts"] + [str(path) for path, _ in role_prompts.values()],
    }
    manifest_hash = digest(manifest)
    write_exclusive(RUN_DIR / "stage-contract.json", contract_body)
    sidecar(RUN_DIR / "stage-contract.json", file_digest(RUN_DIR / "stage-contract.json"))
    write_exclusive(RUN_DIR / "packet.json", packet_body)
    sidecar(RUN_DIR / "packet.json", file_digest(RUN_DIR / "packet.json"))
    write_exclusive(RUN_DIR / "manifest.json", (canonical_bytes(manifest) + b"\n"))
    sidecar(RUN_DIR / "manifest.json", file_digest(RUN_DIR / "manifest.json"))
    write_exclusive(
        RUN_DIR / "creation-record.json",
        (
            canonical_bytes(
                {
                    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "run_id": RUN_ID,
                    "contract_sha256": contract_hash,
                    "packet_sha256": packet_hash,
                    "manifest_sha256": manifest_hash,
                    "prompt_sha256": manifest["prompts"],
                }
            )
            + b"\n"
        ),
    )
    print(json.dumps({
        "run_id": RUN_ID,
        "contract_sha256": contract_hash,
        "packet_sha256": packet_hash,
        "manifest_sha256": manifest_hash,
        "prompt_sha256": manifest["prompts"],
        "verification_dir": str(VERIFICATION_DIR),
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
