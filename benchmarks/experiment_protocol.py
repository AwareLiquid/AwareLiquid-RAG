"""experiment_protocol.py — E0 实验协议固化.

背景：本项目的对外数字（README bench 表格、评测分数）此前均为单次运行
产物——lexical stand-in 的 recall 5/6、retention 5/6 都是单跑一遍的计数，
没有 seed 数、显著性或分布形态约束。套用 M1 仓库（MT-LNN）被"单 seed
结论"咬过两次后固化的 E0 纪律：**凡对外引用的对照数字，必须过代码化
的协议门；过不了门的结果只能入档，不能引用。**

四条硬纪律（全部零依赖，纯 python + math）：

1. ``require_min_seeds(per_seed_values, min_seeds=3)``
   不足 N seeds → ProtocolViolation（引用前必须过这关）。
2. ``bimodality_1d(values)`` — 双峰检测：1-D 二分聚类，
   报告 {bimodal, split_at, gap_ratio}。双峰数据**不得引用**。
3. ``paired_sign_test(a, b)`` / ``fisher_exact_2x2(table)`` — 配对/列联
   检验，不依赖 scipy，跨环境可复现。
4. ``publishable(per_seed_a, per_seed_b)`` — 引用门槛一键判定：
   ≥3 seeds、双臂非双峰、配对检验 p<0.05，返回 (ok, report)。

单次运行的 bench 计数（如 6 题召回 6/6）属于**方向筛选**：只能用于
smoke 和回归对照，不得作为对外结论引用；要引用就必须扩成多 seed /
多题集并过 ``publishable``。

用法::

    from benchmarks.experiment_protocol import publishable
    ok, report = publishable(recall_a, recall_b, tag="bench-e5-vs-lexical")
    # ok=False 时 report["reasons"] 说明差哪关 —— 结果只能入档，不能引用
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple


class ProtocolViolation(RuntimeError):
    """违反 E0 协议（seeds 不足 / 双峰区数据 / 引用门槛未过）。"""


# 双峰判定的绝对间隙下限（指标量纲按 [0,1] 设计；其他量纲需按比例调整）。
# 只有比值判据不够：per-seed 分数是量化值（如 recall 只能取 6/8、7/8），
# 簇内一旦全是重复值，类内散度就是 0，任意两个不同取值的 gap_ratio 都会
# 爆炸——[0.75, 0.75, 0.75, 0.875] 这种正常一致性数据会被误判成双峰。
# 要求空带至少跨 0.25，才能谈"两团中间隔着一条空带"。
_MIN_BIMODAL_GAP = 0.25


def fisher_exact_2x2(table: Sequence[Sequence[int]]) -> Dict:
    """2×2 Fisher 精确检验（双侧, hypergeometric 尾概率和法）。"""
    ((a, b), (c, d)) = table
    n = a + b + c + d
    if min(a + b, c + d, a + c, b + d) == 0:
        return {"p": 1.0, "odds_ratio": float("nan")}

    def p_exact(x):
        return (math.comb(a + c, x) * math.comb(b + d, a + b - x)
                / math.comb(n, a + b))

    p_obs = p_exact(a)
    # 双侧: 所有 ≤ 观察概率的表求和（相对容差：超大表下绝对容差会因
    # 浮点末位差漏加数学上相等的表）
    lo = max(0, (a + b) - (b + d))
    hi = min(a + b, a + c)
    p = sum(p_exact(x) for x in range(lo, hi + 1)
            if p_exact(x) <= p_obs * (1 + 1e-9) + 1e-15)
    or_ = (a * d) / (b * c) if b and c else float("inf")
    return {"p": min(1.0, p), "odds_ratio": or_}


def paired_sign_test(a: Sequence[float], b: Sequence[float]) -> Dict:
    """配对符号检验（精确二项, 双侧）。

    H0: P(a_i > b_i) = 0.5。并列对丢弃。含 NaN 的对会被静默当平局
    （NaN 的比较恒为 False）——引用路径上先过 require_min_seeds（拒绝
    NaN/None）再进来。无 scipy 依赖 —— 跨 macOS/Linux/CI 环境结果一致。
    """
    if len(a) != len(b):
        raise ValueError("paired_sign_test: a/b 长度不一致")
    wins = sum(1 for x, y in zip(a, b) if x > y)
    losses = sum(1 for x, y in zip(a, b) if x < y)
    n = wins + losses
    if n == 0:
        return {"p": 1.0, "wins": 0, "losses": 0, "n_effective": 0}
    k = min(wins, losses)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n * 2
    return {"p": min(1.0, p), "wins": wins, "losses": losses,
            "n_effective": n}


def require_min_seeds(values: Sequence[float], min_seeds: int = 3,
                      what: str = "result") -> List[float]:
    vals = []
    for v in values:
        if v is None:
            # None 必须在 float() 之前拦下，否则会以 TypeError 崩溃而非按协议判负
            raise ProtocolViolation(f"{what}: per-seed 值含 None")
        vals.append(float(v))
    if len(vals) < min_seeds:
        raise ProtocolViolation(
            f"{what}: {len(vals)} seed(s) < required {min_seeds} — "
            "E0 协议禁止引用单/双 seed 结论")
    if any(math.isnan(v) for v in vals):
        raise ProtocolViolation(f"{what}: per-seed 值含 NaN")
    return vals


def bimodality_1d(values: Sequence[float]) -> Dict:
    """1-D 二分聚类双峰检测（简化 dip：最优二分 + 间隙比）。

    返回 {"bimodal": bool, "split_at": float|None, "gap_ratio": float,
          "groups": [[...], [...]]}。判定：类间间隙 / 类内散度 > 3.0
    **且**间隙 ≥ _MIN_BIMODAL_GAP（chance/满分两团中间是空带，间隙比
    极大；量化分数的相邻取值则两条判据都过不了——见 _MIN_BIMODAL_GAP
    的注释）。宁可多报（bimodal=True 只是"不得引用"，不是"扔数据"）。
    """
    vals = sorted(float(v) for v in values)
    if len(vals) < 4:
        return _unimodal_result(vals)
    best = _best_split(vals)
    if best is None:                       # 全同值: 无间隙, 单峰
        return _unimodal_result(vals)
    ratio, i = best
    gap = vals[i] - vals[i - 1]
    return {"bimodal": ratio > 3.0 and gap >= _MIN_BIMODAL_GAP,
            "split_at": (vals[i - 1] + vals[i]) / 2,
            "gap_ratio": round(ratio, 3), "groups": [vals[:i], vals[i:]]}


def forbid_bimodal(values: Sequence[float], what: str = "result") -> Dict:
    b = bimodality_1d(values)
    if b["bimodal"]:
        raise ProtocolViolation(
            f"{what}: per-seed 分布双峰 (gap_ratio={b['gap_ratio']}, "
            f"split@{b['split_at']:.3f}) — 掷硬币区, 数据不得引用; "
            "加 seeds/扩题集后重跑")
    return b


def publishable(a: Sequence[float], b: Sequence[float],
                min_seeds: int = 3, alpha: float = 0.05,
                tag: str = "") -> Tuple[bool, Dict]:
    """对照结果的"可引用"判定：≥min_seeds + 双臂非双峰 + 配对 p<alpha。

    返回 (ok, report)。ok=False 的结果**只能入档**（log + RESULTS.md 的
    Null/筛查区），不得写进 README/提交材料/对外表述。这是 E0 的全部
    执行语义。
    """
    report: Dict = {"tag": tag}
    reasons = _gate_reasons(a, b, min_seeds, alpha, tag, report)
    report["ok"] = not reasons
    report["reasons"] = reasons
    return (not reasons), report


def _best_split(vals: List[float]):
    """最优二分点：间隙/类内散度 最大的切分。返回 (ratio, idx)；全同值 None。"""
    best = None
    for i in range(1, len(vals)):
        gap = vals[i] - vals[i - 1]
        if gap <= 0:
            continue
        lo, hi = vals[:i], vals[i:]
        # 类内散度: 两组合并的 mean absolute deviation（尺度稳定）
        spread = sum(abs(v - _mean(g)) for g in (lo, hi) for v in g) / len(vals)
        ratio = gap / max(spread, 1e-12)
        if best is None or ratio > best[0]:
            best = (ratio, i)
    return best


def _as_floats(vals):
    """数值化一臂；含 None/非数值/NaN 返回 None（脏臂已由 seeds 门槛记因，
    后续门槛跳过——publishable 的任何路径都不允许因脏数据崩溃）。"""
    try:
        nums = [float(v) for v in vals]
    except (TypeError, ValueError):
        return None
    if any(math.isnan(x) for x in nums):
        return None
    return nums


def _gate_reasons(a, b, min_seeds, alpha, tag, report) -> List[str]:
    """三道门槛（seeds / 双峰 / 配对检验）的未过原因收集。"""
    reasons = []
    for name, vals in (("arm-a", a), ("arm-b", b)):
        try:
            require_min_seeds(vals, min_seeds, what=f"{tag} {name}")
        except ProtocolViolation as e:
            reasons.append(str(e))
    reasons += _bimodality_reasons(a, b, report)
    reasons += _sign_test_reasons(a, b, alpha, report)
    return reasons


def _bimodality_reasons(a, b, report) -> List[str]:
    reasons = []
    for name, vals in (("arm-a", a), ("arm-b", b)):
        nums = _as_floats(vals)
        if nums is None or len(nums) < 4:
            continue
        bm = bimodality_1d(nums)
        report[f"bimodality_{name}"] = bm
        if bm["bimodal"]:
            reasons.append(f"{name} 双峰 (gap_ratio={bm['gap_ratio']})")
    return reasons


def _sign_test_reasons(a, b, alpha, report) -> List[str]:
    if len(a) != len(b) or len(a) < 1:
        return ["两臂 seeds 不齐, 无法配对"]
    na, nb = _as_floats(a), _as_floats(b)
    if na is None or nb is None:
        return []
    st = paired_sign_test(na, nb)
    report["sign_test"] = st
    if st["p"] >= alpha:
        return [f"配对符号检验 p={st['p']:.3f} ≥ {alpha}"]
    return []


def _unimodal_result(vals: List[float]) -> Dict:
    return {"bimodal": False, "split_at": None, "gap_ratio": 0.0,
            "groups": [vals, []]}


def _mean(xs):
    return sum(xs) / len(xs)
