"""exp_halting_parity.py — R2 自适应停止（PonderNet 式 halt）合成任务实验.

方向：自适应停止与测试时计算（backlog P0'）。合成任务自带金标，全离线，
零 API 成本；这是类脑轴里唯一不依赖人工裁定的可跑方向。

任务：二进制串 parity（全串异或）。训练长度 U[8,32]；测试 in-dist U[8,32]、
OOD U[40,64]。两臂除"workspace block 迭代方式"外全同：
  arm-fixed    trunk 后 workspace block 恰好跑 1 次，直接读出（无 halt 头）。
  arm-adaptive workspace block 最多迭代 K=8，PonderNet 式 halt 头逐步累积
               预测（p_k = λ_k Π_{j<k}(1-λ_j)），halting 损失 = 与
               Geometric(p_g=0.25) 先验的交叉熵，β=0.05；总损失 = CE + β·L_halting。

预注册（先于任何运行落盘；同步见 docs/PREREGISTRATION.md 附录 R2）：

  最终对比（多种子阶段，非本轮）：指标 = OOD accuracy（per-seed 配对），
  判优 = publishable(per_seed_adaptive, per_seed_fixed) 为 True
  （≥3 seeds、双臂非双峰、配对符号检验 p<0.05）；判负则 adaptive 入
  docs/RESULTS.md 筛查区，方向 REJECTED（留痕），不进毕业流程。

  本轮 screening（seed=1 单种子）go/no-go（跑之前写死）：
  G1 确定性：arm-fixed 同 seed 连跑两次，JSON 指标逐字段一致。
  G2 学习信号：两臂 in-dist test accuracy ≥ 0.55（二分类 chance=0.5）。
     低于 → 判"任务/容量欠配"，下一轮调容量重筛，不进入多种子。
  G3 halt 不坍缩：arm-adaptive 平均停步数 E[k] ∈ [1.3, 7.7]，无 NaN。
  G4 算力预算：单臂 wall time ≤ 10 min（2 臂 × 5 seeds ≈ ≤100 min；
     >60 min 则多种子阶段按算力政策转 Kaggle，本机不硬跑）。

  G1–G4 全过 → 多种子阶段放行；任一不过 → 如实记录原因，下一轮修
  （改判负标准本身须走预注册修订 + 人工确认）。

确定性纪律：CPU-only、torch.use_deterministic_algorithms(True)、全部随机
源走显式 torch.Generator(seed)、PYTHONHASHSEED 钉 0（子进程同理）。

用法：
    .venv/bin/python research/exp_halting_parity.py --arm fixed --seed 1 \
        --steps 1200 --out benchmarks/results/r2_halting_smoke_<date>_r1.json
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


def make_batch(gen: torch.Generator, lo: int, hi: int, n: int):    lens = torch.randint(lo, hi + 1, (n,), generator=gen)
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
        self.tok = nn.Embedding(2, D_MODEL)
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

    def forward(self, x, mask):
        n, L = x.shape
        pos = torch.arange(L, device=x.device).unsqueeze(0).expand(n, -1)
        h = self.trunk(self.tok(x) + self.pos(pos), mask)
        if not self.adaptive:
            return self.head(self._pool(self.workspace(h, mask), mask)), None
        halted = torch.zeros(n, dtype=torch.bool)
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


def evaluate(model, gen, lo, hi, n=512):
    model.eval()
    x, mask, y = make_batch(gen, lo, hi, n)
    with torch.no_grad():
        logits, halt = model(x, mask)
        acc = (logits.argmax(1) == y).float().mean().item()
        mean_steps = None
        if halt is not None:
            lam_list, p_list, p_remain = halt
            ks = torch.arange(1, K_STEPS + 1, dtype=torch.float32).unsqueeze(1)
            mean_steps = float((p_list * ks).sum(0).add(p_remain * K_STEPS).mean().item())
    model.train()
    return acc, mean_steps


def main() -> int:
    ap = argparse.ArgumentParser()
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
        x, mask, y = make_batch(gen_data, lo, hi, BATCH)
        logits, halt = model(x, mask)
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

    indist, mean_steps = evaluate(model, gen_eval_in, 8, 32)
    ood, _ = evaluate(model, gen_eval_ood, 40, 64)
    result = {
        "exp": "r2_halting_parity",
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
