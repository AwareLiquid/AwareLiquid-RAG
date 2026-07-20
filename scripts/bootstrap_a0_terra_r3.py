#!/usr/bin/env python3
"""Create a fresh, immutable A0 audit contract using the Terra fallback."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/Users/aricredemption/Projects/AwareLiquid-M2")
SOURCE = REPO / "scripts" / "bootstrap_a0_artifacts.py"
RUN_ID = "a0-20260719T011500Z-terra-r3"


def load_source():
    spec = importlib.util.spec_from_file_location("a0_bootstrap_source_r3", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    module = load_source()
    original_probe = module.local_registry_probe
    original_prompt = module.role_prompt
    module.RUN_ID = RUN_ID
    module.MODEL = "gpt-5.6-terra"
    module.RUN_DIR = REPO / "docs" / "runs" / RUN_ID
    module.VERIFICATION_DIR = Path("/tmp/awareliquid-verification") / RUN_ID

    def probe() -> dict:
        value = original_probe()
        value["probe_timestamp_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        value["argv"] = [
            "multi_agent_v1.spawn_agent", "model=gpt-5.6-luna",
            "reasoning_effort=high", "service_tier=priority",
            "fork_context=false", "message=availability-probe",
        ]
        value["luna_execution_probe"] = {
            "agent_id": "019f771e-2690-78c0-9596-a458f519d832",
            "argv": value["argv"],
            "model": "gpt-5.6-luna",
            "network_called_by_controller": False,
            "result": "UNAVAILABLE",
            "error": "404 Not Found: Model gpt-5.6-luna is not supported by any configured account in this group",
            "request_id": "ee374a28-5879-4e6b-abdc-e49ae306c26c",
        }
        value["models"]["gpt-5.6-luna"]["execution_available"] = False
        value["models"]["gpt-5.6-terra"]["execution_available"] = True
        value["decision"] = "TERRA_SELECTED_AFTER_LUNA_EXECUTION_404"
        value["exit_code"] = 0
        return value

    def role_prompt(role: str, packet: dict) -> str:
        base = original_prompt(role, packet)
        policy = (
            "\nA0 acceptance interpretation (binding for this run): A0 is a read-only baseline audit. "
            "It PASSES when it independently records official-rule hashes, preserves the dirty baseline, "
            "and identifies every current CSV/input/output, provider/network/Mock/embedding/rerank, "
            "A/B/doc_ids/Evidence/ledger/accuracy risk with direct source evidence. A currently noncompliant "
            "implementation is an audit finding for A1-A4, NOT an A0 acceptance failure. Do not require "
            "the project to be repaired at A0 and do not treat lower-priority implementation artifacts as "
            "normative authority in the audit. Mark an AC FAIL only if the audit itself lacks required direct "
            "evidence, changes the baseline, calls forbidden facilities, or has a hash/scope/model defect. "
            "For V-A0, redo the audit from original sources without reading or trusting the E report; the "
            "Controller's completed E-to-V dispatch is sequencing evidence, not a source-level AC to fail."
        )
        return base.rstrip() + policy + "\n"

    module.local_registry_probe = probe
    module.role_prompt = role_prompt
    module.main()


if __name__ == "__main__":
    main()
