# LinkedIn Post Formatter

A Claude skill that turns a topic, draft, or rough notes into a polished,
ready-to-paste LinkedIn post. Claude writes the copy (hook, structure, spacing,
call to action, hashtags) and a bundled Python script converts it into the exact
Unicode that LinkedIn renders — real **bold**/*italic* glyphs, flattened
mentions, protected links — then checks it against LinkedIn's 3000-character
limit.

The formatting logic is a faithful port of
[Polypost](https://github.com/markrussinovich/Polypost).

---

## What it does

- **Writes the post for you** from a topic, idea, draft, or article — with a
  scroll-stopping hook, airy line spacing, skimmable structure, and a closing
  call to action.
- **Formats it for LinkedIn**, which has no native rich text:
  - `**bold**`, `*italic*`, `***bold italic***`, `` `monospace` ``, `~~strike~~`,
    `__underline__` → the Unicode glyphs LinkedIn displays.
  - `@[Full Name]` → `@Full Name` (ready for you to turn into a real tag).
  - URLs, `#hashtags`, and `@handles` are left untouched so links and tags work.
- **Checks length** the way LinkedIn does (NFC code points) against the 3000
  limit, warning at 2800.
- **Delivers the finished post in a copy-card** — a visual card with a one-click **Copy** button, so you grab the whole post (formatting intact) and paste it straight into LinkedIn.

---

## How to use it (in Claude / Cowork)

Just ask. The skill triggers on natural requests — you don't need to mention
"format" or "Unicode." For example:

- "Write a LinkedIn post about how we cut our deploy time in half."
- "Turn this draft into a LinkedIn post and make the key parts bold."
- "I need a short, punchy LinkedIn post sharing one contrarian lesson about
  hiring. Tag @[Maria Gomez]."
- "Make this blog intro sound good for LinkedIn."

Claude writes the post, runs the formatter, and hands it back as a **copy-card**:
a tidy card showing the finished post with a **Copy** button and a live character
count. Click **Copy**, then paste into LinkedIn's composer — the bold, italics,
and spacing are already baked in.

### Tagging people

Write a mention as `@[First Last]`. In the finished post it appears as
`@First Last`. LinkedIn can't create a real, clickable tag from pasted text, so
when you paste into LinkedIn, **type the `@` yourself at that spot and pick the
person from LinkedIn's dropdown**.

### A note on styled text

LinkedIn "bold" is actually special Unicode glyphs, not true bold. Use it
sparingly — a few key phrases or mini-headings, never whole paragraphs. Screen
readers may skip these glyphs, so never put essential meaning *only* in styled
text. The skill applies this restraint by default.

---

## Using the formatter script directly (optional)

You normally never touch the script — Claude runs it. But it also works as a
standalone command-line tool if you want to format text yourself.

```bash
# Format a markdown-ish file (post prints to your screen):
python scripts/format_linkedin.py draft.md

# Pipe text straight in:
echo "Big news: our **dashboard** is live → https://acme.com" | python scripts/format_linkedin.py

# Format an inline string:
python scripts/format_linkedin.py --text "Thanks @[Ada Lovelace] for **this**!"

# Also save the result to a file:
python scripts/format_linkedin.py draft.md -o linkedin-post.txt
```

The formatted post is printed to **stdout**; a character-count report is printed
to **stderr**, e.g.:

```
[char count] 1742 / 3000 - OK (max 3000)
```

The script exits non-zero if the post is over the 3000-character limit, so it
can be used in automation.

### Markup reference

| You write           | LinkedIn shows           | Use for                      |
|---------------------|--------------------------|------------------------------|
| `**bold**`          | bold glyphs              | key phrases, mini-headings   |
| `*italic*`          | italic glyphs            | emphasis, titles             |
| `***bold italic***` | bold-italic glyphs       | strong emphasis              |
| `` `code` ``        | monospace glyphs         | code, literals               |
| `~~strike~~`        | strikethrough            | corrections, before/after    |
| `__underline__`     | underline                | rare emphasis                |
| `## Heading`        | a bold line              | section headers (no real H1) |
| `@[Jane Doe]`       | `@Jane Doe`              | mentions                     |
| `#topic`            | `#topic` (unstyled)      | hashtags                     |

Requires **Python 3** (standard library only — no packages to install).

---

## Testing and evaluation

There are two layers of checks, and they answer different questions.

### 1. Formatter tests — "is the Unicode conversion correct?"

A self-contained test suite that verifies the formatter against Polypost's own
reference outputs plus the skill's behavioural rules (mentions, untouched
links/hashtags, heading conversion, character counting, the over-limit signal).
Pure standard library — nothing to install. From the skill folder:

```bash
cd linkedin-post-formatter
python tests/test_format_linkedin.py
```

It prints a pass/fail line per check and exits `0` only if everything passes, so
you can wire it into CI:

```
14 passed, 0 failed
```

Run this whenever you change `scripts/format_linkedin.py` — it catches
regressions instantly. To add a case, open `tests/test_format_linkedin.py` and
add a `check("name", format_post("input"), "expected output")` line.

### 2. Skill evals — "does the skill write better posts than no skill?"

This is the higher-level evaluation: it runs realistic prompts through Claude
**with** the skill and **without** it (a baseline), then grades each result
against objective assertions and reports the pass-rate difference. It's how you
confirm the skill actually adds value, not just that the code runs.

The test cases live in `linkedin-post-formatter/evals/evals.json` — each is a
realistic prompt plus the assertions a good post must satisfy (e.g. "uses real
Unicode glyphs," "no literal `**` left," "URL intact," "under 3000 chars").

Unlike the formatter tests, these aren't a single CLI command — running them
needs Claude driving the sub-agents. The practical way to run them:

> Ask Claude (in Cowork or Claude Code, with the `skill-creator` skill available):
> **"Run the evals in `linkedin-post-formatter/evals/evals.json` against the
> linkedin-post-formatter skill."**

Claude will, for each prompt, run it with and without the skill, grade the
assertions, aggregate a benchmark (pass rates + the delta), and open a review
viewer so you can read every post side by side. Results land in a
`linkedin-post-formatter-workspace/` folder (git-ignored — it's regenerated
output, not source). To broaden coverage, add more prompts and assertions to
`evals.json` before running.

---

## What's in this folder

```
linkedin-post-formatter/
├── SKILL.md                     # instructions Claude follows
├── scripts/
│   └── format_linkedin.py       # the deterministic formatter
├── tests/
│   └── test_format_linkedin.py  # offline formatter test suite
├── assets/
│   └── card_template.html       # the copy-card delivery template
├── references/
│   └── writing-guide.md         # the post-writing playbook
└── evals/
    └── evals.json               # skill-level A/B eval prompts + assertions
README.md                        # this file (repo root)
.gitignore
```

---

## Installing the skill

If you have the packaged `linkedin-post-formatter.skill` file, open it in
Cowork / Claude and choose **Save skill**. Once installed, just ask Claude to
write or format a LinkedIn post and the skill activates automatically.

To change the skill, edit the files here, then re-package the folder.

---

## Credits

Formatting logic adapted from
[Polypost](https://github.com/markrussinovich/Polypost) by Mark Russinovich
(MIT License).
