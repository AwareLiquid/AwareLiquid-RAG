# 预注册制度（Pre-registration）

借鉴 M1 仓库（MT-LNN）的纪律：**判定规则写死于代码、先于结果落盘**。
目的：防止结果出来后再"反向定制"判优标准（结果驱动的规则改动会让任何
结论都不可信）。

## 规则

1. **先落盘，后运行**：每次对照实验（新策略 vs 现状、A vs B）在跑之前，
   判定规则必须先写进实验脚本的 docstring 或本文件附录——精确到比较
   指标、方向和阈值。先提交（commit message 用 `prereg:` 前缀），再跑。
2. **判负也归档**：判负/无效结果同样写入 `docs/RESULTS.md` 的
   SUPERSEDED / 筛查区（留痕不删除），不得静默丢弃。
3. **引用门槛**：对外引用对照结论前必须过
   `benchmarks/experiment_protocol.py::publishable`（≥3 seeds、非双峰、
   配对 p<0.05）。过不了门的结果只能入档，不能引用。
4. **不做清单**：证据已闭环的问题不得无新证据重开（见下）。
5. **提交动词纪律**（M1 五段式，按需取用）：
   `prereg:`（规则先落盘）→ `bench:`（运行脚本/口径）→ `results:`
   （结果，含判负）→ `docs:`（RESULTS.md 归档）。

## 不做清单（证据已闭环，无新证据不得重开）

- 检索/编码路径**不得回退到内建 `hash()`**：盐随进程随机，跨进程不可
  复现（2026-09-06 bench 数字漂移事故的根因；修复见
  `benchmarks/bench_adapter.py` 与 `tests/conftest.py`）。
- 单次运行 bench 计数**不得写进对外材料**：只作筛查/smoke；要引用就扩
  多 seed / 多题集并过 `publishable()` 门（`docs/RESULTS.md` 证据政策）。
- `.sha256` sidecar **必须是磁盘字节的哈希**（`raw_hash(path)`），不得
  用 `object_hash`（canonical compact JSON）代替：落盘是 pretty-print
  形式，两者必然失配（2026-09-06 校验器首跑抓到 66 处，全部验证等价后
  重写；管线出处 `scripts/bootstrap_a1_terra_r1.py` 的 `sidecar()` 调用
  点混用两种哈希）。

## 预注册模板

```markdown
## [实验名] — YYYY-MM-DD

- 动机：一句话（预期证伪/证实什么）。
- 两臂：arm-a = <配置>；arm-b = <配置>（除被测变量外全同）。
- 预注册判据（跑之前写死）：
  - 指标：<如 recall@4 / retention / token 用量>
  - 判优规则：<如 arm-a 各题 >= arm-b 且配对符号检验 p<0.05 判 a 胜>
  - 判负处置：<判负后写入 RESULTS.md 筛查区，不做 X>
- 运行计划：seeds/题集/环境；结果归档位置（log/json 路径约定）。
- 结果（跑完填）：数字 + publishable() 输出 + verdict。
```

## R1：lexical vs hybrid（含 multi-query）100 题多种子消融 — 2026-09-11

- 动机：一句话：hybrid（dense e5 + BM25 + RRF）相对纯 lexical 在 100 题标注集上是否真实提升回答能力（现只有 8 题 --fake 筛查计数，无多 seed、无显著性）。
- 两臂：arm-a = `RetrievalConfig(retrieval_backend="lexical")`；arm-b = `RetrievalConfig(retrieval_backend="hybrid")`
  （其余配置全同：`max_chars=450, overlap_chars=80, top_k=6, compression_budget=3000` 等默认；chat 后端 = MockChatClient 离线）。
- 预注册判据（跑之前写死）：
  - 指标：100 题 answer accuracy（accuracy = 解析答案字母 == 标注答案；mock 后端下此为 pipeline 有效性代理指标，结果中如实标注，不作真实准确率引用）。
  - 判优规则：arm-b 在 ≥3 seeds 上每 seed accuracy 均 ≥ arm-a，且配对符号检验（per-question 0/1 配对，`paired_sign_test`）p<0.05 → 判 b 胜（hybrid 保持研究候选，考虑后续优化默认路径）。
  - 判负规则：任一 seed 上 b < a，或 p≥0.05，或双臂任一双峰 → 判负：hybrid 维持 research-only，默认路径不动；结果入 `docs/RESULTS.md` 筛查区。
  - 判负处置：判负后不做默认路径切换、不开毕业 PR；只归档 + backlog 标 REJECTED（留痕）。
- 运行计划：seeds = 3（PYTHONHASHSEED 区分进程盐 + FakeEncoder/模型内 seed 位）；
  题集 = `data/questions/group_a/*.json`（5 域 ×20 题 = 100 题，需 docs 数据装配器，待 R0 后确认）；
  环境 = 本机冒烟（单 seed 超小子集，≤1h）→ 全量若 >1h 则走 Kaggle CPU notebook（通道待验证）；
  结果归档 `benchmarks/results/r1_lexical_vs_hybrid_<日期>_r<轮>.{json,log}`。
- 结果（跑完填）：（待填）数字 + publishable() 输出 + verdict。

## R2：自适应停止（PonderNet 式 halt）合成 parity 消融 — 2026-09-16

- 动机：类脑轴（自适应停止与测试时计算）首个自带金标的对照实验：迭代 + 学到的停步
  相对固定深度是否提升长度外推能力（OOD parity）。
- 两臂：arm-fixed = trunk 后 workspace block 恰 1 次、无 halt 头；
  arm-adaptive = 同一 block 最多迭代 K=8 + PonderNet 停步（Geometric(0.25) 先验、β=0.05）。
  其余（d=96、batch 64、AdamW lr 1e-3、1200 步、CPU 确定性）全同；脚本
  `research/exp_halting_parity.py`（预注册同步写死于其 docstring）。
- 预注册判据（跑之前写死）：
  - 最终指标：OOD accuracy（per-seed 配对）；判优 =
    `publishable(per_seed_adaptive, per_seed_fixed)` 为 True；判负入 `docs/RESULTS.md`
    筛查区，方向 REJECTED（留痕），不进毕业流程。
  - 本轮 screening（seed=1）go/no-go：G1 确定性（arm-fixed 同 seed 两跑逐字段一致）；
    G2 两臂 in-dist acc ≥ 0.55；G3 adaptive 平均停步 E[k] ∈ [1.3, 7.7] 且无 NaN；
    G4 单臂 wall ≤ 10 min。全过 → 多种子放行（seeds=3 起，5 更佳；若 2臂×5seeds
    预计 >60 min 则多种子按算力政策转 Kaggle）；任一不过 → 如实归档原因，
    下一轮修后再筛；修改判据本身须预注册修订 + 人工确认。
- 运行计划：本机冒烟（≤1h 内）；结果归档 `benchmarks/results/r2_halting_smoke_<日期>_r<轮>.{json,log}`。
- 结果（跑完填）：**screening NO-GO（2026-09-16，seed=1，1200 步）**。G1 PASS——两次
  arm-fixed 运行全部科学指标逐比特一致（indist 0.494140625 / ood 0.501953125），仅
  `wall_s` 计时字段差 0.1s（仪表量，非科学指标）；G2 FAIL——fixed 0.494、adaptive
  0.508，均 < 0.55（chance 水平，loss 停在 ~0.70 ≈ ln2，未学到信号）；G3 FAIL——
  mean_steps 1.010 < 1.3（halt 坍缩到第 1 步）；G4 PASS——fixed 22.6s / adaptive
  90.9s ≤ 10 min（2臂×5seeds ≈ 9.5 min，多种子可留在本机）。按预注册 G2 处置条款
  判"任务/容量欠配"，下一轮调容量/任务形式后重筛（不构成预注册修订）；证据
  `benchmarks/results/r2_halting_smoke_20260916_r1.log`（首次尝试的池化 bug 另存
  `*_attempt1_poolingbug.log` 留痕）。

### R2 screening #2 配置（2026-09-17 00:03 落盘，先于运行；G2 处置条款授权的容量校准）

- 判据不变（G1–G4 原文）；仅调容量/初始化：steps 1200→6000；长度课程（前 70% 步
  L∈[4,16]，后 30% 步 L∈[8,32]，两臂同课程）；halt 头 bias 初始化 -2.0（初始停步质量
  按 Geometric(0.12) 铺开到各迭代步，避免第 1 步独吞梯度后其余迭代死透）。
- G1 判定对象明确为"除 wall_s 外的全部 JSON 字段"（计时是仪表量，非科学指标；
  screening #1 实测仅该字段有 0.1s 差）。
- 通过标准仍为 G1–G4 全过；若 G2 再败，下一档升级为任务形式更换（累积取模和类，
  迭代步有独立梯度贡献），同样属于本条款授权范围。

### R2 screening #2 结果（2026-09-17 00:25 判定）

- **NO-GO ×2**（配置见上方 00:03 落盘记录；证据 `benchmarks/results/r2_halting_smoke_20260917_r2.log`）。
- G1 PASS（wall_s 除外全字段一致）；G2 FAIL——fixed in-dist 0.512 / OOD 0.482，
  adaptive 0.488 / 0.502，loss 仍卡 ln2 附近，6000 步 + 长度课程未产生学习信号；
  G3 FAIL——mean_steps 1.003（bias -2 只延迟了坍缩，未阻止）；G4 PASS——fixed 89s /
  adaptive 348s ≤ 10 min（2臂×5seeds ≈ 37 min，仍可留本机）。
- 按已落盘的升级条款：**下一档 = 任务形式更换**（screening #3）：改为"查询位置前缀
  parity"（串 + 查询位 q，答 bits[0:q] 的异或；每个迭代步对应明确的前缀扩展增益，
  难度随 q 连续变化，halt 有真实的"多想一步"收益结构）。配置于下轮运行前落盘。
- 过程事故留痕：00:03 预注册 commit 中的脚本 def 行损坏（我的编辑事故，运行全部
  IndentationError，未产出指标，traceback 日志因轮内日志改名操作未保留，git 历史
  中损坏版本可考）；修复后 attempt B 正常运行。

### R2 screening #3 配置（2026-09-17 00:35 落盘，先于运行；升级条款授权的任务形式更换）

- 任务：`prefix_parity`（查询位置前缀异或）——输入 bits + 查询位标记（embedding id2
  叠加于 qpos），目标 = bits[0:qpos+1] 的异或。相对 parity 的结构性差异：难度随 q
  连续变化（短前缀天然是课程），迭代步对应明确的前缀扩展增益。
- 其余继承 screening #2 配置：6000 步、长度课程（前 70% 步 L∈[4,16] 后 [8,32]）、
  halt bias -2、d=96/K=8/β=0.05/Geometric(0.25)、AdamW 1e-3、batch 64、CPU 确定性。
- 判据 G1–G4 不变（同 R2 原文；G1 判定对象=除 wall_s 外全部字段，且文件缺失不得判
  PASS）。新增诊断字段（不作判据）：in-dist/OOD 的 q 分桶（≤8 / 9–24 / ≥25）acc 与
  adaptive 分桶平均停步——用于检验"长前缀用更多步"的方向性。
- 运行前防线（screening #2 事故后固化）：`py_compile` 强制 + 双臂 150 步 infra
  selfcheck（本轮已过，无 NaN、JSON 字段齐全）→ 再进正式三连。
- 结果（跑完填）：（待填）

### R2 screening #3 结果（2026-09-17 01:05 判定）+ screening #4 终局配置预告

- **判定：G2 首次 PASS，但 G3 FAIL → 综合 NO-GO ×3**（证据
  `benchmarks/results/r2_halting_prefix_20260917_r3.log`）。
- G1 PASS（wall_s 除外逐字段一致）；**G2 PASS**——fixed in-dist 0.666 / adaptive 0.666
  （均 ≥ 0.55；fixed loss 0.480，短前缀桶 acc 0.83-0.87）——任务形式更换成功，
  parity 家族第一次真正被学习；**G3 FAIL**——mean_steps 1.028 < 1.3：任务学会了，
  但 halt 头仍判"一步足够"；G4 PASS（fixed 92s / adaptive 363s）。
- 分桶诊断（单 seed，仅方向性观察非结论）：fixed 臂长前缀桶（q≥25）in-dist 仅
  0.324，adaptive 同桶 0.588，但 adaptive 在该桶平均停步同样 ≈1.01——它的优势
  不来自迭代（噪声亦不可排除）。
- 机理判读（假设，非结论）：读出各步独立池化、step-1 预测已不差，额外迭代在
  任务 CE 下无净收益 → 早停是 halt 头的理性行为。**"多想一步"要有收益，必须让
  单步在结构上不足以作答。**
- **screening #4（阶梯终局步，下轮配置落盘后运行）**：progressive-reveal 前缀
  parity——迭代 k 的注意力只能看到前 ⌈k/K·L⌉ 位（硬约束单步能力上界），使
  长前缀必须迭代才能答对；G1–G4 判据不变，新增诊断同 #3。**结局规则（本轮
  落盘即生效）：#4 若 G3 再败 → P0' 判 REJECTED（机制级阴性结果，归档筛查区/
  backlog 留痕），类脑主轴转 latent-workspace recurrent（固定深度循环，不依赖
  可学习停步）；若全过 → 多种子放行。**

### R2 screening #4 配置（2026-09-17 01:03 落盘，先于运行；阶梯终局步）

- 任务/机制：prefix_parity + **progressive-reveal**。adaptive 臂重构：trunk 以第 1 步
  reveal 掩码（R_1=⌈L/8⌉ 位）跑一次；workspace 迭代 k 的注意力仅见前 R_k=⌈k/8·L⌉ 位；
  读出池化仅覆盖已 reveal 前缀。查询标记随其位置一起被 reveal——标记未 reveal 前模型
  无从知晓 q，只能继续迭代。fixed 臂保持 screening #3 原样（全量单步），作全信息基线。
- 其余配置继承 #3（6000 步、长度课程、halt bias -2、d=96/K=8/β=0.05/Geometric(0.25)、
  batch 64、CPU 确定性）；判据 G1–G4 不变；诊断同 #3（q 分桶 acc/steps）。
- 终局规则（#3 时已落盘，重申）：#4 全过 → 多种子放行；G3 再败 → P0' REJECTED
  （机制级阴性结果），主轴转 latent-workspace recurrent（固定深度循环）。
- 运行前防线：py_compile + 双臂 150 步 infra selfcheck。
- 结果（跑完填）：（待填）

### R2 screening #4 结果（2026-09-17 01:12 判定）——**GO，多种子放行**

- **G1–G4 全过**（证据 `benchmarks/results/r2_halting_prefix_20260917_r4.log`）：
  G1 PASS；G2 PASS（fixed 0.666 / adaptive 0.619 in-dist，OOD 0.553 / 0.547）；
  **G3 PASS——mean_steps 2.005 ∈ [1.3, 7.7]，坍缩首次被打破**；G4 PASS（86.8s / 324.8s）。
- 诊断（非判据）：halt 学到的是统一 2 步预算（各 q 桶均 ≈2.0 步），非逐例自适应；
  adaptive train_loss 0.669 高于 fixed 的 0.480（progressive 下优化更难）。长前缀桶
  in-dist 0.676 仅 ~26 样本，噪声范围内（1.8σ），不作为信息泄漏或优势证据。
- 按终局规则：进入**多种子阶段**——seeds=5（1..5）× 双臂，prefix_parity progressive
  配置不变；判优 = `publishable(per_seed_adaptive, per_seed_fixed)`（主指标 OOD acc），
  过门 → RESULTS.md PROVEN 追加行 + GRADUATION-CANDIDATE；不过 → 筛查区留痕。
- 结果（跑完填）：（待填）

### R2 多种子终判（2026-09-17 01:55 判定）——REJECTED

- `publishable(per_seed_adaptive, per_seed_fixed)`：OOD acc **0/5 胜**，配对符号检验
  p=0.0625 ≥ 0.05；in-dist 1/5 胜（p=0.375）；双臂非双峰。→ **判负**。
- adaptive 各种子 mean_steps = [2.005, 2.005, 2.032, 2.005, 2.003]：固定 2 步预算，
  无逐例自适应证据。
- 按终局规则：P0' REJECTED（机制级阴性结果，RESULTS.md 筛查区留痕）；主轴转
  latent-workspace recurrent（固定深度循环，不依赖可学习停步）。

## R3：latent workspace recurrent depth（固定深度循环）dose-response — 2026-09-17

- 动机：P0' 判负留下的问题——迭代的信息价值已被 progressive-reveal 证明（任务可学），
  但"可学习停步"无收益。本轮去掉停步学习，直接测固定深度 k 的 dose-response：
  共享 workspace block 循环 k 次（Geiping 式 latent recurrent depth），深度是否换来能力。
- 任务/配置：prefix_parity（复用 R2 终版）；6000 步、长度课程、trunk 恒 1 次不循环、
  d=96、batch 64、AdamW 1e-3、CPU 确定性；k ∈ {1, 2, 4, 8}，k=1 与 R2 fixed 臂同构
  （跨轮确定性对账点：seed 1 k=1 应逐字节复现 R2 multi `fixed_s1` 数字）。
- 预注册判据（跑之前写死）：
  - 主门：`publishable(per_seed_k8, per_seed_k1)` on OOD acc（k∈{1,8} 各 5 seeds，
    非双峰、配对符号检验 p<0.05）→ 过门 = 「深度有益」，入 PROVEN、模块标
    GRADUATION-CANDIDATE 候选；不过 = **REJECTED**（阴性：固定深度循环在本任务/
    规模无净收益），入筛查区，轴转 P3 次选。
  - 曲线诊断（非门）：k∈{2,4} 各 3 seeds 的单调性趋势。
  - 沿用门：G1 确定性（k=1 seed1 复现 R2 档案；wall_s 除外）；G2 各臂 in-dist ≥ 0.55；
    G4 单 run wall ≤ 10 min。
- 运行计划：py_compile + 150 步 smoke（k∈{1,8}）→ 全量 ~53 min 本机（≤1h 内），
  先门后曲线；超时则曲线臂顺延。归档 `benchmarks/results/r3_latent_depth_<日期>_k{k}_s{seed}.json`。
- 结果（跑完填）：（待填）

### R3 结果（2026-09-17 03:20 判定）——REJECTED

- 主门 `publishable(k8_ood, k1_ood)`：k8 [0.523, 0.559, 0.535, 0.541, 0.514] vs
  k1 [0.553, 0.572, 0.514, 0.566, 0.537]——**1/5 胜**，配对符号检验 p=0.375 ≥ 0.05，
  双臂非双峰 → 判负。
- 曲线（种子均值，诊断）：in-dist 0.655 / 0.695 / 0.697 / 0.676（k=1/2/4/8，k=2 见顶）；
  OOD 0.548 / 0.548 / 0.551 / 0.534（平坦，k=8 回落）。深度收益限于训练分布内拟合，
  不转化为长度外推；固定步数预算下 k=8 优化更难。
- 按判据：latent recurrent depth 方向 **REJECTED**（筛查区留痕）；轴转 P3 次选
  （predictive world model 筛查）。

## R4：测试场灵敏度校准（阳性对照：层级分块聚合 vs 平铺池化）— 2026-09-17

- 动机（P4 定级结论）：R2/R3 双阴性后必须先回答"是机制无用，还是测试场测不出差异"。
  本轮插入阳性对照：层级分块聚合（chunk 级 parity + 块间组合）在构造上匹配 parity 的
  复合结构，应当赢平铺池化。过门 → 测试场有区分度（此后阴性结果可信）；不过 →
  合成测试场对机制研究宣布失效，真实基准（人工判定项）成为唯一出路。
- 两臂：arm-flat = trunk + workspace×1 + 平铺池化（= R2 fixed 基线）；
  arm-hier = 同前段 + chunk 池化（c=8）→ 二级 workspace 过 chunk 序列 → chunk 均值读出。
  其余全同（prefix_parity、6000 步、课程、d=96、batch 64、CPU 确定性）。
- 预注册判据（跑之前写死）：
  - 主门：`publishable(per_seed_hier, per_seed_flat)` on OOD acc（各 5 seeds，非双峰、
    配对符号检验 p<0.05）→ 过门 = 测试场有效 + 阳性对照成立（PROVEN）；
    不过 = 测试场无区分度（筛查区留痕，合成轴冻结）。
  - 诊断：长前缀桶（q≥25）分桶 acc（层级聚合的收益应集中在此桶）。
  - 沿用门：G1 确定性重跑（wall_s 除外）；G2 双臂 in-dist ≥ 0.55；G4 单 run ≤ 10 min。
- 运行计划：py_compile + 150 步双臂 smoke → 全量 2 臂 × 5 seeds ≈ 25 min 本机。
  归档 `benchmarks/results/r4_arch_control_<日期>_{flat,hier}_s{seed}.json`。
- 结果（跑完填）：（待填）

### R4 结果（2026-09-17 03:40 判定）——阳性对照未过门，合成测试场冻结

- `publishable(hier_ood, flat_ood)`：hier [0.576, 0.539, 0.570, 0.594, 0.504] vs
  flat [0.553, 0.572, 0.514, 0.566, 0.537]——3/5 胜，p=1.0 ≥ 0.05 → 判负。
- 长前缀桶 OOD：hier 均值 0.511 vs flat 0.486（重叠噪声）；hier in-dist 各种子
  [0.729, 0.666, 0.734, 0.715, 0.523]——seed 5 塌到 0.523（层级结构训练方差更大）。
- **结论（按预注册结局规则）**：连构造上匹配任务复合结构的层级聚合都无法与平铺
  池化显著分离 → 合成测试场（pooled-readout 小模型 × prefix-parity）对"测试时
  计算"机制研究**无区分度，冻结**。同夜三连阴性（R2/R3/R4）共同构成该判断的证据。
- 唯一出路 = 真实基准（evals/ 48 题标注集 + 真实 Qwen key），需 AricRedemption
  两项人工裁定（见晨报决策包）。
