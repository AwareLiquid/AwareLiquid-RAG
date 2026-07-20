#!/usr/bin/env python3
"""Create A2 remediation run r2 without changing r1's immutable artifacts."""

from __future__ import annotations

from pathlib import Path


REPO = Path("/Users/aricredemption/Projects/AwareLiquid-M2")
SOURCE = REPO / "scripts" / "bootstrap_a2_terra_r1.py"


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    source = source.replace(
        'RUN_ID="a2-20260719T060000Z-terra-r1"',
        'RUN_ID="a2-20260719T120000Z-terra-r2"',
        1,
    )
    source = source.replace(
        '"agent_id":"019f774d-b5b4-76a1-9c17-75d1306243bd"',
        '"agent_id":"019f7775-e431-7950-978a-c9b10bd626d1"',
        1,
    )
    source = source.replace(
        '"request_id":"50adebd0-bcda-4148-8f1e-47df313b8ea4"',
        '"request_id":"0b35acae-a52d-4d5c-96d1-4184602c9991"',
        1,
    )
    source = source.replace(
        '"preflight_argv":["/usr/bin/true"],"verify_argv":["/usr/bin/true"]',
        '"preflight_argv":[".venv/bin/python","-c","from awareliquid.adapter.qwen_client import formal_network_denied_probe; formal_network_denied_probe()"],"verify_argv":[".venv/bin/python","-c","from awareliquid.adapter.qwen_client import formal_network_denied_probe; formal_network_denied_probe()"]',
        1,
    )
    namespace = {"__name__": "a2_bootstrap_r2"}
    exec(compile(source, str(SOURCE), "exec"), namespace)
    namespace["main"]()


if __name__ == "__main__":
    main()
