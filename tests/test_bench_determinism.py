"""Regression test for the 2026-09-06 bench determinism incident.

事故：``benchmarks/bench_adapter.py`` 的 ``LexicalEncoder`` 曾用内建
``hash()`` 给字符 n-gram 分桶，而内建 ``hash()`` 的盐随进程随机（由
PYTHONHASHSEED 决定）——同一份输入在不同进程得到不同向量，导致
``bench --fake`` 连续两次运行输出互相矛盾（recall 一说 8/8 一说 7/8）。

协议：修复为 hashlib.md5 后，bench 输出必须与进程盐无关。本测试用两个
不同的 ``PYTHONHASHSEED``（1 和 2）各起一个子进程跑 ``--fake`` 基准，
刻意制造"两个不同盐的进程"——修复前这个对照会产出不同结果——并断言
两次 stdout 逐字节一致（事故的自动化锁，替代人工三连跑比对）。
"""

import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BENCH = _REPO_ROOT / "benchmarks" / "bench_adapter.py"


def _run_bench(hash_seed: str) -> bytes:
    """Run ``bench_adapter.py --fake`` in a fresh process with a pinned hash salt.

    用 sys.executable 而非硬编码 .venv 路径，保证在 CI（无 .venv）下可用。
    不以 text 模式捕获：断言对象是原始字节，"逐字节一致"就是字面意思。
    """
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = hash_seed  # 显式覆盖，压过 conftest.py 的 setdefault("0")
    proc = subprocess.run(
        [sys.executable, str(_BENCH), "--fake"],
        cwd=str(_REPO_ROOT),  # bench 按仓库根相对布局导入 awareliquid
        env=env,
        capture_output=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    return proc.stdout


def test_bench_fake_output_is_independent_of_process_hash_salt():
    """两个不同 PYTHONHASHSEED 的进程，bench --fake 输出必须逐字节一致。"""
    run_seed1 = _run_bench("1")
    run_seed2 = _run_bench("2")

    assert b"RESULT: PASS" in run_seed1
    assert b"RESULT: PASS" in run_seed2
    assert run_seed1 == run_seed2, (
        "bench --fake output drifted across process hash salts -- "
        "built-in hash() likely crept back into the scoring path "
        "(2026-09-06 incident regression)"
    )


def test_bench_output_matches_archived_log():
    """bench 输出必须与留档日志逐字节一致。

    把 README / docs/RESULTS.md 引用的数字钉死到产物上：改题集/语料/
    编码器导致输出变化时，这个断言会失败——必须显式重新留档并对账文档，
    而不是让文档数字静默过期（2026-09-07 评审 S3）。
    """
    archived = _REPO_ROOT / "benchmarks" / "results" / "bench_adapter_fake_20260906_r1.log"
    assert archived.is_file(), (
        "archived bench log missing -- regenerate with "
        "`python benchmarks/bench_adapter.py --fake` and reconcile docs"
    )
    assert _run_bench("0") == archived.read_bytes(), (
        "bench output no longer matches the archived log -- "
        "re-archive the log and reconcile README/docs/RESULTS.md"
    )
