# M2 类脑推理实验室 — 夜间循环 backlog（2026-09-11 建）

> 头注（每轮先读）：
> - 状态机：`IDEA → PREREG → SCREENING → MULTI-SEED → GRADUATION-CANDIDATE →（人工合并 main）→ GRADUATED`；
>   `PAUSED（通道/依赖缺）`、`REJECTED（判负入筛查区）` 为终态分支，判负留痕不删除。
> - 毕业看板：见本文件末尾。毕业硬门槛 = 多种子消融 + 预注册基准上明确提升 +
>   `benchmarks/experiment_protocol.py::publishable()` 过门；过门只给 `GRADUATION-CANDIDATE` + 开 PR，合并一律人工。
> - 价值排序：对 100 题标注集（`data/questions/group_a/*.json`，5 域 ×20 题）的能力提升潜力 > 消融科学价值 > 工程摩擦清偿。
> - Kaggle 通道状态（2026-09-11）：`kaggle` CLI 未装（`pip install kaggle` 即有，需 `~/.kaggle/kaggle.json` 凭证——当前缺凭证）；
>   CPU notebook / T4 双通道均 **UNVERIFIED**。配额账本：T4 ~30h/周×双账号（未动用，未记账）；余量 <6h 自动冻结。
> - 算力政策：本机（M2 Max 12 核）只跑预计 ≤1h 的任务（探针、冒烟、验收门、单文件小修）；
>   >1h 训练/批量一律走 Kaggle。`runs/*.pid` 当前无遗留长跑。
> - 文献扫描状态（2026-09-11）：Web 搜索配额耗尽（重置 2026-09-24），本轮方向定级基于训练知识 + 仓库内证据，
>   标记为 `PRELIM（待 9/24 后复核）`；禁止把 PRELIM 定级当引用结论。
> - 证据纪律：`docs/RESULTS.md` 为唯一事实源，只追加不改既有判定行；单 seed 结果只入筛查区；
>   新结果 JSON/日志入 `benchmarks/results/`（命名 `<实验>_<日期>_r<轮>.{json,log}`）；提交动词 `prereg:→bench:→results:→docs:`。

## P0 — R1 multi-seed 消融：lexical vs hybrid（含 multi-query），100 题标注集 [BLOCKED-HUMAN 2026-09-16]

- 动机：主干上真正的首个"能力对比"问题——hybrid（dense+e5+BM25+RRF）相对纯 lexical 到底是提升还是负担？
  仓库里只有 8 题 `--fake` 筛查计数（7/8→8/8），从未在标注集上跑过，更没过 `publishable()` 门。
  这是所有类脑模块毕业时都要对照的基线，没有它一切"提升"都无从谈起。
- 预注册：`docs/PREREGISTRATION.md` 附录 R1（2026-09-11，已落盘）。
- **2026-09-16 冒烟发现两个硬阻塞（需人工裁定，见晨报）：**
  1. **预注册题集无标注**：`data/questions/group_a/*.json` 100/100 题全部没有 `answer` 字段（竞赛题，
     答案未随题下发）——预注册指标"answer accuracy vs 标注答案"在该题集上**不可计算**。
     但仓库存在另一套完整标注集：`evals/questions.jsonl`（48 题、48 个金标、5 域、corpus 为现成 md，
     `evals/run_eval.py` 驱动；其自述定位为"管线回归基线，非真实难度"）。
  2. **mock 后端答案退化**：`MockChatClient` 只回第一个选项（代码+`evals/run_eval.py` 文档双重确认），
     离线 accuracy 对检索质量不敏感（实测 mock 48 题 13/48=27.1%，即 echo-first 基线）。
     有效对比必须真实 Qwen key 计费跑：48 题 ≈ 16.6 万 token/轮（mock 估算口径）。
- 已完成的工程清偿：`evals/run_eval.py` 新增 `--retrieval-backend {lexical,hybrid}` 开关
  （R1 两臂入口，mock 冒烟验证过）；e5 hybrid 臂可行性 = transformers 5.14.1 已装、HF 可达（首次需下 ~500MB 模型）。
- 人工裁定项：**（a）换题集**——预注册题集 100 题无标注 → 改为 `evals/` 48 题标注集（即刻可跑）
  或先造 100 题金标（长期更好，需标注工作）；**（b）计费授权**——是否允许用 `.env` 里的真实
  Qwen key 跑 evals（每轮 ≈16.6 万 token）。两项都批 → 下轮改预注册附录（换题集 + 后端口径）后开跑。
- 状态：**BLOCKED-HUMAN**（不占本机，不烧 API；等裁定）。

## P1 — R0 回归锁：重跑 bench --fake，确认合并后行为与旧证据一致 [REJECTED→已闭环 2026-09-11]

- 动机：`overnight/loop` 建分支时把 `origin/main`（48 题评估管线 + 检索增强）与
  `origin/feat/evidence-governance`（8 题 bench + E0 门）合并，`bench_adapter.build_agent` 曾短暂损坏已修复。
  跑一次 `--fake` 单 seed，确认 `RESULT: PASS` 且数字与 `docs/RESULTS.md` PROVEN 表一致（recall@4 8/8、retention 8/8、1254 vs 22668）。
- 判据：输出与 `benchmarks/results/bench_adapter_fake_20260906_r1.log` 关键行一致；不一致则开事故记录并修 bench，不动 RESULTS 既有行。
- 运行计划：本机 `PYTHONHASHSEED=1 .venv/bin/python benchmarks/bench_adapter.py --fake`（分钟级）。
- 状态：**已闭环（2026-09-11 R0）**：输出与旧日志逐字节一致（`benchmarks/results/r0_bench_fake_20260911_r1.log`）。

## P0' — 自适应停止（PonderNet 式 halt）合成任务消融 [SCREENING NO-GO ×3（至 2026-09-17）；#4=阶梯终局]

- 预注册：`docs/PREREGISTRATION.md` 附录 R2 及 screening 序节；脚本 `research/exp_halting_parity.py`。
- screening #1（parity, 1200 步）：NO-GO——两臂 chance、halt 坍缩（详见附录与晨报 09-16 档）。
- screening #2（parity, 6000 步+课程+bias）：NO-GO——容量校准无效，loss 卡 ln2。
- **screening #3（prefix_parity, 6000 步）：NO-GO ×3，但 G2 首次 PASS**（证据
  `benchmarks/results/r2_halting_prefix_20260917_r3.log`）：任务学会了（fixed in-dist
  0.666、短前缀桶 0.83-0.87），可 halt 仍坍缩（mean_steps 1.028）——任务 CE 下额外
  迭代无净收益，早停是 halt 头的理性行为。分桶：fixed 长前缀桶 0.324 vs adaptive
  0.588（单 seed，仅方向性）。
- **下轮 = screening #4（阶梯终局步）**：progressive-reveal——迭代 k 只能看到前
  ⌈k/K·L⌉ 位，结构上强制"单步不足以答长前缀"；配置下轮落盘后运行。
  **结局规则（已在附录落盘生效）**：#4 G3 再败 → P0' REJECTED（机制级阴性结果），
  主轴转 latent-workspace recurrent（固定深度循环，不依赖可学习停步）；全过 → 多种子。
- 依赖：无（纯 torch 合成数据，全离线）；与 R1 人工裁定全解耦。

## P2 — 工程：Kaggle 通道验证（CLI 安装 + 凭证 + CPU notebook hello-world）[IDEA]

- 动机：所有 >1h 任务的唯一出口，但 CLI 未装、凭证缺、双通道 UNVERIFIED。R1 全量很可能需要它。
- 痛点：装 CLI 要动 `.venv`（单文件小修级，可做）；凭证 `~/.kaggle/kaggle.json` 需 AricRedemption 人工提供 → 可能转人工判定。
- 状态：IDEA；R1 冒烟确认耗时后再决定是否本轮做。

## P3 — 方向定级（PRELIM，待 9/24 复核）：类脑模块迁入顺序 [IDEA]

| 模块 | 定级 | 一句话理由 |
|---|---|---|
| 自适应停止 + 测试时计算（ACT/PonderNet 式 halt，depth 冒烟） | ★ 首个科研方向 | 与"token 预算下多做推理"的主目标直接对齐；可在检索-压缩-回答环路上做 depth 消融，不依赖大训练；失败模式已知（PonderNet 复现难、halt 坍缩）→ 预注册先写防坍缩判据。 |
| latent workspace recurrent reasoning（core/stack iterations） | ★ 并列 | Geiping 式 latent recurrent depth 已在推理任务上验证过 test-time scaling；迁入形态 = 在 compressor/answer 间加 recurrent refine block + iteration 消融。需小训练 → 大概率走 Kaggle。 |
| predictive world model（预测式重排/压缩验证） | ☆ 次轮 | 用下一句/掩码预测分数做 passage 重排信号，纯本地可跑；但与 BM25 强基线的差异需先做 screening。 |
| GWTB / workspace iterations、Global Coherence、global rhythm | ☆ 次轮 | 概念大、落地形态需先形式化（shared workspace tensor + broadcast 迭代）；先写设计预注册再谈实验。 |
| Orch-OR top-down modulation | ◇ 后轮 | 调制语义模糊，先文献复核（等 9/24 配额）再立项，避免玄学模块。 |
| astrocyte / Hebbian / consciousness metrics | ◇ 后轮 | Hebbian 外环更新与度量（Φ近似、整合度量）科学价值高但对 100 题准确率提升链路最长；放后轮。 |
| Hamiltonian world model | ◇ 后轮 | 能量形式化漂亮但工程映射不明；等 predictive 先探路。 |

## 毕业看板

- GRADUATION-CANDIDATE：（空）
- GRADUATED：（空）
- REJECTED：（空）
