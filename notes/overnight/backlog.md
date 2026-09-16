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

## P0' — 自适应停止（PonderNet 式 halt）合成任务消融 [REJECTED 2026-09-17（机制级阴性，5 seeds）]

- 全链留痕：4 轮 screening（#1 parity→NO-GO；#2 +课程/6k 步→NO-GO；#3 prefix-parity→
  G2 首过但 halt 坍缩；#4 progressive-reveal→G1–G4 全过）+ 5 seeds 多种子终判。
- **终判 REJECTED**：`publishable()` 判负——OOD acc adaptive **0/5 胜** fixed
  （配对符号检验 p=0.0625；adaptive [0.547,0.551,0.502,0.555,0.502] vs fixed
  [0.553,0.572,0.514,0.566,0.537]）；mean_steps 各种子 ≈2.00（固定预算，非逐例自适应）。
  已入 `docs/RESULTS.md` 筛查区（REJECTED 2026-09-17 行）。
- 结论：本规模/本读出结构下，可学习停步无净收益——"多想"必须在结构上被强制
  （progressive-reveal 做到了），但强制后的统一 2 步预算说明 halt 头学到的仍是
  策略常量而非按需分配。**可作为 M1 类结论引用（过 E0 门的阴性结果）。**
- 可复用资产：`research/exp_halting_parity.py`（双臂双任务确定性骨架，后续方向直接复用）。

## P0'' — latent workspace recurrent（固定深度循环）[REJECTED 2026-09-17（5 seeds，筛查区有行）]

- 预注册 R3（2026-09-17 落盘后运行）：k∈{1,8}×5 seeds 主门 + k∈{2,4}×3 曲线诊断。
- **终判 REJECTED**：`publishable(k8_ood, k1_ood)` 判负——k8 1/5 胜（p=0.375）；
  OOD 曲线平坦（均值 0.548/0.548/0.551/0.534），in-dist k=2 见顶（0.655→0.695→0.697→0.676）。
  结论：深度收益限于训练分布内拟合，不转化为长度外推；固定步数下 k=8 优化更难。
- 跨轮确定性对账：k=1 seed1 逐比特复现 R2 fixed_s1 档案（架构重构未扰动基线）。
- 与 R2 合并读出的轴级结论：**在 pooled-readout 小模型 + 合成 prefix-parity 上，
  迭代/深度/停步三类"测试时计算"机制均无净收益**——该 setup 对类脑机制不构成
  有效的压力测试场，后续类脑方向需换更大的任务/模型规模才有区分度。

## P4 — 测试场灵敏度校准（R4 阳性对照）[已执行 2026-09-17：**测试场冻结**]

- 定级结论：真实基准被人工判定项阻塞 → 先回答"R2/R3 阴性是机制问题还是测试场问题"。
  R4 = 阳性对照（层级分块聚合，构造上匹配 parity 复合结构，应当赢平铺池化）。
- **R4 判负**：hier 3/5 胜 flat（p=1.0），长前缀桶 0.511 vs 0.486（噪声）。
  连构造上应分离的对照都分不开 → **合成测试场对机制研究无区分度，冻结**
  （证据：`benchmarks/results/r4_arch_control_20260917_summary.json`）。
- P3 表中其余机制（predictive/GWTB/Hebbian 等）在冻结测试场上暂不可测——
  全部依赖下述人工裁定的去向。

## 【停靠点 2026-09-17】方向池进入人工判定——决策包

合成轴冻结后，所有剩余路径都汇到同一组人工决策（循环已无可自主推进的科研方向）：

- **选项 1（推荐）**：批准 R1' —— 预注册新实验换用 `evals/` 48 题标注集
  （5 域、金标齐全、corpus 现成）+ 授权 `.env` 真实 Qwen key 计费跑
  （~16.6 万 token/轮）。批准后循环恢复：lexical vs hybrid（R1 原问题）
  在真实基准上过 E0 门，类脑模块此后在该基准上受测。
- **选项 2**：授权合成升级（d≥192、2 层 trunk、多跳/组合任务，预计 >1h →
  需选项 3 的 Kaggle 通道）。R4 提示希望渺茫，不推荐。
- **选项 3**：提供 Kaggle 凭证（`~/.kaggle/kaggle.json`）+ 装 CLI —— 任何 >1h
  实验的前置，独立有效。
- 其余三项登记事项（evidence-governance PR 去留 / 夜间防睡眠 / notes 私有化）不变。

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
- REJECTED：P0' 自适应停止（PonderNet 式 halt）——2026-09-17，5 seeds 0/5，p=0.0625；P0'' latent recurrent depth——2026-09-17，5 seeds 1/5，p=0.375（均有筛查区行）
