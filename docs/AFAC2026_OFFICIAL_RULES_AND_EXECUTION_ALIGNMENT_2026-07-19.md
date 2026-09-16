# AFAC2026 官方规则与执行对齐

> 文档日期：2026-07-19  
> 官方规则来源：[天池赛事页面](https://tianchi.aliyun.com/competition/entrance/532486/information)  
> 项目规则原文：[AFAC2026_OFFICIAL_RULES.md](../reference/AFAC2026_OFFICIAL_RULES.md)

## 1. 文档目的

本文件将最新官网规则转换为项目执行约束，作为后续 Prompt、实现、测试、Qwen 评测和提交前检查的工作依据。

官网规则优先级高于此前生成的 baseline、advanced、handoff、M0 manifest 和旧 Prompt。旧文档中与本文件冲突的内容必须以本文件为准。

## 2. 项目最终目标

构建一个金融长文本 Agent，在不修改基座模型参数的前提下，通过本地文档预处理、确定性证据组织和 Qwen API 推理，实现：

```text
金融长文档
→ 文档解析与结构化
→ 题目和候选文档分析
→ 关键词/章节/数字/条款确定性定位
→ Evidence 组织与上下文管理
→ Qwen 证据判断与答案生成
→ 答案格式校验与 Token 统计
→ answer.csv
```

项目最终优化目标按优先级排列：

1. 提高 A/B 榜准确率。
2. 在准确率不下降的情况下减少 Token 消耗。
3. 严格生成可评测的 `answer.csv`。
4. 保留 `evidence.json`、处理数据、代码和日志，支持 B 榜前 15 名代码审核。

液态神经网络、Embedding、Rerank 和其他新模型不属于当前正式答题主链路。

## 3. 赛事规则冻结

### 3.1 数据和题型

- 全量基准题：200 道。
- A 榜：100 道，题目提供 `doc_ids`。
- B 榜：100 道，题目不提供 `doc_ids`，系统必须先定位候选文档。
- A 榜有效后才有资格进入 B 榜评测。
- 领域包括：`insurance`、`regulatory`、`financial_contracts`、`financial_reports`、`research`。
- 题型包括：`mcq`、`multi`、`tf`。

题目字段：

```json
{
  "qid": "fin_a_001",
  "domain": "financial_reports",
  "split": "A",
  "question": "...",
  "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "answer_format": "multi",
  "type": "...",
  "doc_ids": ["...", "..."]
}
```

文档元数据至少包括 `doc_id`、`path`、`title`。系统必须能够根据 `doc_id` 找到对应原始 PDF 或处理后的文档。

### 3.2 模型使用限制

正式推理问答阶段只能使用 Qwen 系列模型 API。官网当前指定的基准模型为 `Qwen3.6-plus`。

允许在数据预处理和文档解析阶段使用非 Qwen 工具，包括：

- OCR；
- PDF 文本抽取；
- 版面分析；
- 表格恢复；
- 阅读顺序还原；
- PDF 转结构化文本。

正式答题阶段禁止：

- Embedding 模型；
- 向量检索；
- Embedding 生成的排序或召回结果；
- 非 Qwen Rerank；
- 非 Qwen 候选过滤；
- 非 Qwen 答案投票或纠错；
- 非 Qwen 生成的语义摘要、FAQ、结论或知识库直接参与正式答题。

合规的正式路径是：

```text
允许的文档解析
→ 确定性关键词/章节/数字/条款/表格索引
→ 必要的规则检索与证据定位
→ Qwen API 进行证据判断和答案生成
```

### 3.3 开发测试与正式提交的边界

开发阶段可以使用以下工具进行工程验证：

- `MockChatClient`：验证调用链、解析、格式和错误处理；
- 本地模型：验证 Prompt 和 Evidence 组织；
- GPT Codex 子代理：执行代码实现、只读审计和测试；
- synthetic fixture：验证确定性检索、计算器和输出契约。

这些工具不能用于生成正式提交答案，也不能据此声称获得真实 A/B 准确率或赛事成绩。

正式提交答案必须由 Qwen API 生成。正式模式缺少 Qwen API、使用非 Qwen 模型或使用 Mock 时必须失败，不得静默回退。

## 4. 提交文件契约

正式文件名为 `answer.csv`，大小不得超过 100MB。

官网示例对应的 CSV 结构为：

```csv
qid,answer,prompt_tokens,completion_tokens,total_tokens
summary,,3627557,629,3628186
ins_a_001,B,37201,1,37202
ins_a_002,A,33063,1,33064
```

冻结要求：

- 第一行是表头；
- 第二行是 `summary`；
- `summary` 行的 `answer` 为空；
- 不存在 `unused_tokens` 字段；
- 后续每行对应一道题；
- `total_tokens = prompt_tokens + completion_tokens`；
- `summary.total_tokens` 是本次所有模型 API 调用的总和；
- Token 统计覆盖检索摘要、上下文压缩、证据判断、答案生成、自检等所有模型调用；
- 单选题提交一个大写字母；
- 判断题按照题目选项提交 `A` 或 `B`；
- 多选题提交按字母顺序排列、无分隔符的答案，例如 `AC`；
- 多选题漏选、错选、多选均不得分；
- 空答案、非法字符和顺序错误不得提交。

此前的无表头格式、`T/F` 判断题格式和 `unused_tokens` 设计均已废弃。

## 5. 评测指标

设：

```text
TokenBudget = 5,000,000
TotalTokens = summary.total_tokens
Accuracy = Correct / Total
TokenScore = max(0, min(1, (TokenBudget - TotalTokens) / TokenBudget))
FinalScore = 100 * Accuracy * (0.7 + 0.3 * TokenScore)
```

排序规则：

1. 准确率更高者优先；
2. 准确率相同时，`TotalTokens` 更低者优先；
3. 仍相同时，提交时间更早者优先。

官网给出的历史基线：

| 组别 | 正确/样本 | 准确率 | Token 消耗 |
| --- | ---: | ---: | ---: |
| A 组 | 49/100 | 49.0% | 2,991,883 |
| B 组 | 13/100 | 13.0% | 3,884,045 |
| 总计 | 30/200 | 15.0% | 6,875,928 |

基线说明：仅将长文档输入通用模型不能稳定解决任务，主要提升方向是文档解析、确定性检索、证据聚合、答案约束和领域策略。

## 6. 当前数据状态

当前项目本地已确认：

- A 榜题目 100 道；
- A 榜题目包含非空 `doc_ids`；
- 五个领域的题目和原始文档已在 `data/` 中；
- 题库没有标准答案字段；
- 没有独立的答案 key；
- 当前没有官方 B 榜题目文件。

因此本地无法计算完整真实 A/B 准确率。可以生成 Qwen 答案并提交平台，由平台使用标准答案评分。

当前日期为 2026-07-19，官网时间安排为：

- A 榜评测：2026-06-08 10:00 至 2026-07-21 20:00；
- B 榜评测：2026-07-22 00:00 至 2026-07-24 17:00。

当前优先级必须是 A 榜正式提交准备，不能等待本地 B 榜答案或标准答案。

## 7. 代码审核材料

B 榜排名前 15 名需要准备以下 `submission.zip`：

```text
submission.zip
├── answer.csv
├── evidence.json
├── processed_data/
├── agent/
├── script/
├── logs/
├── requirements.txt
└── README.md
```

压缩包总大小不得超过 1GB，并且应支持按照 README 一键运行并生成结果文件。

## 8. 现在的推进顺序

### 阶段 0：停止旧契约执行

当前旧执行 thread 不能继续进入 M1-M6，原因是它使用了已经过时的约束：

- 判断题 `T/F`；
- 无表头 CSV；
- `unused_tokens`；
- 禁止 Qwen API 的本地离线主链路；
- Mock 作为主要运行后端；
- 旧版 summary 解释。

先基于本文件重新生成执行 Prompt，并更新 manifest 的规则来源。

### 阶段 1：修正输入和输出契约

必须先修改并测试：

- `awareliquid/adapter/afac_contract.py`；
- `awareliquid/adapter/contracts.py`；
- `awareliquid/adapter/schemas.py`；
- `submit.py`；
- 相关契约测试。

验收内容：

- 表头正确；
- summary 行正确；
- 无 `unused_tokens`；
- `mcq`、`multi` 和 `tf` 输出合法；
- 判断题按照题目 A/B 选项处理；
- 每题 Token 三列一致；
- summary Token 覆盖全部模型调用；
- Mock 不能进入正式模式。

### 阶段 2：完成允许的文档预处理

从 PDF、HTML、TXT 生成可复现的处理数据，保留：

- `doc_id`；
- 页码；
- 标题和章节；
- 段落位置；
- 条款编号；
- 表格标题、表头、行、列、单位和脚注；
- 原始文本；
- 解析警告和源文件哈希。

预处理可以使用非 Qwen 工具，但不得生成会在正式答题中直接替代 Qwen 推理的语义结论。

### 阶段 3：建立正式检索和证据链路

使用确定性方法完成：

- 领域和文档过滤；
- 关键词和短语匹配；
- 章节和条款编号定位；
- 数字、年份、日期、百分比和货币定位；
- 表格行列定位；
- 选项级证据收集；
- 多文档证据合并。

禁止 Embedding、向量召回和非 Qwen 语义 Rerank。

### 阶段 4：接入 Qwen 正式推理

正式答案链路使用 Qwen API：

```text
题目
→ 确定性候选证据
→ Qwen 证据判断
→ Qwen 答案生成
→ 本地格式校验
→ Token 账本
```

每个 API 调用都必须记录真实的 `prompt_tokens`、`completion_tokens` 和 `total_tokens`。

### 阶段 5：生成 A 榜候选文件

在正式提交前必须完成本地预检：

- 题目数量和 `qid` 完整；
- 没有重复 `qid`；
- 每题答案符合题型；
- 判断题只输出 A/B；
- 多选答案排序、去重、无分隔符；
- summary 行完整；
- `summary.total_tokens` 等于所有模型调用总和；
- Token 不超过 5,000,000；
- 文件有表头；
- CSV 小于 100MB；
- UTF-8 编码；
- 无额外调试输出；
- 使用真实 Qwen 结果，不是 Mock 或 GPT 子代理结果。

### 阶段 6：使用剩余 3 次提交机会

提交策略：

1. 第一次提交：完整 Qwen A 榜候选，确认格式和链路有效；
2. 第二次提交：仅在第一次结果暴露明确问题后进行针对性修复；
3. 第三次提交：保留给最终稳定版本。

提交前不得使用 Mock 结果替代 Qwen 结果，也不得把 GPT 子代理结果写入正式 `answer.csv`。

### 阶段 7：B 榜开放后

B 榜开放后：

- 读取真实 B 榜题目；
- 不通过删除 A 榜 `doc_ids` 伪造 B 榜；
- 使用确定性候选文档定位；
- 仍然只用 Qwen API 进行正式推理；
- 生成 B 榜 `answer.csv`；
- 保存 `evidence.json` 和完整复现材料。

## 9. 当前代码必须修正的已知问题

当前代码和旧 manifest 仍包含以下过时实现：

- `unused_tokens` 参数和相关测试；
- 无表头 summary-first CSV；
- 判断题正式输出 `T/F`；
- 默认无 API Key 时回退 Mock；
- `hybrid` embedding 检索路径；
- README 中与正式规则不一致的输出描述；
- 旧 M0 manifest 将 PDF 页图的冲突解释为不可继续执行。

这些内容在更新 Prompt 后必须由独立执行 Agent 修改，再由独立验收 Agent 重跑测试。

## 10. 最终完成标志

项目只有在以下条件同时满足时，才可以进入正式 A 榜提交：

- 官方输入契约已按本文件冻结；
- CSV 契约已按官网示例实现；
- 判断题输出 A/B；
- 没有 `unused_tokens`；
- 正式模式无法使用 Mock 或非 Qwen 模型；
- 正式路径不使用 Embedding 和 Rerank；
- A 榜 100 道题全部生成答案；
- 所有 API Token 都被准确统计；
- `answer.csv` 通过本地预检并小于 100MB；
- 本地保存了提交版本、配置、日志和文件哈希。

最终目标是获得平台真实评分，不是把 Mock、GPT 子代理或 synthetic fixture 的结果称为比赛准确率。
