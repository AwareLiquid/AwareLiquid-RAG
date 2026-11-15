# AwareLiquid-M2 最终执行总控 Prompt

## 0. 当前状态与物理启动门

本文件是后续执行的完整 Prompt。当前回合仅允许读取和审查本文件；不得修改项目代码，不得创建或运行 E/V/R/Sol Agent，不得调用 Qwen/API、外网或 API Key，不得生成、上传或提交 `answer.csv`。

只有用户明确发送 `CONFIRM_IMPLEMENTATION`，或同等明确且不可误解地授权“进入实现阶段”后，Controller 才能创建 A0 `stage-contract`、Packet、Manifest 和 sidecar，并派遣 A0。

在收到确认前，严禁：

- 修改项目代码；
- 创建或写入执行 Packet、stage-contract、Manifest 或 sidecar；
- 启动 E/V/R/Sol Agent；
- 运行实现、测试、格式化、安装或迁移命令；
- 调用 Qwen/API、外网或 API Key；
- 生成、上传或提交 `answer.csv`。

目标是在保留当前 working tree 中有意义的 dirty changes 的前提下，按 A0-A6 修复工程契约、确定性证据链、Qwen 正式模式和候选预检。无关 dirty changes 必须保护，不得覆盖、删除或 reset。

阶段含义固定：

- A0：只读规则、代码、数据基线审计；
- A1：输入、答案和 CSV 契约；
- A2：Qwen provider、network、Mock、Token gate；
- A3：允许的离线预处理与 Evidence provenance；
- A4：Evidence 组织、Decimal、选项验证和 deterministic exact-only locator；
- A5：用户授权后的 Qwen 正式模式和本地候选；
- A6：独立只读最终验收，不生成候选。

## 1. 唯一规则来源与硬约束

唯一规范性来源：

`reference/AFAC2026_OFFICIAL_RULES.md`

`output/`、其他 `reference/` 文件、handoff、README、旧 Prompt、旧 manifest、代码和测试只能作为思路、baseline 经验和实现启发，不能定义或覆盖正式字段、提交格式、模型限制、A/B 规则或时间。冲突必须舍弃并报告，禁止猜测。

硬约束：

- 正式推理只能使用官方允许的 Qwen API。当前官网目标若为 Qwen3.6-plus，精确 model id 必须由用户确认且 API 实际可用；禁止猜测、替换非 Qwen、静默降级或 Mock fallback。
- OCR、PDF/HTML/TXT 解析、版面分析、表格恢复、阅读顺序还原和结构化文本转换等非 Qwen 预处理允许使用。
- 非 Qwen 不得生成直接用于正式答题的语义摘要、FAQ、结论或知识库。
- 正式答题禁止 Embedding、向量召回及其排序、非 Qwen rerank、非 Qwen 候选过滤、非 Qwen 投票/纠错。
- 确定性关键词、章节、条款、数字、日期、标题、表格、doc_id 和原文位置可用于证据定位。
- A=100，B=100。
- A 时间为 `2026-06-08 10:00–2026-07-21 20:00`。
- B 时间为 `2026-07-22 00:00–2026-07-24 17:00`。
- A 有效成绩前不得进入 B。
- A 每题必须使用题目提供的非空 doc_ids；A locator 严格限定这些 doc_ids。
- B 无 doc_ids，只有官方 B 文件出现后才可启用 B locator。
- 当前本地只有官方 A100，无官方 B；只能使用明确标记的 synthetic B 非赛事 dry-run，不得从 A 删除 doc_ids 伪造 B，不得声称真实 B 验证。
- TokenBudget 为 5,000,000；所有模型调用（规划、检索摘要、上下文压缩、证据判断、答案生成、自检）进入同一 ledger；usage 缺失、未知或超预算必须 fail closed。
- CSV 按官方文件执行：UTF-8、<100MB；第一行 `qid,answer,prompt_tokens,completion_tokens,total_tokens`；第二行 `summary,,prompt_total,completion_total,total_total`；无 `unused_tokens`；qid 唯一且题数完整；`total_tokens = prompt_tokens + completion_tokens`；mcq 输出大写选项；multi 去重、按字母排序、无分隔符；tf 按 options 输出 A/B，不硬编码 T/F。
- 没有 A 标准答案 key 不报告真实 A accuracy；没有官方 B 不报告真实 B accuracy；Mock、GPT 子 Agent、非 Qwen 模型不是赛事结果。

## 2. Stage Contract、模型探测、hash 和派遣协议

### 2.1 模型探测

每个 stage-contract 创建前，Controller 必须在不调用 Qwen/API/外网的本地控制环境执行一次 Luna availability probe，并记录绝对 cwd、argv、env、退出码、结果、model、model_hash、时间和决策。

- Luna 可用：该阶段 E/V/R 全部使用同一 `gpt-5.6-luna`；
- Luna 不可用：该阶段 E/V/R 全部使用同一 `gpt-5.6-terra`；
- 同一阶段不得混用 Luna/Terra；
- A6 后的 `FINAL-PROJECT-V-SOL` 使用新的独立 `gpt-5.6-sol`；
- Sol 不可用时 STOP/BLOCKED，不回退；
- probe 失败、结果不确定或 model_hash 无法记录时，不创建 contract、不派 Agent，标记 `BLOCKED_MODEL_PROBE`。

### 2.2 Stage Contract

收到 `CONFIRM_IMPLEMENTATION` 后，每个 `run_id + stage` 只创建一个不可变、versioned `stage-contract.json` 和 `stage-contract.json.sha256`。E/V/R 必须共同引用同一 `contract_sha256`。

Contract 必须绑定：

- run_id、thread_id、stage；
- rules_path、rules_sha256；
- model_probe、model、model_hash、decision；
- git HEAD、status、diff-stat、dirty 文件 hashes；
- inputs（path/hash/purpose）；
- 完整 E/V/R commands；
- acceptance criteria、fail conditions、stop conditions；
- read/write/forbidden permissions；
- artifacts、handoff。

任何规则、baseline、AC、fail、stop、scope、model、command、allowlist 或 artifact policy 改变，都必须新 run_id、新 contract、新 E；V/R 不得修改 contract。

### 2.3 Canonical Hash

所有 contract、Packet、Manifest canonical JSON 的 hash domain 固定为：

- UTF-8、无 BOM、LF、无尾随空格；
- 对象键递归按 Unicode code-point 升序；
- 数组保持原顺序；
- 仅 JSON 标准类型；
- 数字唯一表示，禁止 NaN/Infinity；
- separator 只用 `,` 与 `:`；
- canonical body 末尾不含 LF；
- 落盘最多追加一个 LF，hash 排除该 LF。

hash 排除自身或相互自引用字段：

`contract_sha256`、`packet_sha256`、`prompt_sha256`、`manifest_sha256`、`self_hash`、`created_at`、`status`、`result`。

Sidecar 固定单行格式：

```text
<64位小写hex><两个ASCII空格><basename>\n
```

Sidecar 必须 create-exclusive，已存在不得覆盖。固定文件名：

```text
stage-contract.json
stage-contract.json.sha256
packet.json
packet.json.sha256
prompt.md
prompt.md.sha256
manifest.json
manifest.json.sha256
```

Prompt 使用 UTF-8、LF、无 BOM、无尾随空格、末尾恰好一个 LF；Prompt hash 是完整 role Prompt UTF-8 bytes，sidecar 不参与自身 hash。

### 2.4 Command Object

每个 E/V/R/Sol 命令必须是完整对象，不得“见上文”、省略号或让 Agent 自行发明：

```json
{
  "id": "A6-V-CMD-01",
  "cwd": "绝对 realpath",
  "argv": ["每个参数单独元素"],
  "env_inheritance": "none",
  "env_allow": {},
  "env_deny": ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"],
  "stdin": {"source": "none|literal|absolute-file", "sha256": "..."},
  "network_enforcement": {
    "mode": "actual-deny|allowlisted-qwen-only",
    "egress_allowlist": [],
    "preflight_argv": [],
    "verify_argv": [],
    "expected_preflight_exit": 0,
    "expected_verify_exit": 0
  },
  "credential_ref": null,
  "proxy_unset": true,
  "timeout_seconds": 300,
  "kill_grace_seconds": 5,
  "allowed_read_roots": [],
  "allowed_writes": [],
  "expected_exit_codes": [0],
  "expected_artifacts": []
}
```

禁止 shell、pipe、redirection、命令替换、隐式子进程和隐式网络。A0-A4 及 A5 授权前使用 `actual-deny`；A5 授权后仅使用 `allowlisted-qwen-only`；A6 只读、无网络。

### 2.5 Allowlist 与依赖闭包

所有 allowlist 元素必须是 `{path,type,recursive,access}` 对象。使用前执行 realpath+lstat，拒绝 symlink escape、目录穿越、设备文件、FIFO 和未知类型；forbidden 优先；每次 open/read/write 重算 realpath；未分类路径一律 BLOCKED_SCOPE。

必须审计 Python import、dynamic import、plugin、dlopen、子进程和配置加载的依赖闭包。禁止加载 embedding、sentence-transformers、transformers、torch、SentenceEncoder、vector DB、dense/hybrid、RRF、rerank。

V 的缓存、SQLite、报告和临时文件只能写：

`/tmp/awareliquid-verification/<run_id>/`

并设置 `PYTHONDONTWRITEBYTECODE=1`、`TMPDIR`、`pytest -p no:cacheprovider`。

### 2.6 Packet/Prompt/Manifest 闭环

hash 依赖顺序固定：

```text
contract → packet → prompt → manifest
```

Prompt 必须嵌入与外部 Packet 完全逐字节一致的：

```text
BEGIN PACKET
...
END PACKET
```

抽取后重算 hash 必须与外部 Packet sidecar 一致。每个 Agent 启动前重新计算 contract、packet、prompt、manifest digest，并核对 sidecar、内嵌 Packet、realpath、model probe。任何 mismatch、CRLF、额外尾行、sidecar 可覆盖、contract/model 不一致都标记 `BLOCKED_HASH_MISMATCH`，不得执行。

E 完成后派新 V；V FAIL 才派新 R；R 后新 V 全量复验。V 不信任 E/R 报告。R 不得修改 contract、AC、fail、scope、model、commands 或 allowlist。

## 3. 统一报告

每份 E/V/R/Sol 报告至少包含：

```yaml
run_id: ...
thread_id: ...
stage: ...
role: ...
model: ...
model_probe: ...
contract_sha256: ...
packet_sha256: ...
prompt_sha256: ...
manifest_sha256: ...
status: PASS|FAIL|BLOCKED
rules_source: reference/AFAC2026_OFFICIAL_RULES.md
rules_sha256: ...
commands: []
changed_files: []
findings: []
artifacts: []
next_action: ...
accuracy_claim: "不得声称真实赛事 accuracy"
```

V 必须按每个 AC ID 提供 PASS/FAIL 和直接证据。

## 4. A0：只读基线审计

E-A0 只读官方规则、HEAD/status/diff-stat、代码、测试、manifest、data 和思路材料，记录 baseline/hash/data 摘要，检查 unused_tokens、summary、CSV 表头、tf T/F、Mock fallback、provider/model gate、embedding/hybrid/dense/rerank、A doc_ids、Evidence、ledger、A/B 数据与时间偏差。不得修改、联网、调用 API、生成 CSV 或报告 accuracy。

V-A0 独立重做审计和 hash 核对，确认 E 无写入、无网络，每项有直接证据。

R-A0 只能补正审计目录中的报告、manifest、证据；不得改项目、规则或数据；新 V-A0 全量复验。

## 5. A1：CSV/输入输出契约

E-A1 在 A0 V PASS 后修 canonical contract、schemas、submit 和测试，实现官方表头、summary、五列 Token、删除 unused_tokens、qid 唯一完整、mcq/multi/tf、tf A/B、multi 排序去重、total 加和和预算校验。Mock 仅工程测试，不生成正式候选，不改无关 dirty changes。

V-A1 独立运行完整命令，核验表头、summary、无 unused_tokens、tf A/B、qid/multi、UTF-8、大小、Token 等式、fail closed、无 API/network。

R-A1 只修 findings 和回归测试，不恢复旧契约或手改答案；新 V-A1 全量复验。

## 6. A2：Qwen provider/network/Mock/Token gate

E-A2 在 A1 V PASS 后实现唯一 transport、provider/model/endpoint allowlist、formal Qwen-only gate、显式 Mock、network deny、统一 Token ledger。无 key、错误 provider/model/endpoint、deny 失败、usage 缺失/未知或超预算时正式 fail closed，不能 fallback Mock。本阶段不调用真实 API。

V-A2 在隔离环境执行 deny preflight/verify、gate 正反例、显式 Mock、无 key、usage 缺失、ledger/预算测试，并检查未列 transport、fallback 和直接网络。

R-A2 只修 findings，不放宽 allowlist、Mock、usage 或调用网络；新 V-A2 全量复验。

## 7. A3：离线预处理和 Evidence provenance

E-A3 在 A2 V PASS 后冻结 PDF/HTML/TXT 离线解析器、版本和配置，允许 OCR/PDF/版面/表格/阅读顺序/结构化转换；逐页记录空页、乱码、正文/表格失败和 parse_warning；Evidence 至少保留 domain、doc_id、page、source_path、char_start、char_end、section、title、table_id、row_id、column_ids、unit、footnote、parent_evidence_id、neighbor_evidence_ids、parse_warning；evidence_id 由版本、来源、位置和内容 hash 确定性生成；不得非 Qwen 摘要/FAQ/结论。

V-A3 独立核对页码、字符偏移、表头、完整表格行、单位、脚注、否定、例外、条件边界和 warning，用 synthetic fixture 验字段和 ID 稳定，真实 A 只验 provenance。

R-A3 只修 provenance、解析和 fixture，不删页引用、不压边界、不引摘要；新 V-A3 全量复验。

## 8. A4：Evidence、Decimal、选项验证、exact-only locator

E-A4 在 A3 V PASS 后组织完整 Evidence context，保留原文、标题、章节、完整相关表格行/表头、单位、脚注、否定、例外、限定词、条件边界、parent/neighbor 和 Evidence ID。Decimal+白名单结构化操作，禁止 eval/exec；每个计算输入绑定 Evidence ID；选项逐项输出 supported/refuted/insufficient，比较数字、年份、单位、否定、例外、限定词和来源，错误或 insufficient 不得伪造答案。

建立 deterministic exact-only backend：允许 doc_id、标题/章节/条款、精确词/短语、数字、年份、日期、百分比、货币、评级、表格字段和原文位置；全部匹配按原始 doc/page/char 顺序稳定返回 Evidence IDs。SQLite/FTS5 如使用只能做无相关性评分 exact token/phrase lookup。禁止 BM25、RRF、vector、dense、hybrid、query-dependent ranking、非 Qwen 语义过滤、语义截断、同义词扩展、问题改写、option 过滤、embedding、transformers、torch、SentenceEncoder、vector DB、rerank。A 严格限制题目非空 doc_ids；无官方 B 仅 synthetic B。

V-A4 独立运行 Decimal、无 eval、Evidence 保真、三态选项、exact-only 稳定性和 A scope 测试，构造越界 doc、同义词、排序诱导、空匹配、表格数字、否定/例外边界，确认 fail closed。

R-A4 只修 findings，不得以召回为由引入 embedding/BM25/rerank/同义词/语义过滤或删除 Evidence 边界；新 V-A4 全量复验。

## 9. A5：Qwen 正式模式和本地候选

A5 入口为 A4 V PASS。收到用户精确 `CONFIRM_QWEN_CANDIDATE` 前只能 Mock/dry-run，network actual-deny，不得真实 API/Qwen、不得生成会被误认的正式 answer.csv、不得上传/提交；dry-run 必须 synthetic/mock 标记。授权必须明确 provider、endpoint、实际 model id、opaque credential_ref、egress 和本地输出路径；授权后创建新的 versioned A5 contract/Packet，不复用 dry-run contract。

A 分支：只处理官方 A100，每题保留非空 doc_ids，query scope 是题目 doc_ids 严格交集，使用 A 时间窗口；不得删除 doc_ids、改题或伪造 B。

B 分支：只有官方 B100 实际存在、可审计 A 有效成绩已提供、B 时间窗口已到、用户另发 `CONFIRM_QWEN_CANDIDATE-B` 且 B 专属 locator/scope 就绪时才可启用。B 无 doc_ids。当前无官方 B，不得生成/上传/声称真实 B；synthetic B 只能非赛事 dry-run。

E-A5 授权正式模式执行 Qwen；规划、压缩、证据判断、生成、自检等所有模型调用进入同一 ledger，<=5,000,000；检索仍 exact-only；不引入 embedding/rerank/非 Qwen 过滤。A 分支生成本地官方 A100 answer.csv；B 分支只有满足 B 前置后生成官方 B100。保存 raw call、ledger、Evidence/Decision Artifact、metadata、candidate hashes、preflight；不上传/提交/报 accuracy。

V-A5 独立重算 contract/Packet/Prompt/Manifest hashes，验证 Qwen-only、model、endpoint、egress、credential、A/B split、doc_ids、时间/授权、Evidence、ledger、预算、CSV/preflight，确认非 Mock/非 Qwen。V 不修改 candidate、ledger、raw call、Evidence、Decision Artifact、metadata 或 CSV。

R-A5 不得就地修改 candidate、ledger、raw call、Evidence、Decision Artifact、metadata、CSV 或 hash，不得手改答案/绕过 validator/preflight。R 触及代码、Prompt、config、dependency、input、ledger、generator、validator 或 preflight 实质内容时，旧 candidate 作废并保留旧 hash；创建新的 A5 R stage-contract/Packet，按机械回退链生成全新 candidate，新 V-A5 全量复验。

## 10. A6：独立只读最终验收

A6 只在 A0-A5 V PASS 后启动；A6 只读，不调用 Qwen/API/网络，不生成/修改/重生成 candidate。

至少运行：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider
git diff --check
bash -n scripts/test.sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m compileall -q awareliquid submit.py examples
```

compileall 不得直接运行在 dirty working tree。必须先创建 `/tmp/awareliquid-verification/<run_id>/compile-root` 受控只读副本，记录源文件 hashes、快照清单 hash、副本 hash；compileall cwd、argv、read roots、writes、artifacts 全部指向副本或其 TMPDIR；pyc/报告只能写 TMPDIR；working tree 前后 hash 必须完全不变。

E-A6 只读收集 A0-A5 contracts、Packets、Prompts、Manifests、sidecars、reports、规则、dirty baseline、测试结果和 candidate，重算 digest，核对内嵌 Packet 与外部 Packet 一致，检查全部 gates、allowlist、symlink、依赖闭包、无 embedding/rerank、A/B、Evidence、Decimal、选项、Qwen gate、ledger、CSV、preflight、candidate immutable、无上传/提交。

V-A6 新独立 V 从原始 contract 全量复验，运行规定命令，为每个 AC 提供证据。A5 未授权/dry-run 时可建议 `LOCAL_ENGINEERING_READY`；真实候选合规时可建议 candidate PASS，但不能代替总体 Sol。实质 finding FAIL，旧 candidate 作废并走回退链。

R-A6 只能在允许的审计目录补正验收记录/证据，不得改 contract、AC、fail、scope、model、commands、allowlist、项目、candidate、测试。实质问题回最早阶段。

## 11. 机械回退链

若 A5/A6 发现 candidate、代码、Prompt、config、dependency、input、ledger、generator、validator、preflight 或其他实质问题：

1. 旧 candidate、ledger、raw calls、Evidence、Decision Artifact、metadata、CSV 和 hashes 原样只读保留并标为失效证据；
2. 创建新的 R stage-contract/Packet，使用新的 run_id 和全新 hashes；
3. 新 R 只处理 finding，不改 AC/fail/scope；
4. 新 V 全量复验；
5. 按依赖顺序重跑所有下游 V；
6. 回到 A5 重新取得授权并由新 A5 E 生成新 candidate；
7. 新 A5 V 全量复验；
8. 新 A6 全量 V；
9. 新 FINAL-PROJECT-V-SOL；
10. 缺授权、model id、credential、网络隔离、官方 B 或 A 有效成绩时 STOP/BLOCKED，不得用 Mock、旧 candidate 或猜测替代。

## 12. FINAL-PROJECT-V-SOL

A6 V PASS 后，创建 Sol contract 前完成 Sol availability probe；Sol 缺失 STOP，不回退。

新的独立 `gpt-5.6-sol` 必须从 A0-A6 所有原始 stage-contract、Packet、Prompt、Manifest、sidecars、E/V/R/A6 reports、dirty baseline、rules/input/artifact hashes 全量重读并交叉验收，不能只看 A6 或 candidate。

验收：

- hash domain、sidecar、内嵌 Packet；
- contract immutability；
- model probe；
- E→V→R→V 独立性；
- command isolation/allowlist/network；
- A0-A5 原始语义；
- A/B 数据、时间、授权；
- 禁止 embedding/rerank；
- Evidence、Decimal、选项；
- Qwen-only；
- Token ledger/预算；
- CSV/preflight；
- candidate/ledger/raw call/Evidence/Decision Artifact/metadata/CSV immutable；
- 所有 P0/P1 已关闭；
- dirty worktree 未被改写；
- 未上传/提交。

Sol 不调用 API、不重生成、不修改文件。

无真实授权候选时，全量 PASS 只能输出 `LOCAL_ENGINEERING_READY`，不得报告 accuracy。

有新 A5 真实候选时，只有该 Sol 全量 PASS 才能唯一输出 `QWEN_CANDIDATE_READY`。

`A_SUBMISSION_READY` 只有用户另行明确授权上传/提交后才可产生；Controller 不自动上传、提交或消耗机会。

## 13. 当前执行纪律

- 不要把 gpt-5.6-sol 用作 E/V/R；
- 不要并行派遣写同一 working tree 的 Agent；
- 不要跳过 V 或 R；
- 不要将 Mock、GPT 子 Agent 或非 Qwen 结果当赛事结果；
- 不要调用 Qwen，除非用户明确授权且 A5 门已满足；
- 不要自动上传、提交或生成 A_SUBMISSION_READY；
- 不要绕过 CONFIRM_IMPLEMENTATION；
- 任何不确定性都必须 STOP/BLOCKED，而不是猜测。

现在先把本文件设置为 Goal，读取并遵守本文件；未收到 CONFIRM_IMPLEMENTATION 前停在启动门，后续严格按本文件完整执行。"} irresponsive? Need final via tool. We got invalid arguments maybe due prompt too long or target invalid. Could be parameter `thinking` not supported? It is. But error likely because project environment local cannot specify environment local? schema target project with `environment: {type:"local"}` yes. Maybe prompt too long exceeding tool limit. We can create thread with short prompt that tells read file, after we write file. Great! We just wrote file. Retry create_thread with short prompt. Need no new file changes. Use same `codex_app.create_thread`. 
