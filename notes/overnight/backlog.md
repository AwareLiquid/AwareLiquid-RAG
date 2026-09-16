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

## P0 — R1 multi-seed 消融：lexical vs hybrid（含 multi-query），100 题标注集 [SCREENING]

- 动机：主干上真正的首个"能力对比"问题——hybrid（dense+e5+BM25+RRF）相对纯 lexical 到底是提升还是负担？
  仓库里只有 8 题 `--fake` 筛查计数（7/8→8/8），从未在 100 题集上跑过，更没过 `publishable()` 门。
  这是所有类脑模块毕业时都要对照的基线，没有它一切"提升"都无从谈起。
- 预注册：`docs/PREREGISTRATION.md` 附录 R1（2026-09-11，已落盘）。
- 两臂：arm-a = `retrieval_backend="lexical"`；arm-b = `retrieval_backend="hybrid"`（向量 path；需 e5 模型下载）。
- 判据：100 题 × ≥3 seeds，指标 answer accuracy（mock 后端下为 pipeline 有效性代理指标，如实标注）；
  判优 = b 各 seed 均 ≥ a 且配对符号检验 p<0.05；判负 = b 未显著优于 a → hybrid 维持 research-only，不动默认路径。
- 运行计划：本机先跑单 seed 超小冒烟（≤1h）；e5 下载 + 全量多 seed 若超 1h 则走 Kaggle CPU notebook（通道 UNVERIFIED→ 先验证通道）。
- 状态：PREREG 已落盘；SCREENING 待跑。

## P1 — R0 回归锁：重跑 bench --fake，确认合并后行为与旧证据一致 [SCREENING]

- 动机：`overnight/loop` 建分支时把 `origin/main`（48 题评估管线 + 检索增强）与
  `origin/feat/evidence-governance`（8 题 bench + E0 门）合并，`bench_adapter.build_agent` 曾短暂损坏已修复。
  跑一次 `--fake` 单 seed，确认 `RESULT: PASS` 且数字与 `docs/RESULTS.md` PROVEN 表一致（recall@4 8/8、retention 8/8、1254 vs 22668）。
- 判据：输出与 `benchmarks/results/bench_adapter_fake_20260906_r1.log` 关键行一致；不一致则开事故记录并修 bench，不动 RESULTS 既有行。
- 运行计划：本机 `PYTHONHASHSEED=1 .venv/bin/python benchmarks/bench_adapter.py --fake`（分钟级）。
- 状态：待跑（即本轮 R0）。

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
