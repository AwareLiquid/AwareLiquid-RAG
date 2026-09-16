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
