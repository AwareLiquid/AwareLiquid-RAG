# AFAC M0 Contract Evidence

Run: `afac-20260718-203623-019f74b8`  
Source thread: `019f74b8-0bbf-74f0-a168-1ab34711a671`

This record freezes only the local offline input, internal, and formal-output
contracts. It does not establish real A/B accuracy, real token usage, ranking,
or submission readiness.

## Source precedence and decisions

1. **Primary source:** `downloads/AFAC-赛题四-PDF/金融长文本 Agent 的动态记忆压缩与高效问答.pdf`, page 4 for the A/B distinction and page 6 for the input/output image. The page-level evidence supplied for this run states that A provides `doc_ids`, B locates documents itself, inputs include `qid/domain/question/options/answer_format/type/doc_ids`, the generic options description is A/B/C/D, and the formal first row is `summary,5000000,1234567,0` without a header. It also states single-choice is one letter, multi-choice is sorted concatenated letters, judgment is `T/F`, and Token accounting covers every model-interface call. The page does not define how the fourth summary value is computed; the literal example is arithmetically inconsistent with `budget-used`, so that meaning remains unresolved.
2. **Local extraction of the primary source:** `output/pdf/AFAC-赛题四-Markdown/金融长文本 Agent 的动态记忆压缩与高效问答-精简版.md:188-224` records the fields, option keys, summary row, answer formats, Token scope, and A/B distinction. Its `:136-143` view is the compact table used for the line references in the earlier verification report.
3. **Lower-priority reference:** `reference/advanced.md:561-575` (also rendered in the Baseline PDF Markdown at `output/pdf/AFAC-赛题四-Markdown/定稿版【跑通Baseline】赛题四：金融长文本Agent的动态记忆压缩与高效问答挑战.md:561-575`) shows a header and a five-field prompt/completion/total summary. This conflicts with the primary page-6 image. The primary source wins; the conflict is retained in the M0 manifest and the implementation emits headerless summary-first rows.

## Frozen input contract

`awareliquid.adapter.afac_contract.parse_question` and
`awareliquid.adapter.contracts.validate_question` validate the explicit
`split` field and never infer it from `qid`, `type`, or `doc_ids`.

| split | `doc_ids` missing | `doc_ids: null` | `doc_ids: []` | non-empty list |
| --- | --- | --- | --- | --- |
| A | fail `DOC_IDS_REQUIRED_FOR_A` | fail `DOC_IDS_REQUIRED_FOR_A` | fail `EMPTY_DOC_IDS` | accepted and preserved in order |
| B | accepted and normalized to `None` | accepted and normalized to `None` | fail `EMPTY_DOC_IDS` | fail `SPLIT_DOC_IDS_CONFLICT` |

Split values are explicit `A`/`B` (case-normalized); both entry points accept
explicit lowercase `a`/`b` and normalize the internal standard object to
uppercase before applying the split-specific `doc_ids` rules. An absent,
non-string, or otherwise invalid split is a structured error. `mcq` and `multi` options must be an object with exactly
the four keys `A`, `B`, `C`, `D`, with string values. The verified real A set
uses two-key `A`/`B` options for its 20 `tf` questions; the synthetic fixture
also exercises a four-key TF object, so both TF shapes are accepted. The
formal TF output remains strictly `T` or `F`. `answer_format` is one of `mcq`,
`multi`, or `tf`; `type` is retained only as a hint.

### R-M0-R5 split-normalization repair

The two M0 validation entry points now have the same explicit split boundary:
they accept only string `A`/`B` values case-insensitively, normalize accepted
values to uppercase, and then apply the existing four-state `doc_ids` table.
The paired regression in `tests/test_contracts_m0.py` covers lowercase `a` and
`b` through both entry points. It confirms normalization without permitting
split inference or weakening the A/B `doc_ids`, TF option, formal `T`/`F`, or
explicit `unused_tokens` fail-closed contracts.

## Internal standard object

`ParsedQuestion` contains `qid`, `domain`, normalized `split`, `question`, the
keyed options (A/B for audited real `tf` questions, or A/B/C/D for `mcq` and
`multi`; four-key `tf` remains accepted for compatibility), `answer_format`, `type_hint`, and `doc_ids` as
`Optional[Tuple[str, ...]]`. `to_dict()` is deterministic and preserves A-list
document order. `SubmissionAnswer` validates formal answer letters and
internally consistent per-question token counts. `SubmissionSummary` accepts
explicit `budget_tokens`, `used_tokens`, and `unused_tokens`; it never derives
the fourth summary value from the first two.

## Frozen formal output

`render_submission_csv` emits CSV with no header only for local structural
tests. It refuses to render with `MISSING_UNUSED_TOKENS` until the caller
supplies `unused_tokens` explicitly, and serializes that supplied value without
derivation. `submit.py` likewise requires explicit `--budget-tokens`,
`--used-tokens`, and `--unused-tokens` before it can write an output file. This
is a structural contract only, not an interpretation of the fourth field.

The official meaning of that field is not frozen because page 6 labels it
`未用` but gives `summary,5000000,1234567,0`; therefore this stage must not
claim that `unused = budget - used` is authoritative. The formal-output
contract remains **unresolved** at M0 and
`official_submission_allowed=false`.

```text
summary,5000000,<used>,<unresolved-unused>
<qid>,<answer>,<prompt_tokens>,<completion_tokens>,<total_tokens>
```

`mcq` accepts one of A/B/C/D; `multi` accepts a non-empty sorted, de-duplicated
letter string such as `BC`; `tf` accepts exactly `T` or `F`. Summary `used`
must cover all per-question `total_tokens` and cannot exceed the supplied
budget. Token fields represent all model-interface calls represented by the
answer rows; this local implementation reports only supplied/mock counts. No
official submission is emitted while the fourth summary field is unresolved.

## Blocking gates for later stages

These gates are recorded at M0 and remain blocking requirements; none is
evidence that M1 or M3 has been started or passed.

1. The page-6 official summary example is the highest-priority source for the
   fourth summary column. Its calculation rule must be confirmed from official
   material before an official submission can be authorized; the explicit API
   only preserves structure and does not resolve that rule.
2. M1 must freeze the actual PDF body-parser version and configuration.
   `pdfinfo` alone is not evidence of body quality. Each page with empty text,
   garbling, or table-extraction failure must retain the original page reference
   and a `parse_warning`.
3. M3 may claim 100% required coverage only for synthetic golden fixtures.
   Real A validation must instead preserve and verify lossless
   locator/hash/source/page/character metadata.
4. Any B validation must use an independent synthetic fixture. It must not
   delete or simulate away the real A `doc_ids` inputs.
5. Before the first verification run, confirm `.venv` and development
   dependencies. Verification must use `PYTHONDONTWRITEBYTECODE=1 pytest -p
   no:cacheprovider`; caches, SQLite state, and reports belong only under
   `/tmp/awareliquid-verification/<run_id>`, not the workspace.
6. Step 7 remains offline: network, external API or key use, GPU, embedding,
   and reranking are prohibited.

## Data status and fixture boundary

The local filesystem audit found `data/` with 578 readable files: five
`data/questions/group_a/*.json` files (20 questions each, 100 total), all with
explicit `split=A` and non-empty `doc_ids`, plus 573 raw files. Raw counts by
top-level domain are financial_contracts=14, financial_reports=10, insurance=16,
regulatory=513 (including attachments/HTML/TXT), and research=20. No
`data/questions/group_b/` directory or B question set was found. The resulting
status is `REAL_A_DATA_FOUND_B_NOT_VERIFIED`. This permits local component
verification against A inputs only; it does not permit real A/B accuracy or
leaderboard claims. The five A question file SHA-256 values are recorded in the
stage manifest. Shape audit: mcq/multi A/B/C/D=80, tf A/B=20. `downloads/` remains source/tutorial material and `examples/`
contains sample data only. The fixtures
`tests/fixtures/afac_m0_synthetic_golden.json` and
`tests/fixtures/afac_synthetic_golden/questions.json` are explicitly marked
synthetic and are for local component verification only.

### PDF encryption re-audit (R-M0-R4)

An independent offline `pdfinfo` audit traversed every case-insensitive
`data/raw/**/*.[pP][dD][fF]` candidate. It parses the value from lines beginning
exactly `Encrypted:` and classifies values beginning `yes` as encrypted, because
`pdfinfo` includes permissions and algorithm details after that value. The
reproducible result is 190 PDFs, 190 readable PDFs, 0 `pdfinfo` errors, 188
unencrypted PDFs, 2 encrypted PDFs, and 11,667 pages.

The encrypted paths are `data/raw/insurance/1.pdf` (21 pages, RC4) and
`data/raw/insurance/4.pdf` (33 pages, AES). Their fields are respectively
`Encrypted: yes (print:yes copy:no change:no addNotes:no algorithm:RC4)` and
`Encrypted: yes (print:yes copy:no change:no addNotes:no algorithm:AES)`.

This conflicts with the prior user claim that there were zero encrypted PDFs;
the directly reproducible local evidence takes precedence and keeps M0 failed.
It also corrects V-M0-R3's reported count of nine. That report does not retain
the prior audit script, so its mechanism cannot be established; the correction
source is R-M0-R4's direct parsing of the `Encrypted:` fields above, rather than
an assertion about the unavailable script.
