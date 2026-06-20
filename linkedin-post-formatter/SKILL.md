---
name: linkedin-post-formatter
description: >-
  Write and format a ready-to-publish LinkedIn post from a topic, idea, rough
  notes, draft, article, or announcement. Use this skill whenever the user wants
  to create, write, draft, polish, reformat, or "make a LinkedIn post" — even if
  they only give a topic and don't say the word "format." It crafts the copy
  (hook, structure, line-break spacing, call to action) AND converts it into
  LinkedIn-ready text: Unicode bold/italic (LinkedIn has no native rich text),
  @[Name] mentions, hashtags, emoji, and a hard check against LinkedIn's 3000-
  character limit. Trigger on requests like "turn this into a LinkedIn post,"
  "write a LinkedIn post about X," "make this sound good for LinkedIn," "I need a
  post announcing our launch," or pasting a blog/draft and asking to post it.
  Do NOT use for X/Twitter, Threads, Instagram, or generic copywriting that
  isn't destined for LinkedIn.
---

# LinkedIn Post Formatter

Turn a topic, draft, or rough notes into a polished, ready-to-paste LinkedIn
post. The job has two halves that you do in order:

1. **Write the post** — craft strong copy following LinkedIn's conventions.
2. **Format the post** — run the bundled script to convert your lightweight
   markup into LinkedIn-ready Unicode and verify the character count.

LinkedIn's composer has no rich-text formatting (no real bold, italic,
headings, or bullets), so "bold" on LinkedIn is actually special Unicode glyphs
that look bold. The script handles that conversion deterministically — you never
hand-type Unicode. Your job is to write great copy and mark it up with simple
markdown-style symbols.

## Step 1 — Write the post

If the user gave only a topic or rough notes, you are writing the whole post.
If they gave a draft or article, you are restructuring and tightening it for
LinkedIn. Either way, apply these conventions (full detail in
`references/writing-guide.md` — read it when you want depth on any point):

- **Hook first.** The opening 1–2 lines are all that show before the "…more"
  fold. Lead with the most surprising, useful, or human line. No throat-clearing
  ("I'm excited to share…"). Make someone stop scrolling.
- **One idea per line, generous white space.** Short paragraphs (1–3 lines)
  separated by blank lines. Walls of text die on LinkedIn. Use blank lines
  deliberately — they survive into the final post 1:1.
- **Skimmable body.** Use line-broken lists (a leading "→", "•", or "—" then a
  space) rather than dense prose when enumerating. LinkedIn has no real bullet
  lists, so these are just characters at the start of a line.
- **Concrete > abstract.** Specific numbers, examples, and stories beat
  generalities.
- **End with a CTA or question** to invite comments (engagement favors replies).
- **Hashtags:** 3–5 relevant ones, placed at the very end. Write them as
  `#likeThis`.
- **Mentions:** to tag a person or company, write `@[Their Full Name]`. The
  script renders it as `@Their Full Name`. (In LinkedIn's own composer the
  Polypost extension turns this into a real clickable mention; when pasting
  plain text, the user types the `@` and picks the name from LinkedIn's popup.)
- **Emoji:** use sparingly and purposefully (a section marker or accent), not
  in every line. They count toward the limit.
- **Length:** aim for 1300–2000 characters for most posts; the hard cap is 3000.

Write the post using this lightweight markup (this is what the script reads):

| You write              | LinkedIn shows                  | Use for                       |
|------------------------|---------------------------------|-------------------------------|
| `**bold**`             | bold Unicode glyphs             | key phrases, mini-headings    |
| `*italic*`             | italic Unicode glyphs           | emphasis, titles              |
| `***bold italic***`    | bold-italic glyphs              | strong emphasis               |
| `` `code` ``           | monospace glyphs                | code, handles, literals       |
| `~~strike~~`           | strikethrough                   | corrections, before/after     |
| `__underline__`        | underline                       | rare emphasis                 |
| `## Heading`           | a bold line                     | section headers (no real H1)  |
| `@[Jane Doe]`          | `@Jane Doe`                     | mentions                      |
| `#topic`               | `#topic` (unstyled)             | hashtags                      |

Use Unicode styling **sparingly** — a post in all-bold is hard to read and hurts
accessibility (screen readers may skip math-alphanumeric glyphs). Bold a handful
of key phrases or mini-headings, not whole paragraphs.

## Step 2 — Format and verify with the script

Write your marked-up draft to a temp file, then run the bundled script to
convert it. The script does the formatting deterministically: it maps the markup
to the exact Unicode glyphs LinkedIn renders, leaves URLs/hashtags/handles
untouched, flattens `@[Name]` mentions, prints the finished post to **stdout**,
and prints a character-count report to **stderr**.

```bash
# From the skill directory — capture the formatted post from stdout:
python scripts/format_linkedin.py draft.md
# or pipe the draft straight in:
printf '%s' "Your **draft** here" | python scripts/format_linkedin.py
```

Capture stdout — that styled text IS the final post to give the user. Read the
stderr line, e.g. `[char count] 1742 / 3000 - OK (max 3000)`. If it reports
**OVER LIMIT**, tighten the copy and re-run — never ship a post over 3000
characters, because LinkedIn truncates it mid-sentence. If it reports
**approaching limit** (≥2800), trim for safety.

Always run the script rather than hand-typing Unicode: it guarantees the exact
code points LinkedIn renders and an accurate count (NFC-normalized code points,
the same rule LinkedIn uses). You write the words; the script guarantees the
formatting.

## Step 3 — Deliver as a copy-card

Deliver the finished post in a **visual card with a Copy button**, rendered via
the `show_widget` tool (call `read_me` with module `mockup` first if you haven't
this session). The card is the default deliverable — it lets the user copy the
whole post, Unicode formatting intact, in one click and paste it straight into
LinkedIn.

Build the card from the template in `assets/card_template.html`. Read that file,
then substitute three things:
- the styled post text the script printed to stdout (drop it into the
  `<div id="post">…</div>`, preserving line breaks — no markup, no code fences).
  **HTML-escape it first** (`&`→`&amp;`, `<`→`&lt;`, `>`→`&gt;`): the text comes
  from user input, so substituting it raw would let crafted input inject markup
  into the card. Escaping leaves the Unicode styling untouched and the Copy
  button still copies clean text via `innerText`.
- the character count in the header (e.g. `1,742`),
- the mention reminder line, HTML-escaped too (name the person to retype the
  `@` for, or remove the line if the post has no `@[Name]` mentions).

The card's Copy button copies `post.innerText`, so whatever you place in that div
is exactly what lands on the clipboard. Keep the post text pristine.

Alongside the card, in your normal chat reply, add one short line with the
character count and the same mention reminder (so it's visible even if the widget
doesn't render). Don't paste the full post again as plain text — the card is the
copyable source of truth. Do not save a file unless the user asks.

If the `show_widget` tool isn't available in the current environment, fall back
to delivering the post as a clean plain-text block in chat (post on its own, then
the character-count line and mention reminder below it).

## Notes and edge cases

- **Don't over-style.** If the user didn't ask for bold everywhere, keep styling
  to a few key phrases. Readability and reach matter more than decoration.
- **Links:** LinkedIn shows a preview card for the first URL. Put the primary
  link on its own line. Some advise moving links to the first comment to protect
  reach — mention this option if relevant, but follow the user's preference.
- **Accessibility:** Unicode "bold" is not real bold and can be unreadable to
  screen readers. Never style an entire post; never put essential meaning only
  in styled text.
- The script is a faithful port of Polypost's LinkedIn formatter
  (github.com/markrussinovich/Polypost). See `references/writing-guide.md` for
  the writing playbook.
