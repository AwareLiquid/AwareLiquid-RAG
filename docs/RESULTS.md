# Canonical Evidence Base（单一事实源）

Last reconciled: **2026-09-07**

本文件是本仓库实验证据的**唯一事实源**。任何其他文档（README、HANDOFF、
docs/runs/、幻灯片、对外表述）与本文件冲突时，**以本文件为准**——错的
是那份文档，需要改的是它。

## 证据政策

1. 每个对外引用的数字必须指回本文件 Proven 表，并给出仓库内可复现产物
   路径（反引号包裹，如 `benchmarks/results/bench_adapter_fake_20260906_r1.log`）。
   引用路径的真实性由 `scripts/check_results_refs.py` 机器校验（CI 门禁，
   见 `.github/workflows/ci.yml`）。
2. **引用门槛（E0 协议门）**：凡对外引用的**对照数字**（A vs B、新旧
   策略对比），必须过 `benchmarks/experiment_protocol.py` 的
   `publishable()` 判定——≥3 seeds、双臂非双峰、配对检验 p<0.05。
   **单次运行的计数（如本仓库 bench 的 N/N 题）属于筛查/smoke**：只能
   用于回归对照和方向判断，不得作为对外结论引用，直到扩展为多 seed /
   多题集并过门。
3. **撤回/取代不删除**：过时或被推翻的数字移入下面的 SUPERSEDED /
   筛查区表，保留原始数值、日期和原因。
4. 判定规则先于结果落盘：见 `docs/PREREGISTRATION.md`。

## PROVEN（当前有效）

| Claim | Number | Status | 证据 |
|---|---|---|---|
| bench lexical stand-in（8 题，哈希确定性修复后，单次筛查运行）：hybrid recall@4 | 8/8 (100%)，dense 7/8 | 筛查有效 | `benchmarks/results/bench_adapter_fake_20260906_r1.log` |
| 同上：answer retention（hybrid / dense） | 8/8 / 7/8 | 筛查有效 | `benchmarks/results/bench_adapter_fake_20260906_r1.log` |
| 同上：prompt context tokens vs 全文档 | 1254 vs 22668（−94%） | 筛查有效 | `benchmarks/results/bench_adapter_fake_20260906_r1.log` |
| 同上：正式格式有效行 / 判定 | 8/8，RESULT: PASS | 筛查有效 | `benchmarks/results/bench_adapter_fake_20260906_r1.log` |
| bench `--fake` 跨进程可复现（修复内建 `hash()` 后） | 连跑 3 次输出逐字节一致 | 已验证 | `benchmarks/results/bench_adapter_fake_20260906_r1.log`、`benchmarks/results/bench_adapter_fake_20260906_r2.log`、`benchmarks/results/bench_adapter_fake_20260906_r3.log` |
| 单元测试基线（离线全量，197 个测试） | 197 passed | 当前有效 | `benchmarks/results/pytest_20260907.log`（运行 `scripts/test.sh`） |
| M0 输入/内部/正式输出合同冻结（仅合同，非准确率） | 冻结，来源优先级与冲突已留痕 | 已归档 | `docs/AFAC_M0_CONTRACT_EVIDENCE.md` |
| run 证据链完整性（18/19 个 run 目录有 manifest + sha256 sidecar；a0-20260719T001816-26628 为杂散目录，仅 baseline.txt 无 manifest，校验器显式 SKIP 列出） | 可机器校验，当前 PASS | 已归档 | `docs/runs/`（`scripts/check_results_refs.py` 输出 PASS） |

## SUPERSEDED / 筛查区（留痕不删除）

| Claim | Number | 处置 | 证据 / 备注 |
|---|---|---|---|
| bench e5（真实 multilingual embedder，6 题集）：recall@4、retention | 6/6、6/6；压缩率 0.48 | **历史单次筛查，未复核**——重跑需下载模型，离线环境无法复核；引用前必须重跑并过 E0 门 | `README.md` Validation 节（旧 6 题集） |
| bench lexical stand-in 旧 6 题集：recall@4、retention、压缩率 | 5/6、5/6、0.46 | **SUPERSEDED (2026-09-06)**——被 8 题集确定性运行取代（题集与编码器哈希均已变更，数字不可比） | 旧 `benchmarks/bench_adapter.py` 运行，无留档日志 |
| 修复前 bench `--fake` 两次运行 8/8 与 7/8 互相矛盾 | — | **RETRACTED (2026-09-06)**——根因：`benchmarks/bench_adapter.py` 的 `LexicalEncoder` 用内建 `hash()`，盐随进程随机；两值均为随机盐的运气，不代表系统能力 | 无留档（修复前输出未保存），仅本行记录；修复后日志见 `benchmarks/results/` |
| run 目录 JSON sidecar 哈希（提交于 f459eca） | 66 处失配 | **CORRECTED (2026-09-06)**——sidecar 哈希的是 canonical compact JSON，落盘是 pretty-print 版，内容语义相同（逐一验证 canonical 哈希吻合后重写为磁盘字节哈希，0 处遗留失配）；管线出处：`scripts/bootstrap_a1_terra_r1.py` 的 `sidecar()` 调用点混用 `object_hash` 与 `raw_hash` | `docs/runs/`（修复后 `scripts/check_results_refs.py` PASS） |
| R2 自适应停止（PonderNet 式 halt，progressive-reveal prefix-parity，5 seeds 配对）：adaptive vs fixed 的 OOD / in-dist accuracy | adaptive OOD [0.547, 0.551, 0.502, 0.555, 0.502] vs fixed [0.553, 0.572, 0.514, 0.566, 0.537]——**adaptive 0/5 胜**（配对符号检验 p=0.0625）；in-dist 1/5 胜（p=0.375）；双臂均非双峰 | **REJECTED (2026-09-17)**——`publishable()` 判负：progressive-reveal 下 halt 学到固定 2 步预算（各种子 mean_steps≈2.00），准确率一致性地不低于全信息单步基线；机制级阴性结果：本规模下可学习停步无净收益 | `benchmarks/results/r2_halting_prefix_20260917_multi_summary.json`、`benchmarks/results/r2_halting_prefix_20260917_multi.log`（协议与 screening 链：`docs/PREREGISTRATION.md` 附录 R2） |
| R3 latent recurrent depth（固定深度循环 k∈{1,2,4,8}，prefix-parity，k=1/k=8 各 5 seeds 配对）：k8 vs k1 的 OOD accuracy | k8 [0.523, 0.559, 0.535, 0.541, 0.514] vs k1 [0.553, 0.572, 0.514, 0.566, 0.537]——**1/5 胜**（p=0.375）；OOD 曲线平坦（k=1/2/4/8 均值 0.548/0.548/0.551/0.534），in-dist 在 k=2 见顶（0.655→0.695→0.697→0.676） | **REJECTED (2026-09-17)**——`publishable()` 判负：深度的收益限于训练分布内拟合，不转化为长度外推；固定步数预算下 k=8 优化更难。阴性结果：共享块循环深度在本任务/规模无净收益 | `benchmarks/results/r3_latent_depth_20260917_summary.json`、`benchmarks/results/r3_latent_depth_20260917.log`（协议：`docs/PREREGISTRATION.md` 附录 R3） |
| R4 测试场阳性对照（层级分块聚合 vs 平铺池化，prefix-parity，各 5 seeds 配对）：hier vs flat 的 OOD accuracy | hier [0.576, 0.539, 0.570, 0.594, 0.504] vs flat [0.553, 0.572, 0.514, 0.566, 0.537]——**3/5 胜**（p=1.0）；长前缀桶均值 0.511 vs 0.486（重叠噪声） | **测试场无区分度 (2026-09-17)**——构造上应当分离的阳性对照都无法显著胜出，`publishable()` 判负。按预注册结局规则：合成测试场（pooled-readout 小模型 × prefix-parity）对机制研究**冻结**；同夜 R2/R3/R4 三连阴性共同构成该判断 | `benchmarks/results/r4_arch_control_20260917_summary.json`、`benchmarks/results/r4_arch_control_20260917.log`（协议：`docs/PREREGISTRATION.md` 附录 R4） |

## What we do NOT claim（负面声明）

1. **端到端答案准确率未测量**：最终字母由冻结模型选择，离线无法评估；
   需要 live Qwen key 才能测（README Scope 节同款声明）。
2. **91.7% 无本仓库产物支撑**：外部表述（含 M1 仓库 README 对本仓库的
   描述）中的 ~91.7% eval score 在本仓库找不到任何可复现证据，在证据
   链补齐前不得引用。
3. **`answer.csv` 不是可提交状态**：token 三列全 0 是占位，不代表真实
   用量或排名。
4. **M0 合同证据不建立**真实 A/B 准确率、真实 token 用量、排名或提交
   就绪（`docs/AFAC_M0_CONTRACT_EVIDENCE.md` 开头的自限声明）。
5. **bench 表格数字不是结论**：8 题单次运行只证明"管线工作、门槛条件
   满足"，不证明检索/压缩质量优于任何基线——那需要多 seed / 多题集 +
   `publishable()` 过门。

## 对账日志

- **2026-09-06**（首次对账）：
  - 移植 M1 仓库 E0 协议门为 `benchmarks/experiment_protocol.py`（零依赖，
    7 个契约测试：`tests/test_experiment_protocol.py`）。
  - 修复两处内建 `hash()` 跨进程不确定性：`tests/conftest.py` 的
    `FakeEncoder`、`benchmarks/bench_adapter.py` 的 `LexicalEncoder`；
    bench 三连跑逐字节一致（见 PROVEN 表）。
  - 收敛 run 证据清单：`docs/runs/` 19 个目录全部过
    `scripts/check_results_refs.py`（manifest 路径 + sha256 sidecar）。
  - 确立本文件为单一事实源；README bench 表与本文件对齐（见下）。
  - **事故 1（bench 数字漂移）**：`bench --fake` 连续两次运行结果矛盾，
    根因为 `LexicalEncoder` 内建 `hash()` 盐随机 → 修复后三连跑逐字节
    一致，旧数字（8/8、7/8）撤回。新增 bench 确定性回归测试
    （`tests/test_bench_determinism.py`，PYTHONHASHSEED=1/2 双盐对照，
    断言两次 stdout 逐字节一致），锁住 2026-09-06 事故，替代人工三连跑。
  - **事故 2（sidecar 失配）**：`scripts/check_results_refs.py` 首跑抓到
    66 处 JSON sidecar 失配——管线哈希 canonical compact JSON 而落盘是
    pretty-print 版；逐一验证对象等价后重写为磁盘字节哈希，纪律入
    `docs/PREREGISTRATION.md` 不做清单。
- **2026-09-07（评审轮）**：只读评审发现并当日修复——
  (a) PROVEN 表"19/19 run 目录"声称超出实际（实为 18/19，杂散目录
  a0-20260719T001816-26628 无 manifest），校验器改为对无 manifest 的
  run 目录显式 SKIP 列出，不再静默跳过；
  (b) `bimodality_1d` 对量化分数误报双峰（簇内全为重复值时类内散度为
  0，任意两个相邻取值的 gap_ratio 爆炸，如 6/8 与 7/8 的正常一致性
  数据会被判双峰），增加绝对间隙下限 0.25（按 [0,1] 量纲设计）；
  (c) 含 None 的臂会让 `publishable()` 路径 TypeError 崩溃（seeds /
  双峰 / 符号检验三层各崩一处），统一收敛为 `_as_floats` 清洗——
  脏臂由 seeds 门槛判负，`publishable()` 任何路径不再崩溃；
  (d) 确定性测试增加"bench 输出 == 留档日志"逐字节断言，把 README /
  本文件引用的数字钉死到产物（改口径必须显式重新留档并对账）；
  (e) pytest 结果留档为 `benchmarks/results/pytest_20260907.log`，
  Proven 表不再有无产物支撑的数字；
  (f) README Validation 表撤下 e5 历史数字本体（单次运行计数不入对外
  材料，见 `docs/PREREGISTRATION.md`），保留指向本文件的指针；
  (g) CI 加最小权限（`permissions: contents: read`）与
  `timeout-minutes: 30`。
- **2026-09-07（遗留 NIT 修复轮）**：评审遗留三项全部修复——
  (a) md5 分桶逻辑收敛为共享模块 `awareliquid/hashing.py::stable_hash`
  （`tests/conftest.py` 与 `benchmarks/bench_adapter.py` 不再各写一份；
  行为逐位不变，日志钉扎测试确认输出仍与留档一致）；
  (b) 校验器对**歧义裸文件名**从"静默取第一个命中"改为 FAIL 并列出全部
  候选（`scripts/check_results_refs.py`，新增对应测试）；
  (c) 5 个 `scripts/bootstrap_*.py` 的 sidecar 调用点全部改为写盘后的
  磁盘字节哈希（`raw_hash`/`file_digest`）——换 RUN_ID 重跑不再复制
  66 处失配事故；manifest/contract 内部 `*_sha256` 字段保持 canonical
  对象哈希语义（有文档化的 hash domain，与 sidecar 是两套含义）。

- **2026-09-17**（类脑轴首个多种子判定）：
  - R2「自适应停止」（PonderNet 式 halt）走完预注册全链：4 轮 screening
    （parity→parity+课程→prefix-parity→progressive-reveal，逐轮配置先落盘）
    + 5 seeds 多种子对照，终判 **REJECTED**：progressive-reveal 使 halt 脱离
    坍缩（mean_steps≈2.0，G3 首过），但 5 seeds 配对 0/5 胜全信息单步基线
    （OOD 符号检验 p=0.0625），`publishable()` 判负。完整数字与证据见
    筛查区新行；方向梯队与逐轮判定见 `notes/overnight/backlog.md` P0'。
  - 判负亦产出可复用资产：`research/exp_halting_parity.py`（双臂、双任务、
    确定性、progressive-reveal 开关）；后续 latent-recurrent 方向直接复用
    其合成任务与验收骨架。
  - 无 RESULTS.md 既有判定行改动；本节与筛查区新行均为追加。

- **2026-09-17 续**：R3「latent recurrent depth」（固定深度循环）5 seeds 判
    **REJECTED**——k=8 vs k=1 OOD 仅 1/5 胜（p=0.375），OOD 曲线平坦、in-dist
    k=2 见顶：深度收益不转化为长度外推。筛查区新行留痕；同夜连续两个类脑机制
    阴性结果（R2 停步、R3 深度）出自同一可复现骨架 `research/exp_halting_parity.py`。

- **2026-09-17 续（R4）**：阳性对照（层级分块聚合）亦判负——合成测试场按预注册
  规则**冻结**，循环转入"需人工判定"停靠点：后续唯一有区分度的路径是真实基准
  （48 题标注集 + 真实 Qwen key），决策包见当夜晨报。
