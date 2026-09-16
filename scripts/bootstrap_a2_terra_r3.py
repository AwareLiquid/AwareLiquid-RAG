#!/usr/bin/env python3
"""Create a fresh A2 audit run that protects the pre-existing r2 bytecode file."""

from __future__ import annotations

from pathlib import Path


REPO = Path("/Users/aricredemption/Projects/AwareLiquid-M2")
SOURCE = REPO / "scripts" / "bootstrap_a2_terra_r1.py"


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    source = source.replace(
        'RUN_ID="a2-20260719T060000Z-terra-r1"',
        'RUN_ID="a2-20260719T180000Z-terra-r3"',
        1,
    )
    source = source.replace(
        '"agent_id":"019f774d-b5b4-76a1-9c17-75d1306243bd"',
        '"agent_id":"019f77b7-69fd-70b2-a7e2-1d3d72a5a592"',
        1,
    )
    source = source.replace(
        '"request_id":"50adebd0-bcda-4148-8f1e-47df313b8ea4"',
        '"request_id":"fbbab072-c926-4646-99e5-9648a809ab00"',
        1,
    )
    source = source.replace(
        '".git",".venv","__pycache__",".pytest_cache"',
        '".git",".venv",".pytest_cache"',
        1,
    )
    source = source.replace(
        '"preflight_argv":["/usr/bin/true"],"verify_argv":["/usr/bin/true"]',
        '"preflight_argv":[".venv/bin/python","-B","-c","from awareliquid.adapter.qwen_client import formal_network_denied_probe; formal_network_denied_probe()"],"verify_argv":[".venv/bin/python","-B","-c","from awareliquid.adapter.qwen_client import formal_network_denied_probe; formal_network_denied_probe()"]',
        1,
    )
    namespace = {"__name__": "a2_bootstrap_r3"}
    exec(compile(source, str(SOURCE), "exec"), namespace)
    namespace["main"]()


if __name__ == "__main__":
    main()
