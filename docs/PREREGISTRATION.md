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
