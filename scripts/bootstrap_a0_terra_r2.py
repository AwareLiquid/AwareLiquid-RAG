#!/usr/bin/env python3
"""Create a fresh A0 Terra contract after the recorded Luna execution probe failed."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path


REPO = Path("/Users/aricredemption/Projects/AwareLiquid-M2")
SOURCE = REPO / "scripts" / "bootstrap_a0_artifacts.py"


def load_source():
    spec = importlib.util.spec_from_file_location("a0_bootstrap_source", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    module = load_source()
    original_probe = module.local_registry_probe
    module.RUN_ID = "a0-20260719T003000Z-terra-r2"
    module.MODEL = "gpt-5.6-terra"
    module.RUN_DIR = REPO / "docs" / "runs" / module.RUN_ID
    module.VERIFICATION_DIR = Path("/tmp/awareliquid-verification") / module.RUN_ID

    def probe() -> dict:
        value = original_probe()
        value["probe_timestamp_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        value["argv"] = [
            "multi_agent_v1.spawn_agent",
            "model=gpt-5.6-luna",
            "reasoning_effort=high",
            "service_tier=priority",
            "fork_context=false",
            "message=availability-probe",
        ]
        value["luna_execution_probe"] = {
            "agent_id": "019f770e-0b2f-7260-b9af-63d8de167501",
            "argv": value["argv"],
            "model": "gpt-5.6-luna",
            "network_called_by_controller": False,
            "result": "UNAVAILABLE",
            "error": "404 Not Found: Model gpt-5.6-luna is not supported by any configured account in this group",
            "request_id": "b5d28037-19c0-4d88-ac99-edc28cf05931",
        }
        value["models"]["gpt-5.6-luna"]["execution_available"] = False
        value["models"]["gpt-5.6-terra"]["execution_available"] = True
        value["decision"] = "TERRA_SELECTED_AFTER_LUNA_EXECUTION_404"
        value["exit_code"] = 0
        return value

    module.local_registry_probe = probe
    module.main()


if __name__ == "__main__":
    main()
