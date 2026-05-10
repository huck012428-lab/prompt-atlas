# prompt-atlas

A curated, versioned, searchable library of production-grade prompts for
LLM trainers, AI product managers, prompt engineers, RLHF / SFT data
teams, model evaluation teams, and AI application builders.

一个精选、带版本、可检索的生产级 Prompt 库，面向 LLM trainer、AI 产品
经理、Prompt 工程师、RLHF / SFT 数据团队、模型评估团队、AI 应用开发者。

> 🌐 **Live site / 在线站点**:
> [huck012428-lab.github.io/prompt-atlas](https://huck012428-lab.github.io/prompt-atlas/)
> — searchable, sidebar navigation, copy-button on every prompt block.
> 网页版含全站搜索、侧边栏导航、prompt 一键复制。

This is **not** a "awesome prompts" snippet collection. Every entry is a
**Prompt Card**: a reusable work asset with metadata, variables,
examples, documented failure modes, and tuning notes.

这**不是** awesome-prompts 式的素材合集。每一个条目都是一张 **Prompt
Card**：带元数据、变量、示例、失败模式、调优笔记的可复用工作资产。

## Why this exists / 为什么做这个

Production prompt work has the same problems as any other engineering
discipline: people rewrite the same prompts from scratch, lose track of
what works on which model, and discover failure modes the third time
they ship them. Treating prompts as *cards* — with schema, examples, and
documented failure modes — makes them reusable across teams and over
time.

生产环境的 Prompt 工作和任何工程学科一样会踩同样的坑：每次都从零写、
记不清哪条 prompt 在哪个模型上稳、上线第三次才发现固定的失败模式。把
prompt 当作"卡片"——有 schema、有示例、有失败模式记录——它们才能在
团队之间和时间线上被真正复用。

## What's inside / 库里有什么

Cards are organised by direction:

卡片按技术方向组织：

| Direction / 方向 | Examples / 内容举例                                            |
|------------------|----------------------------------------------------------------|
| **RAG**          | Retrieval scoring, multi-hop eval synthesis, query rewriting, HyDE, citation faithfulness, answer grounding<br/>检索打分、多跳评测题合成、query 改写、HyDE、citation 忠实度、答案扎根性 |
| **Agent**        | ReAct planners with strict tool-call schemas<br/>带严格 tool-call schema 的 ReAct planner |
| **RLHF**         | Pairwise preference labelers across HHH dimensions<br/>HHH 三维度的 pairwise 偏好标注器 |
| **SFT**          | Instruction-set augmentation from seed examples<br/>从种子样本扩展 SFT 指令集 |
| **Multimodal**   | VLM caption verification against actual images<br/>VLM caption 与图像内容核对 |
| **CoT**          | Structured reasoning with rationale summaries<br/>结构化推理 + rationale 摘要 |
| **Eval**         | LLM-as-judge rubrics for open-ended outputs<br/>开放式输出的 LLM-as-judge rubric |
| **Code**         | Code review checklist, test generation, code explanation, refactor suggestions, code-eval judge<br/>结构化 code review、测试生成、代码解释、重构建议、代码评估 |

The complete catalog lives in [`INDEX.md`](INDEX.md) (auto-generated).

完整目录见 [`INDEX.md`](INDEX.md)（自动生成）。

## I want to... / 我想做...

Maps a goal to the card to use. New here? See
[`docs/QUICKSTART.md`](docs/QUICKSTART.md) for a 5-minute walkthrough.

第一次用？看 [`docs/QUICKSTART.md`](docs/QUICKSTART.md) — 5 分钟从零到能用一张卡。

### Evaluate / score AI outputs · 评估和打分

| Goal · 我想做                                                          | Card · 用这张卡 |
|------------------------------------------------------------------------|-----------------|
| Score one AI output on factuality / coherence / completeness · 给单个 AI 输出按多维度打分 | [`eval/llm-judge-rubric-open-ended`](prompts/eval/llm-judge-rubric-open-ended.md) |
| Compare a model output against a gold answer · 用 gold 答案对照打分 | [`eval/reference-based-judge`](prompts/eval/reference-based-judge.md) |
| Decompose an output into atomic claims and fact-check each · 把答案拆成原子事实逐条核查 | [`eval/per-claim-factuality-judge`](prompts/eval/per-claim-factuality-judge.md) |
| Score one output on custom dimensions with confidence · 自定义维度打分 + 置信度 | [`eval/pointwise-quality-scorer`](prompts/eval/pointwise-quality-scorer.md) |
| Classify an AI output for safety harms · 输出安全分类（allow/review/block） | [`eval/safety-output-classifier`](prompts/eval/safety-output-classifier.md) |
| Pick the best of N AI responses · 从 N 个回答里选最好的 | [`rlhf/best-of-n-selector`](prompts/rlhf/best-of-n-selector.md) |
| Label A vs B preference (HHH) · 给 A/B 两个回答打偏好标签 | [`rlhf/pairwise-preference-labeler`](prompts/rlhf/pairwise-preference-labeler.md) |
| Pairwise judge with position-bias detection (two-call protocol) · 带位置偏置检测的 pairwise judge（双向调用） | [`eval/pairwise-judge-with-position-bias-probe`](prompts/eval/pairwise-judge-with-position-bias-probe.md) |
| Judge a multi-turn dialogue (per-turn + conversation-level) · 多轮对话评估 | [`eval/multi-turn-dialogue-judge`](prompts/eval/multi-turn-dialogue-judge.md) |
| Generate a domain-specific rubric with level anchors · 给具体任务自动生成定制化评分 rubric | [`eval/rubric-generator`](prompts/eval/rubric-generator.md) |
| Diagnose refusal calibration (over / under / correct) · 诊断模型拒绝是否校准 | [`rlhf/refusal-calibration-probe`](prompts/rlhf/refusal-calibration-probe.md) |

### RAG · 检索增强

| Goal · 我想做                                                          | Card · 用这张卡 |
|------------------------------------------------------------------------|-----------------|
| Score whether a retrieved passage is relevant to a query · 评估 passage 与 query 的相关性 | [`rag/retrieval-relevance-evaluator`](prompts/rag/retrieval-relevance-evaluator.md) |
| Build multi-hop QA eval questions · 合成多跳评测题 | [`rag/multihop-eval-synthesizer`](prompts/rag/multihop-eval-synthesizer.md) |
| Decompose / rewrite a query for retrieval · query 改写或拆解 | [`rag/query-rewriting-decomposition`](prompts/rag/query-rewriting-decomposition.md) |
| Generate hypothetical answer for HyDE retrieval · HyDE 假答生成 | [`rag/hyde-hypothetical-answer-generator`](prompts/rag/hyde-hypothetical-answer-generator.md) |
| Audit whether a citation actually supports a claim · 审计 citation 是否真的支持 claim | [`rag/citation-faithfulness-scorer`](prompts/rag/citation-faithfulness-scorer.md) |
| Detect hallucinations in a RAG answer · 检测 RAG 答案的幻觉 | [`rag/answer-grounding-checker`](prompts/rag/answer-grounding-checker.md) |
| Summarize a long document chunk for retrieval indexing · 给长文档块产 search-friendly summary | [`rag/chunk-summarizer-for-retrieval`](prompts/rag/chunk-summarizer-for-retrieval.md) |
| Compress retrieved passages into a smaller question-tailored context · 把检索结果压缩成针对问题的小上下文 | [`rag/context-compression`](prompts/rag/context-compression.md) |

### Build / debug an agent · 搭建和调试 Agent

| Goal · 我想做                                                          | Card · 用这张卡 |
|------------------------------------------------------------------------|-----------------|
| Run a ReAct loop with strict tool calls · 跑 ReAct loop，严格 tool call | [`agent/react-planner-with-tool-schema`](prompts/agent/react-planner-with-tool-schema.md) |
| Produce a complete plan upfront · 一次性给出完整计划 | [`agent/plan-and-execute-planner`](prompts/agent/plan-and-execute-planner.md) |
| Fix a malformed tool call from a validation error · 修复格式错误的 tool call | [`agent/tool-call-repair`](prompts/agent/tool-call-repair.md) |
| Reflect on whether the trajectory is on track · 反思 agent 是否在正轨 | [`agent/self-critique-reflection`](prompts/agent/self-critique-reflection.md) |
| Compress a long agent trajectory into memory · 把长 trajectory 压缩成 memory | [`agent/long-context-memory-summarizer`](prompts/agent/long-context-memory-summarizer.md) |
| Split a complex task across multiple specialized workers · 把复杂任务派给多个专精 agent | [`agent/sub-task-delegator`](prompts/agent/sub-task-delegator.md) |
| Decide whether a goal needs clarification, ask one good question · 判断是否要问澄清问题，问一个好问题 | [`agent/clarification-asker`](prompts/agent/clarification-asker.md) |

### Generate / filter training data · 训练数据生成与过滤

| Goal · 我想做                                                          | Card · 用这张卡 |
|------------------------------------------------------------------------|-----------------|
| Rewrite ONE instruction into N variants · 把 1 条指令改写成 N 个变体 | [`sft/instruction-variant-expander`](prompts/sft/instruction-variant-expander.md) |
| Generate NEW instructions from seed examples · 从种子生成新指令 | [`sft/self-instruct-from-seed`](prompts/sft/self-instruct-from-seed.md) |
| Generate a high-quality response for an instruction · 给指令生成回答 | [`sft/response-generator`](prompts/sft/response-generator.md) |
| Filter SFT pairs by quality (keep / review / drop) · 按质量过滤 SFT 数据 | [`sft/data-quality-filter`](prompts/sft/data-quality-filter.md) |
| Produce scalar reward for one response · 给单回答打 reward 分 | [`rlhf/pointwise-reward-scorer`](prompts/rlhf/pointwise-reward-scorer.md) |
| Critique a response against a constitution and revise · 按 constitution 批评 + 重写 | [`rlhf/constitutional-critique-revise`](prompts/rlhf/constitutional-critique-revise.md) |
| Generate adversarial probes for safety evaluation (defensive) · 生成防御性安全评估探针 | [`rlhf/red-team-prompt-generator`](prompts/rlhf/red-team-prompt-generator.md) |
| Generate multi-turn conversation SFT data · 生成多轮对话 SFT 数据 | [`sft/conversation-sft-pair-generator`](prompts/sft/conversation-sft-pair-generator.md) |
| Pick best K few-shot demonstrations from a candidate pool · 从样本池为目标 query 选最好的 K 个示例 | [`sft/few-shot-example-selector`](prompts/sft/few-shot-example-selector.md) |

### Work with images · 处理图像

| Goal · 我想做                                                          | Card · 用这张卡 |
|------------------------------------------------------------------------|-----------------|
| Generate a structured caption for an image · 给图片生成结构化 caption | [`multimodal/structured-caption-generator`](prompts/multimodal/structured-caption-generator.md) |
| Verify a caption against the actual image · 核对 caption 与图像 | [`multimodal/vlm-image-description-verifier`](prompts/multimodal/vlm-image-description-verifier.md) |
| Answer a question about an image · 视觉问答 + grounding + 置信度 | [`multimodal/vqa-with-confidence`](prompts/multimodal/vqa-with-confidence.md) |
| Extract typed fields from a document image · 从文档图片抽取结构化字段 | [`multimodal/ocr-structured-extraction`](prompts/multimodal/ocr-structured-extraction.md) |
| Extract data from a chart / plot / table image · 从图表或表格图片抽数据 | [`multimodal/chart-table-extractor`](prompts/multimodal/chart-table-extractor.md) |
| Analyze a document page's layout (title / body / tables / figures) · 分析文档页面版式结构 | [`multimodal/document-layout-analyzer`](prompts/multimodal/document-layout-analyzer.md) |

### Improve reasoning quality · 提升推理质量

| Goal · 我想做                                                          | Card · 用这张卡 |
|------------------------------------------------------------------------|-----------------|
| Single-pass structured reasoning with rationale · 单次结构化推理 + rationale | [`cot/structured-reasoning-with-rationale-summary`](prompts/cot/structured-reasoning-with-rationale-summary.md) |
| Decompose a complex problem into easier sub-problems · 把复杂问题拆成更简单的子问题 | [`cot/least-to-most-decomposition`](prompts/cot/least-to-most-decomposition.md) |
| Aggregate N sampled paths into a consensus answer · 把 N 条采样路径聚合成共识答案 | [`cot/self-consistency-aggregator`](prompts/cot/self-consistency-aggregator.md) |
| Draft + verify before committing to a final answer · 先 draft 再 verify 再交答案 | [`cot/verify-then-finalize`](prompts/cot/verify-then-finalize.md) |
| Explore multiple branches in parallel and prune (tree-of-thoughts) · 多分支并行探索 + 剪枝 | [`cot/tree-of-thoughts`](prompts/cot/tree-of-thoughts.md) |
| Abstract the question into a principle first, then apply (step-back) · 先抽象到原理再代入具体题 | [`cot/step-back-prompting`](prompts/cot/step-back-prompting.md) |

### Work with code · 处理代码

| Goal · 我想做                                                          | Card · 用这张卡 |
|------------------------------------------------------------------------|-----------------|
| Structured code review with per-dimension findings · 按维度做结构化 code review | [`code/code-review-checklist`](prompts/code/code-review-checklist.md) |
| Generate test cases for a function · 给函数生成测试用例 | [`code/test-case-generator`](prompts/code/test-case-generator.md) |
| Explain code at a specific audience level · 按受众层级解释代码 | [`code/code-explanation-generator`](prompts/code/code-explanation-generator.md) |
| Judge whether candidate code fulfills a task · 评估候选代码是否完成任务 | [`code/code-eval-judge`](prompts/code/code-eval-judge.md) |
| Suggest concrete refactors with rationale · 提结构化重构建议 | [`code/refactor-suggestion`](prompts/code/refactor-suggestion.md) |
| Translate code from one language to another · 跨语言代码翻译（含 idiom 控制） | [`code/code-translation`](prompts/code/code-translation.md) |

## How to use it / 如何使用

### As a GitHub repository / 作为 GitHub 仓库

1. Browse [`INDEX.md`](INDEX.md) or `prompts/<direction>/`.
2. Open the card you want; copy the **Prompt** section.
3. Read the **Failure Modes** and **Tuning Notes** sections — that is
   where the experience lives.
4. Substitute `{{variable}}` placeholders with your inputs.

中文流程：

1. 浏览 [`INDEX.md`](INDEX.md) 或 `prompts/<方向>/` 目录。
2. 打开目标卡片，复制 `## Prompt` 段落。
3. **务必读** `## Failure Modes` 和 `## Tuning Notes` 两段——那是真正的
   经验所在。
4. 用你自己的输入替换 `{{variable}}` 占位符。

### As a Claude Code skill / 作为 Claude Code Skill

Install this repository as a skill so Claude Code can route user intents
to the right card directly:

把本仓库当作 skill 安装，Claude Code 就能根据用户描述自动定位到对应
卡片：

```bash
git clone https://github.com/huck012428-lab/prompt-atlas ~/.claude/skills/prompt-atlas
```

Then in Claude Code:

之后在 Claude Code 中：

```
You: I need a prompt to score whether a retrieved passage is relevant.
Claude: [reads SKILL.md routing tree, picks rag/retrieval-relevance-evaluator,
         and adapts it to your inputs]
```

```
你: 帮我写个判断 retrieved passage 相关性的 prompt。
Claude:[读取 SKILL.md 的路由树，选中 rag/retrieval-relevance-evaluator，
         按你的输入做适配]
```

The skill entry is [`SKILL.md`](SKILL.md).

Skill 入口在 [`SKILL.md`](SKILL.md)。

## Anatomy of a Prompt Card / 一张卡片的结构

```
prompts/rag/retrieval-relevance-evaluator.md
├── frontmatter / 元信息块
│   ├── id, title, version, status         (identity / 身份)
│   ├── direction, tags, audience, models  (discovery / 发现)
│   ├── language, input/output_schema      (integration / 集成)
│   └── variables                          (slots / 变量槽)
└── body / 正文
    ├── ## Purpose         适用场景与目标
    ├── ## Prompt          带 {{variable}} 占位符的 prompt 主体
    ├── ## Example         具体的输入 → 期望输出
    ├── ## Failure Modes   常见失败模式与检测方法
    ├── ## Tuning Notes    模型差异、温度、相邻用法的调优笔记
    └── ## Changelog       版本历史
```

Full schema and controlled vocabulary: [`docs/SCHEMA.md`](docs/SCHEMA.md).

完整 schema 与受控词汇表：[`docs/SCHEMA.md`](docs/SCHEMA.md)。

## Safety / 安全立场

This repository does **not** accept jailbreaks, safety-bypass prompts,
hidden chain-of-thought extraction techniques, harm-enabling content, or
proprietary leaks. See [`docs/SAFETY.md`](docs/SAFETY.md). Defensive and
evaluation-oriented prompts (red-team rubrics, harmlessness labelers,
factuality judges) are explicitly welcome.

本仓库**拒收** jailbreak、绕过安全的 prompt、套取闭源模型隐藏推理链
的 prompt、有害内容生成 prompt、私有/泄露 prompt。详见
[`docs/SAFETY.md`](docs/SAFETY.md)。**明确欢迎**评估类、防御类 prompt
——红队评分、有害性标注、事实性判官等。

## Contributing / 贡献流程

See [`CONTRIBUTING.md`](.github/CONTRIBUTING.md). Short version:

详见 [`CONTRIBUTING.md`](.github/CONTRIBUTING.md)。简要流程：

1. Copy [`templates/prompt-card.md`](templates/prompt-card.md) into
   `prompts/<direction>/<your-slug>.md`.
   <br/>复制 [`templates/prompt-card.md`](templates/prompt-card.md) 到
   `prompts/<方向>/<你的-slug>.md`。
2. Run `python scripts/validate.py` until it returns `OK`.
   <br/>跑 `python scripts/validate.py` 直到输出 `OK`。
3. Run `python scripts/build_index.py` to refresh `INDEX.md`.
   <br/>跑 `python scripts/build_index.py` 刷新 `INDEX.md`。
4. Open a PR using the prompt-card issue template.
   <br/>用 prompt-card issue 模板开 PR。

CI runs the same validation; PRs that don't pass won't be merged.

CI 跑同一套校验；不通过的 PR 不会被合入。

## License / 许可证

Dual-licensed. See [`LICENSE`](LICENSE).

双许可证。详见 [`LICENSE`](LICENSE)。

- **Code** (`scripts/`, CI configs): MIT
- **Prompt content** (`prompts/`, `templates/`, `docs/`): CC-BY-4.0

- **代码**（`scripts/`、CI 配置）：MIT
- **Prompt 内容**（`prompts/`、`templates/`、`docs/`）：CC-BY-4.0

Each Prompt Card carries `license: CC-BY-4.0` in its frontmatter for
clarity.

每张 Prompt Card 的 frontmatter 中都标注 `license: CC-BY-4.0`，避免混淆。

## Status / 当前状态

**v0.1.0** — first public release with 32 Prompt Cards. Library has
since grown to **53 Prompt Cards across all 7 directions** (post-v0.1
additions tracked in [`CHANGELOG.md`](docs/CHANGELOG.md)).
See [`ROADMAP.md`](docs/ROADMAP.md) for what's planned next. Pull
requests welcome.

**v0.1.0** —— 首个公开版本，32 张 Prompt Card。后续已扩到
**53 张，覆盖 8 个方向**（v0.1 之后的新卡见
[`CHANGELOG.md`](docs/CHANGELOG.md)）。后续计划见
[`ROADMAP.md`](docs/ROADMAP.md)，欢迎 PR。
