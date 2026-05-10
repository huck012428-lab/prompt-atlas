# prompt-atlas

A curated, versioned, searchable library of production-grade prompts for
LLM trainers, AI product managers, prompt engineers, RLHF / SFT data teams,
model evaluation teams, and AI application builders.

This is **not** a "awesome prompts" snippet collection. Every entry is a
**Prompt Card**: a reusable work asset with metadata, variables, examples,
documented failure modes, and tuning notes.

> 中文摘要见文末。

## Why this exists

Production prompt work has the same problems as any other engineering
discipline: people rewrite the same prompts from scratch, lose track of
what works on which model, and discover failure modes the third time
they ship them. Treating prompts as *cards* — with schema, examples, and
documented failure modes — makes them reusable across teams and over
time.

## What's inside

Cards are organised by direction:

| Direction       | Examples of what you'll find                              |
|-----------------|-----------------------------------------------------------|
| **RAG**         | Retrieval relevance scoring, multi-hop eval synthesis     |
| **Agent**       | ReAct planners with strict tool-call schemas              |
| **RLHF**        | Pairwise preference labelers across HHH dimensions        |
| **SFT**         | Instruction-set augmentation from seed examples           |
| **Multimodal**  | VLM caption verification against actual images            |
| **CoT**         | Structured reasoning with rationale summaries             |
| **Eval**        | LLM-as-judge rubrics for open-ended outputs               |

The complete catalog lives in [`INDEX.md`](INDEX.md) (auto-generated).

## How to use it

### As a GitHub repository

1. Browse [`INDEX.md`](INDEX.md) or `prompts/<direction>/`.
2. Open the card you want; copy the **Prompt** section.
3. Read the **Failure Modes** and **Tuning Notes** sections — that is
   where the experience lives.
4. Substitute `{{variable}}` placeholders with your inputs.

### As a Claude Code skill

Install this repository as a skill so Claude Code can route user
intents to the right card directly:

```bash
git clone https://github.com/huck012428-lab/prompt-atlas ~/.claude/skills/prompt-atlas
```

Then in Claude Code:

```
You: I need a prompt to score whether a retrieved passage is relevant.
Claude: [reads SKILL.md routing tree, picks rag/retrieval-relevance-evaluator,
         and adapts it to your inputs]
```

The skill entry is [`SKILL.md`](SKILL.md).

## Anatomy of a Prompt Card

```
prompts/rag/retrieval-relevance-evaluator.md
├── frontmatter
│   ├── id, title, version, status         (identity)
│   ├── direction, tags, audience, models  (discovery)
│   ├── language, input/output_schema      (integration)
│   └── variables                          (slots)
└── body
    ├── ## Purpose
    ├── ## Prompt           (with {{variable}} placeholders)
    ├── ## Example          (concrete input → expected output)
    ├── ## Failure Modes    (how it breaks, how to detect)
    ├── ## Tuning Notes     (model diffs, temperature, adjacent uses)
    └── ## Changelog        (per-version)
```

Full schema and controlled vocabulary: [`docs/SCHEMA.md`](docs/SCHEMA.md).

## Safety

This repository does **not** accept jailbreaks, safety-bypass prompts,
hidden chain-of-thought extraction techniques, harm-enabling content, or
proprietary leaks. See [`docs/SAFETY.md`](docs/SAFETY.md). Defensive and
evaluation-oriented prompts (red-team rubrics, harmlessness labelers,
factuality judges) are explicitly welcome.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Short version:

1. Copy [`templates/prompt-card.md`](templates/prompt-card.md) into
   `prompts/<direction>/<your-slug>.md`.
2. Run `python scripts/validate.py` until it returns `OK`.
3. Run `python scripts/build_index.py` to refresh `INDEX.md`.
4. Open a PR using the prompt-card issue template.

CI runs the same validation; PRs that don't pass won't be merged.

## License

Dual-licensed. See [`LICENSE`](LICENSE).

- **Code** (`scripts/`, CI configs): MIT
- **Prompt content** (`prompts/`, `templates/`, `docs/`): CC-BY-4.0

Each Prompt Card carries `license: CC-BY-4.0` in its frontmatter for
clarity.

## Status

v0.1 — seed release with 8 cards across all 7 directions. Roadmap and
open issues live on GitHub. Pull requests welcome.

---

## 中文摘要

**prompt-atlas** 是一个面向 LLM trainer、AI 产品经理、Prompt 工程师、
RLHF / SFT 数据团队、模型评估团队的精选 Prompt 库。和"awesome
prompts"式的素材合集不同，本仓库的每一个条目都是一张**Prompt
Card**——带元数据、变量、示例、失败模式与调优笔记的可复用工作
资产。

**两种使用方式：**

1. **作为 GitHub 仓库**：浏览 [`INDEX.md`](INDEX.md) 或
   `prompts/<方向>/` 目录，找到目标卡片后复制 `## Prompt` 段落，按
   `{{variable}}` 替换变量；务必阅读 `## Failure Modes` 和
   `## Tuning Notes` 两段——那是经验所在。
2. **作为 Claude Code Skill**：clone 到
   `~/.claude/skills/prompt-atlas`，然后在 Claude Code 里用自然语言
   描述任务（"帮我写个判断 passage 相关性的 prompt"），Claude 会
   通过 [`SKILL.md`](SKILL.md) 中的路由树定位到具体卡片。

**安全立场：** 拒收 jailbreak、绕过安全的 prompt、套取闭源模型内部
推理链路的 prompt、私有 / 泄露 / 付费课盗版 prompt。详见
[`docs/SAFETY.md`](docs/SAFETY.md)。评估类、红队评分、有害性标注
等防御方向的 prompt **明确欢迎**。

**贡献流程：** 复制 [`templates/prompt-card.md`](templates/prompt-card.md)
→ 填写 → `python scripts/validate.py` 通过 → 开 PR。详见
[`CONTRIBUTING.md`](CONTRIBUTING.md)。

License：脚本 MIT、prompt 内容 CC-BY-4.0。
