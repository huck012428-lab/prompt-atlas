# prompt-atlas

A curated, versioned, searchable library of production-grade prompts for
LLM trainers, AI product managers, prompt engineers, RLHF / SFT data
teams, model evaluation teams, and AI application builders.

一个精选、带版本、可检索的生产级 Prompt 库，面向 LLM trainer、AI 产品
经理、Prompt 工程师、RLHF / SFT 数据团队、模型评估团队、AI 应用开发者。

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

The complete catalog lives in [`INDEX.md`](INDEX.md) (auto-generated).

完整目录见 [`INDEX.md`](INDEX.md)（自动生成）。

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

**v0.1.0** — first public release. 32 Prompt Cards across all 7
directions. See [`CHANGELOG.md`](docs/CHANGELOG.md) for details and
[`ROADMAP.md`](docs/ROADMAP.md) for what's next. Pull requests welcome.

**v0.1.0** —— 首个公开版本。32 张 Prompt Card，覆盖全部 7 个方向。
变更详见 [`CHANGELOG.md`](docs/CHANGELOG.md)，后续计划见
[`ROADMAP.md`](docs/ROADMAP.md)，欢迎 PR。
