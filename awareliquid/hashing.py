"""Salt-free text hashing for scoring paths.

内建 ``hash()`` 的盐随进程变化（PYTHONHASHSEED），出现在检索/打分路径上
会让结果跨进程不可复现——2026-09-06 bench 数字漂移事故的根因（见
docs/RESULTS.md 对账日志与 docs/PREREGISTRATION.md 不做清单）。所有需要
"字符串 → 稳定桶"的地方一律走本模块，禁止回退到内建 ``hash()``。
"""

from __future__ import annotations

import hashlib


def stable_hash(text: str) -> int:
    """Deterministic 32-bit bucket hash — identical across processes and salt settings."""
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
