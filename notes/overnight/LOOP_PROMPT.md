# M2 自主研究循环提示词（夜间定时任务用，2026-09-11 定稿）

永续运行 M2 自主研究循环（类脑推理实验室）。工作区：/Users/aricredemption/Projects/AwareLiquid-RAG。

【研究纲领】M2 = 类脑推理实验室，方向池围绕以下模块展开（迁入+新建）：GWTB / workspace iterations、Global Coherence、Orch-OR top-down modulation、predictive world model、Hamiltonian world model、global rhythm、astrocyte / Hebbian / consciousness metrics、core_iterations、stack_iterations、新的 latent workspace recurrent reasoning、自适应停止与测试时计算。毕业纪律（硬规则）：任何模块只有通过多种子消融、在预注册基准上明确提升能力（过 benchmarks/experiment_protocol.py::publishable 门）后，才在 backlog 标 GRADUATION-CANDIDATE 并开 PR 等人工合并进稳定主干；未过门一律留在 overnight/loop。

【分支纪律】只在 overnight/loop 分支上工作（无则自 origin/main 新建；origin/main 有新合入则先 merge），其余任何分支与 worktree 一律不碰。永不：改 docs/RESULTS.md 既有判定行（新结果只能按证据政策追加，单 seed 只能入筛查区，判负也留痕不删除）、合并或关闭任何 PR、push main、force push、改写历史、提交 .pt/.onnx/.env/模型权重/data/ 大文件。提交只 add 明确文件路径，禁止 git add -A / git add .（工作区可能有 answer.csv 等杂项）。实验先预注册后运行：判定规则先写进实验脚本 docstring 或 docs/PREREGISTRATION.md 附录，prereg: 前缀先落盘再跑，提交动词纪律 prereg: → bench: → results: → docs:。

【每轮流程】从 notes/overnight/backlog.md 取最高优先方向（先读其头注：状态机、毕业看板、价值排序、Kaggle 通道状态、算力政策），按预注册判负标准跑最便宜实验，严谨验收：① publishable() 门（≥3 seeds、双臂非双峰、配对符号检验 p<0.05），单 seed 只标 screening；② scripts/check_results_refs.py PASS；③ scripts/test.sh 离线全量测试绿；④ 对照预注册标准逐条判定。结果 JSON/日志入 benchmarks/results/（带日期与轮次命名），原子 commit+push 到 overnight/loop，更新 backlog（方向状态机+毕业看板）并强制浮现下一个方向：科研按 arXiv/GitHub 扫"谁做过、失败在哪"（global workspace/latent workspace、recurrent depth、ACT/PonderNet 自适应停止、test-time compute scaling、predictive processing/世界模型、Hebbian/astrocyte、意识度量），按"对核心基准的能力提升潜力 > 消融科学价值"排序；工程清偿最痛摩擦（确定性、复现、度量基建、Kaggle 通道）。方向池空则先扫描浮现新方向再继续。迁入类方向若旧仓（如 /Users/aricredemption/Projects/M1，MT-LNN）已有实现，只读参考移植，绝不写源仓。

【算力政策（用户定调，硬规则）】本机（M2 Max 12 核）只跑预计 ≤1 小时的任务：探针、分析、判读、验收门、单文件小修、超小冒烟。预计 >1h 的训练/批量任务禁止本机执行——一律推 Kaggle：纯 CPU 批量推 CPU notebook（4 核，不烧 GPU 配额，数据用 Kaggle dataset 挂载绕私有仓限制）；GPU 训练推 T4（.venv/bin/kaggle kernels push；kaggle CLI 未装则 pip install kaggle 并登记工程欠账；配额 ~30h/周×双账号，推送前 kernels list 记账，单实验 ≤2 臂，余量 <6h 冻结）。Kaggle/T4 通道可用性以 backlog 头注登记为准：不可用则该方向标 PAUSED 并浮现替代方向，不占本机硬跑。开场先 ps 查 CPU 占用与 notes/overnight/runs/*.pid 遗留进程：预计剩余 >1h 的本地长跑不默认续跑——登记欠账并浮现替代方向，或明确请求用户裁定。

【防重入】开场若 notes/overnight/loop.lock 存在且 mtime 距今 <2h，本轮直接退出不做任何事；否则写入自己的 pid+时间戳，收尾删除。

【开场】checkout overnight/loop（无则自 origin/main 新建；origin/main 有新合入则先 merge），检查 notes/overnight/runs/ 全部 pid 并按算力政策处置，读 backlog 头注与最近晨报后开轮。backlog 不存在时（首次运行）：初始化 notes/overnight/（backlog.md 含头注+上述模块清单为初始方向池、runs/ 目录、晨报骨架），先做一轮文献/代码扫描给方向定级，再开轮。

【停止条件】停止并写晨报仅当：方向池真穷尽（连续 2 轮扫描无新方向且主轴无实验，附 query 清单为证）或需人工判定（毕业 PR 合并、修改预注册协议、>1h 任务去向、Kaggle 配额冻结）。其余循环不止；每轮结束必须留下可续跑的干净状态（backlog 状态机+晨报+已 push）；若被强制结束，确保最后状态是"最近一轮已原子提交+晨报已更新"。

【晨报】notes/overnight/<日期>-morning.md 随每轮增量更新并 push：每轮方向/参数/seeds/命令/实验 commit SHA、三门验收结果（publishable/check_results_refs/pytest）、kernel id 与状态、Kaggle 配额账本、backlog 变化（含毕业看板变动）、需 AricRedemption 人工判定的事项。
