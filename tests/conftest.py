"""Shared test fixtures.

Tests must run offline, so we never download the real sentence-transformer.
``FakeEncoder`` is a tiny deterministic hashing embedder that satisfies the same
interface (``.dim`` and ``.encode(text, is_query=...)``) the agent depends on.
"""

import os
import random
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

from awareliquid.hashing import stable_hash

# 让 tests/ 可以 import 仓库根下的 benchmarks/ 等目录，不依赖 editable install。
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def pytest_configure(config):
    # 内建 hash() 的盐由解释器启动时的 PYTHONHASHSEED 决定，运行期无法钉扎。
    # 这里显式设置环境变量，供子进程/工具脚本继承；本进程内的 FakeEncoder
    # 则改用 hashlib（见下），保证跨进程可复现。
    os.environ.setdefault("PYTHONHASHSEED", "0")


@pytest.fixture(autouse=True)
def _pin_rng():
    """把所有测试的 RNG 统一钉到固定 seed。

    一个忘了 seed 的测试不能因为邻居留下的 RNG 状态而变 flaky；
    这是把"可复现性"落到测试层（M1 tests/conftest.py 同款纪律）。
    """
    seed = 1234
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    yield


class FakeEncoder:
    """Deterministic hashing embedder over character bigrams (no model download)."""

    def __init__(self, dim: int = 64):
        self._dim = int(dim)

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, text: str, is_query: bool = False) -> torch.Tensor:
        vec = torch.zeros(self._dim, dtype=torch.float32)
        text = (text or "").lower()
        for i in range(len(text) - 1):
            # stable_hash 而非内建 hash()：内建 hash 的盐随进程变化，会让
            # 同一份输入在不同进程得到不同向量（基准数字不可复现）。
            vec[stable_hash(text[i : i + 2]) % self._dim] += 1.0
        norm = torch.linalg.vector_norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def as_fn(self, is_query: bool = False):
        return lambda t: self.encode(t, is_query=is_query)
