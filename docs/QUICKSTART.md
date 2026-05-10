# Quickstart — 5 minutes from zero to using a Prompt Card

Audience: anyone who wants to **use** a prompt from this library —
including non-technical users (PMs, content folks, anyone who pastes
prompts into ChatGPT / Claude / Gemini). You do NOT need to install
git, Python, or anything else to follow this guide.

> 中文版本在文末。

---

## The whole flow in one minute

1. **Find the card** that matches what you want to do (the
   [INDEX](../INDEX.md) lists all of them grouped by direction).
2. **Open the card file** — it's a single Markdown page on GitHub.
3. **Read the `Quick Use` block** at the very top of the card.
4. **Copy the prompt** from the `## Prompt` section (GitHub shows a
   "Copy" button when you hover over the code block).
5. **Replace `{{placeholders}}`** with your actual inputs.
6. **Paste into ChatGPT / Claude / Gemini / your tool of choice**, send.

That's it. The next sections walk through one example end-to-end.

---

## Walkthrough — using the `llm-judge-rubric-open-ended` card

Suppose you have an AI-generated response to a question, and you want
a structured quality assessment instead of a vibe-check. We'll use the
[`eval/llm-judge-rubric-open-ended`](../prompts/eval/llm-judge-rubric-open-ended.md)
card.

### Step 1 — open the card

Click the link above (or browse to it from
[`INDEX.md`](../INDEX.md)). You'll see a Markdown page that starts
with some YAML metadata (the lines between `---` markers — you can
skip these), then sections like `## Quick Use`, `## Purpose`,
`## Prompt`, etc.

### Step 2 — read `## Quick Use`

This block tells you what the card is for and what to fill in. For
example:

> **Use when:** You have a single AI output and want a structured
> quality score on factuality, instruction-following, coherence,
> and completeness.
> **Fill in:** `{{task_description}}` with what the AI was asked to
> do; `{{model_output}}` with the AI's response; `{{reference_answer}}`
> empty if you don't have a gold reference.
> **You'll get:** Per-dimension scores 1-5 plus a holistic verdict.
> Output is JSON.

### Step 3 — copy the `## Prompt` block

Find the `## Prompt` heading in the card and copy the text block
underneath. It looks like:

```text
You are an evaluation judge. Score the model output on each rubric dimension
from 1 (poor) to 5 (excellent), then give a holistic verdict.

Rubric:
- factuality: ...
- instruction_following: ...
- coherence: ...
- completeness: ...

Task description:
{{task_description}}

Model output:
{{model_output}}

Reference answer (may be empty if no reference exists):
{{reference_answer}}

Return ONLY this JSON object: ...
```

### Step 4 — replace the `{{placeholders}}`

Anywhere you see `{{something}}` in the prompt, swap it for your
actual content. For example, if you're asking the AI to summarize an
article and you have its response, the filled prompt looks like:

```text
...
Task description:
Summarize the following 800-word article in three bullet points.

Model output:
- The Voyager 1 spacecraft entered interstellar space in 2012.
- It continues to send data despite being over 24 billion km from Earth.
- Its primary instruments are nearing the end of their operational life.

Reference answer (may be empty if no reference exists):

...
```

(Notice we left `reference_answer` blank because the card explicitly
allows that — the **Quick Use** said so.)

### Step 5 — paste and send

Drop the filled prompt into ChatGPT / Claude / Gemini and hit send.
You'll get back something like:

```json
{
  "scores": {
    "factuality": 4,
    "instruction_following": 5,
    "coherence": 5,
    "completeness": 4
  },
  "verdict": "good",
  "decision_basis": "Three relevant bullets at the right register; minor gaps on technical detail.",
  "issues": ["Does not mention the specific date of the heliopause crossing."]
}
```

**That's the result.** You can read it as-is (each field labeled in
plain words), or pass it into a script if you're automating something.

---

## Common questions

### "What is JSON? I'm not a programmer."

JSON is just a structured text format with `{`, `}`, `:`, `,`, and
`"`. You can read it visually:

```json
{
  "verdict": "good",
  "score": 4
}
```

means: the verdict is "good", the score is 4. You can also just
**ignore the JSON shape and read the values** — the LLM will format
it nicely. If a card's output is JSON, the `Quick Use` block tells
you what fields to look at.

If you want plain English instead of JSON, you can add to the prompt:
*"After the JSON, also explain it in one paragraph in plain English."*
This works on most strong models.

### "What if a card has `output_schema: structured-json`?"

Means the card is designed to produce JSON. Either read the JSON
visually (see above), or use it programmatically. Most cards in this
library output JSON because it makes the result auditable — you can
clearly see scores, verdicts, and rationales as separate fields.

### "What if a card has `output_schema: text`?"

Means the output is plain text — you'll just get a paragraph or two
back, no JSON. (Example: `rag/hyde-hypothetical-answer-generator`.)

### "What if I don't know which card to use?"

Two ways:

1. **Browse [INDEX.md](../INDEX.md)** — cards are grouped by
   direction (RAG, Agent, RLHF, SFT, Multimodal, CoT, Eval) with a
   "Use when" column.
2. **Read the README's "I want to..." section** — maps user goals to
   recommended cards in plain English.

### "What models does this work on?"

Each card has a `models` field in its metadata listing model classes
the card has been tested with. Some cards work on most modern LLMs
(`generic`); others need a strong frontier model
(`frontier-closed`) or a vision model (`vision-language`). The
**Tuning Notes** section in each card explains what changes if you
use a weaker model.

### "What does `{{variable}}` mean?"

It's a placeholder — a slot for you to fill in. Whenever you see
double curly braces around a name, replace the entire `{{...}}`
(braces and all) with your actual content. The `Quick Use` block
tells you what each one expects.

### "Can I modify a card's prompt?"

Yes — these are reusable prompts, not sacred text. The card gives
you a tested baseline; you can adapt the wording, add domain
context, or tighten constraints. The `## Tuning Notes` section in
each card often suggests what knobs to turn.

### "What if I find a bug or want to suggest a card?"

Open an issue: https://github.com/huck012428-lab/prompt-atlas/issues
There are templates for "new prompt card request" and "bug report".

---

## 中文版本

**5 分钟从零到能用一张 Prompt Card** —— 适合任何想用本库的用户，**不需要装 git / Python / 任何工具**。

### 完整流程一分钟版

1. **找到合适的卡**：去 [INDEX](../INDEX.md) 按方向浏览；或看 README 的"我想做..."导航。
2. **打开卡片**：点开 GitHub 上的 .md 文件。
3. **读 `## Quick Use` 段**：在卡片最上面，告诉你这张卡能做什么、要填什么、会输出什么。
4. **复制 `## Prompt` 段的内容**：把那个代码块整段复制（GitHub 鼠标悬停代码块会出现复制按钮）。
5. **替换 `{{占位符}}`**：把所有 `{{xxx}}` 换成你自己的输入。
6. **粘贴到 ChatGPT / Claude / Gemini**：发送，看结果。

### 常见疑问

**Q：什么是 JSON？我不会编程。**
A：JSON 是带 `{ } : , "` 的结构化文本，肉眼能读：
```json
{ "verdict": "good", "score": 4 }
```
意思是 verdict 是 "good"，score 是 4。如果不想看 JSON，可以在 prompt 末尾加一句"在 JSON 后面再用一段中文解释一下"，强模型都能配合。

**Q：怎么知道用哪张卡？**
A：两条路 ——
- 看 [INDEX.md](../INDEX.md)：按方向分组，每张卡都有"Use when"列说明用途。
- 看 README 的"我想做..."段：直接把"我要做的事"映射到推荐的卡片。

**Q：`{{variable}}` 是什么意思？**
A：占位符，给你留的空。看到 `{{xxx}}` 就把它整体（包括两个大括号）换成你自己的内容。Quick Use 会告诉你每个占位符要填什么。

**Q：能改 prompt 吗？**
A：能，这是可复用 prompt，不是教条。卡片给你一个已经测过的基线，你可以按需修改 —— `## Tuning Notes` 段往往写了哪些旋钮值得调。

**Q：发现 bug / 想提议加卡片？**
A：开 issue：https://github.com/huck012428-lab/prompt-atlas/issues
