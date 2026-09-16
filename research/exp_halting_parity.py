"""exp_halting_parity.py — R2 自适应停止（PonderNet 式 halt）合成任务实验.

方向：自适应停止与测试时计算（backlog P0'）。合成任务自带金标，全离线，
零 API 成本。

任务（--task）：
  parity         全串异或（screening #1/#2 的任务，原样保留以复现旧档）。
  prefix_parity  查询位置前缀异或（screening #3，2026-09-17 起）：输入 bits +
                 查询位标记（id=2 叠加在 qpos 位置），目标 = bits[0:qpos+1] 的
                 异或。每个迭代步对应明确的前缀扩展增益，难度随 q 连续变化，
                 halt 头第一次有真实的"多想一步"收益结构；短前缀样本（q 小）
                 天然构成课程。

两臂（除 workspace 迭代方式外全同）：
  arm-fixed    trunk 后 workspace block 恰好跑 1 次，直接读出（无 halt 头）。
  arm-adaptive workspace block 最多迭代 K=8，PonderNet 式 halt 头逐步累积
               预测，halting 损失 = 与 Geometric(p_g=0.25) 先验的交叉熵，
               β=0.05；总损失 = CE + β·L_halting。

预注册：docs/PREREGISTRATION.md 附录 R2 及其 screening 序节。当前生效：
screening #3 配置（2026-09-17 落盘）——task=prefix_parity，6000 步，长度课程
（前 70% 步 L∈[4,16]，后 30% 步 L∈[8,32]），halt bias -2；判据 G1–G4 不变：
  G1 确定性（arm-fixed 同 seed 两跑，除 wall_s 外逐字段一致；文件缺失不得判 PASS）；
  G2 两臂 in-dist acc ≥ 0.55；G3 adaptive 平均停步 E[k] ∈ [1.3, 7.7] 且无 NaN；
  G4 单臂 wall ≤ 10 min。全过 → 多种子放行（seeds≥3，publishable 门）。

确定性纪律：CPU-only、torch.use_deterministic_algorithms(True)、全部随机源走
显式 torch.Generator(seed)、PYTHONHASHSEED 钉 0。运行前必须过 py_compile。

用法：
    .venv/bin/python research/exp_halting_parity.py --task prefix_parity \
        --arm adaptive --seed 1 --steps 6000 --out <path>.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("PYTHONHASHSEED", "0")

import torch
from torch import nn

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

D_MODEL = 96
N_HEADS = 2
MAX_LEN = 64
K_STEPS = 8
BETA = 0.05
PRIOR_P = 0.25
LR = 1e-3
BATCH = 64
QUERY_ID = 2


def make_batch(gen: torch.Generator, lo: int, hi: int, n: int):
    lens = torch.randint(lo, hi + 1, (n,), generator=gen)
    maxlen = int(lens.max())
    x = torch.zeros(n, maxlen, dtype=torch.long)
    mask = torch.zeros(n, maxlen, dtype=torch.bool)
    for i, L in enumerate(lens.tolist()):
        bits = torch.randint(0, 2, (L,), generator=gen)
        x[i, :L] = bits
        mask[i, :L] = True
    parity = torch.zeros(n, dtype=torch.long)
    for i, L in enumerate(lens.tolist()):
        parity[i] = int(x[i, :L].sum().item()) % 2
    return x, mask, parity


def make_prefix_batch(gen: torch.Generator, lo: int, hi: int, n: int):
    """prefix parity：目标 = bits[0:qpos+1] 的异或（标记位含入前缀）。"""
    lens = torch.randint(lo, hi + 1, (n,), generator=gen)
    maxlen = int(lens.max())
    x = torch.zeros(n, maxlen, dtype=torch.long)
    mask = torch.zeros(n, maxlen, dtype=torch.bool)
    qpos = torch.zeros(n, dtype=torch.long)
    target = torch.zeros(n, dtype=torch.long)
    for i, L in enumerate(lens.tolist()):
        bits = torch.randint(0, 2, (L,), generator=gen)
        q = int(torch.randint(1, L + 1, (1,), generator=gen))
        x[i, :L] = bits
        mask[i, :L] = True
        qpos[i] = q - 1
        target[i] = int(bits[:q].sum().item()) % 2
    return x, mask, qpos, target


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.ln1 = nn.LayerNorm(D_MODEL)
        self.attn = nn.MultiheadAttention(D_MODEL, N_HEADS, batch_first=True)
        self.ln2 = nn.LayerNorm(D_MODEL)
        self.mlp = nn.Sequential(
            nn.Linear(D_MODEL, 2 * D_MODEL), nn.GELU(), nn.Linear(2 * D_MODEL, D_MODEL)
        )

    def forward(self, h, mask):
        key_padding = ~mask
        a, _ = self.attn(self.ln1(h), self.ln1(h), self.ln1(h),
                         key_padding_mask=key_padding, need_weights=False)
        h = h + a
        h = h + self.mlp(self.ln2(h))
        return h


class HaltingNet(nn.Module):
    def __init__(self, adaptive: bool):
        super().__init__()
        self.tok = nn.Embedding(3, D_MODEL)  # 0/1 bit；id2 仅作查询标记向量
        self.pos = nn.Embedding(MAX_LEN, D_MODEL)
        self.trunk = Block()
        self.workspace = Block()
        self.head = nn.Linear(D_MODEL, 2)
        self.adaptive = adaptive
        if adaptive:
            self.halt = nn.Linear(D_MODEL, 1)
            # 初始停步质量按 Geometric(0.12) 铺开：若 λ 初始接近 1，第 1 步独吞全部
            # 预测质量，后续迭代收不到梯度、永远死掉（screening #1 坍缩到 1.01 步）。
            nn.init.constant_(self.halt.bias, -2.0)

    @staticmethod
    def _pool(h, mask):
        # masked mean over sequence -> one vector per example (readout + halt both
        # act per example, not per position).
        summed = (h * mask.unsqueeze(-1)).sum(1)
        return summed / mask.sum(1, keepdim=True).clamp(min=1)

    def forward(self, x, mask, qpos=None):
        n, L = x.shape
        pos = torch.arange(L, device=x.device).unsqueeze(0).expand(n, -1)
        emb = self.tok(x)
        if qpos is not None:
            marker = torch.zeros_like(emb)
            marker[torch.arange(n), qpos] = 1.0
            emb = emb + marker * self.tok.weight[QUERY_ID]
        h = self.trunk(emb + self.pos(pos), mask)
        if not self.adaptive:
            return self.head(self._pool(self.workspace(h, mask), mask)), None
        acc = torch.zeros(n, 2)
        lam_list, p_list = [], []
        prev = torch.ones(n)
        state = h
        pooled = self._pool(state, mask)
        for _ in range(K_STEPS):
            state = self.workspace(state, mask)
            pooled = self._pool(state, mask)
            lam = torch.sigmoid(self.halt(pooled)).squeeze(-1)  # (n,)
            lam_list.append(lam)
            p_k = lam * prev
            p_list.append(p_k)
            acc = acc + p_k.unsqueeze(1) * self.head(pooled)
            prev = prev * (1 - lam)
        p_remain = prev  # 未停质量留在第 K 步
        acc = acc + p_remain.unsqueeze(1) * self.head(pooled)
        return acc, (torch.stack(lam_list, 0), torch.stack(p_list, 0), p_remain)


def halting_loss(p_list, p_remain):
    # PonderNet: 与 Geometric(PRIOR_P) 先验的交叉熵（log-domain 等价 KL 的 CE 项）。
    K = p_list.shape[0]
    n = p_list.shape[1]
    losses = []
    for k in range(K):
        g_k = (1 - PRIOR_P) ** k * PRIOR_P
        losses.append((p_list[k] * (-torch.log(torch.tensor(g_k)))).sum() / n)
    g_g = (1 - PRIOR_P) ** K
    losses.append((p_remain * (-torch.log(torch.tensor(g_g)))).sum() / n)
    return torch.stack(losses).sum()


def _bucket_of(q: torch.Tensor):
    """q≤8 / 9-24 / ≥25 → 0/1/2（难度分档诊断）。"""
    return torch.where(q <= 8, torch.zeros_like(q),
                       torch.where(q <= 24, torch.ones_like(q), torch.full_like(q, 2)))


def evaluate(model, gen, lo, hi, n, task):
    model.eval()
    qpos = None
    if task == "parity":
        x, mask, y = make_batch(gen, lo, hi, n)
    else:
        x, mask, qpos, y = make_prefix_batch(gen, lo, hi, n)
    with torch.no_grad():
        logits, halt = model(x, mask, qpos)
        hit = (logits.argmax(1) == y)
        acc = hit.float().mean().item()
        buckets = None
        if task != "parity":
            b = _bucket_of(qpos + 1)
            buckets = {}
            for bi in range(3):
                sel = b == bi
                buckets[f"q_bucket_{bi}"] = {
                    "n": int(sel.sum()),
                    "acc": hit[sel].float().mean().item() if int(sel.sum()) else None,
                }
        mean_steps = None
        if halt is not None:
            lam_list, p_list, p_remain = halt
            ks = torch.arange(1, K_STEPS + 1, dtype=torch.float32).unsqueeze(1)
            steps = (p_list * ks).sum(0).add(p_remain * K_STEPS)
            mean_steps = float(steps.mean().item())
            if buckets is not None:
                for bi in range(3):
                    sel = _bucket_of(qpos + 1) == bi
                    buckets[f"q_bucket_{bi}"]["mean_steps"] = (
                        float(steps[sel].mean().item()) if int(sel.sum()) else None
                    )
    model.train()
    return acc, mean_steps, buckets


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=("parity", "prefix_parity"), default="parity")
    ap.add_argument("--arm", choices=("fixed", "adaptive"), required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--steps", type=int, default=1200)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()

    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(2)
    torch.manual_seed(args.seed)
    gen = torch.Generator().manual_seed(args.seed)
    gen_data = torch.Generator().manual_seed(args.seed)
    gen_eval_in = torch.Generator().manual_seed(9001)
    gen_eval_ood = torch.Generator().manual_seed(9002)

    model = HaltingNet(adaptive=(args.arm == "adaptive"))
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    t0 = time.time()
    curriculum_until = int(0.7 * args.steps)  # 长度课程：前期短串（易），后期全量 [8,32]
    for step in range(1, args.steps + 1):
        lo, hi = (4, 16) if step <= curriculum_until else (8, 32)
        qpos = None
        if args.task == "parity":
            x, mask, y = make_batch(gen_data, lo, hi, BATCH)
        else:
            x, mask, qpos, y = make_prefix_batch(gen_data, lo, hi, BATCH)
        logits, halt = model(x, mask, qpos)
        loss = nn.functional.cross_entropy(logits, y)
        if halt is not None:
            lam_list, p_list, p_remain = halt
            loss = loss + BETA * halting_loss(p_list, p_remain)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        if step % 300 == 0 or step == 1:
            print(f"step {step:5d} loss {loss.item():.4f}", flush=True)
    wall = time.time() - t0

    indist, mean_steps, buckets_in = evaluate(model, gen_eval_in, 8, 32, 512, args.task)
    ood, _, buckets_ood = evaluate(model, gen_eval_ood, 40, 64, 512, args.task)
    result = {
        "exp": "r2_halting_parity",
        "task": args.task,
        "arm": args.arm,
        "seed": args.seed,
        "steps": args.steps,
        "d_model": D_MODEL,
        "K": K_STEPS,
        "beta": BETA,
        "prior_p": PRIOR_P,
        "curriculum": True,
        "curriculum_split": "first 70% steps L in [4,16], then [8,32]",
        "halt_bias_init": -2.0 if args.arm == "adaptive" else None,
        "train_loss_last": float(loss.item()),
        "indist_acc": indist,
        "ood_acc": ood,
        "mean_steps": mean_steps,
        "buckets_indist": buckets_in,
        "buckets_ood": buckets_ood,
        "wall_s": round(wall, 1),
        "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
        "torch_version": torch.__version__,
    }
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
