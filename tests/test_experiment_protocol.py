"""tests/test_experiment_protocol.py — E0 协议固化契约.

真实案例回放（事故 → 协议 → 测试，三条用例对应本仓库实际发生过的事故形态）：
  • README bench 表格单跑一遍的 6 题计数（如 lexical recall 5/6）——
    属"单 seed 单次运行"，引用前必须被 seeds 门槛拦下
  • chance/满分两团的双峰 per-seed 分布 → 必须被判双峰
  • 6/6 全胜对照 → 配对符号检验 p = 0.03125 < 0.05，是"可引用"的最小形态
"""

import pytest

from benchmarks.experiment_protocol import (
    ProtocolViolation, bimodality_1d, fisher_exact_2x2, forbid_bimodal,
    paired_sign_test, publishable, require_min_seeds,
)


def test_min_seeds_gate():
    # README bench 表格即此类：单次运行的计数不得直接引用
    with pytest.raises(ProtocolViolation, match="单/双 seed"):
        require_min_seeds([5 / 6], what="bench-lexical-recall")
    with pytest.raises(ProtocolViolation):
        require_min_seeds([0.5, 0.6])                  # 双 seed 同样不够
    assert require_min_seeds([0.5, 0.6, 0.55]) == [0.5, 0.6, 0.55]


def test_bimodality_detects_chance_or_perfect():
    # 两个 seed 卡在 chance 区, 三个 seed 满分 —— 中间是空带, 不得引用
    bm = bimodality_1d([0.17, 0.18, 1.0, 1.0, 1.0])
    assert bm["bimodal"] is True
    with pytest.raises(ProtocolViolation, match="双峰"):
        forbid_bimodal([0.17, 0.18, 1.0, 1.0, 1.0])


def test_bimodality_passes_unimodal_noise():
    bm = bimodality_1d([0.52, 0.55, 0.53, 0.56, 0.54, 0.55])
    assert bm["bimodal"] is False


def test_bimodality_ignores_quantized_neighbors():
    # 量化分数的常态: 簇内全是重复值时类内散度为 0, 任意两个相邻取值的
    # gap_ratio 都会爆炸——2026-09-07 评审修复: 增加绝对间隙下限 0.25,
    # 这种正常一致性数据不得误判成双峰 (否则小题集永远过不了门)
    assert bimodality_1d([0.75, 0.75, 0.75, 0.875])["bimodal"] is False
    assert bimodality_1d([0.875, 0.875, 1.0, 1.0])["bimodal"] is False
    # 真双峰 (空带跨 0.25 以上) 仍然要抓
    assert bimodality_1d([0.25, 0.25, 0.75, 0.75])["bimodal"] is True


def test_none_per_seed_value_is_violation_not_crash():
    # None 必须以 ProtocolViolation 判负, 不能以 TypeError 崩溃
    with pytest.raises(ProtocolViolation, match="None"):
        require_min_seeds([0.5, None, 0.6])
    # publishable 路径: 含 None 的臂记为未过门, 而不是让调用方收到异常
    ok, rep = publishable([0.5, None, 0.6, 0.55], [0.2, 0.3, 0.2, 0.3],
                          tag="none-arm")
    assert not ok and any("None" in r for r in rep["reasons"])


def test_paired_sign_test_significance():
    # 6/6 全胜 → p = 2·(1/64) = 0.03125 < 0.05
    st = paired_sign_test([1.0] * 6, [0.0] * 6)
    assert st["p"] == pytest.approx(0.03125)
    # 3胜3负 (无平局) → p = 1.0 (不显著)
    st2 = paired_sign_test([1, 0.3, 1, 0.3, 1, 0.3], [0.4] * 6)
    assert st2["p"] > 0.99
    # 平局被丢弃: 0 vs 0 的对不参与 (3 对里 2 对分胜负)
    st3 = paired_sign_test([1, 0, 1], [0, 0, 0])
    assert st3["n_effective"] == 2 and st3["wins"] == 2


def test_fisher_exact_2x2_significant_case():
    # 5/6 vs 0/6 的列联对比 (双侧 Fisher) 必须显著
    r = fisher_exact_2x2([[5, 1], [0, 6]])
    assert r["p"] < 0.05


def test_fisher_exact_independence_edge():
    assert fisher_exact_2x2([[3, 3], [3, 3]])["p"] > 0.9   # 无关联


def test_publishable_full_gate():
    # 干净分离 + 足量 seeds + 单峰 → 可引用 (6/6 全胜 p=0.031)
    ok, rep = publishable([1.0] * 6, [0.2] * 6, tag="demo-good")
    assert ok, rep["reasons"]
    # 4 seeds 全胜: p=2/16=0.125 ≥ 0.05 → 协议正确地拒绝 (4 seeds 不够引用)
    ok4s, rep4s = publishable([1.0] * 4, [0.2] * 4, tag="four-seeds")
    assert not ok4s and any("配对符号检验" in r for r in rep4s["reasons"])
    # 单次运行 → 只能入档
    ok2, rep2 = publishable([5 / 6], [4 / 6], tag="bench-single-run")
    assert not ok2 and any("seed" in r for r in rep2["reasons"])
    # 双峰臂 → 只能入档
    ok3, rep3 = publishable([0.17, 0.18, 1.0, 1.0, 1.0, 1.0],
                            [0.2] * 6, tag="bimodal-arm")
    assert not ok3 and any("双峰" in r for r in rep3["reasons"])
    # 无分离 (p≥α) → 只能入档
    ok4, rep4 = publishable([0.5, 0.6, 0.55, 0.52, 0.58, 0.51],
                            [0.52, 0.5, 0.58, 0.54, 0.5, 0.55], tag="null")
    assert not ok4 and any("配对符号检验" in r for r in rep4["reasons"])
