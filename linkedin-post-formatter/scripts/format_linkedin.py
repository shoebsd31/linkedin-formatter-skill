#!/usr/bin/env python3
"""Format a LinkedIn post: convert lightweight markup into LinkedIn-ready text.

A faithful Python port of Polypost's (github.com/markrussinovich/Polypost)
LinkedIn formatting logic. It:
  * converts **bold**, *italic*, ***bold italic***, `monospace`, ~~strike~~ and
    __underline__ markup into the Unicode LinkedIn renders (no native rich text,
    so styling uses math-alphanumeric glyphs and combining marks);
  * leaves URLs and #hashtags / @handles unstyled (styled glyphs break links and
    tag autocomplete);
  * flattens @[Display Name] mention tokens to "@Display Name" (spaces kept);
  * counts NFC-normalized code points against the 3000 limit (2800 warning).

Usage:
    python format_linkedin.py input.md
    python format_linkedin.py < input.md
    python format_linkedin.py --text "**hi**"
    python format_linkedin.py input.md -o out.txt
Post goes to stdout; the character-count report goes to stderr.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata

LINKEDIN_LIMIT = 3000
LINKEDIN_WARNING = 2800

# Hard ceiling on how much text we will parse. LinkedIn's own limit is 3000
# characters, so 5000 leaves comfortable headroom for an untrimmed draft while
# staying well below the size at which densely-alternating markup can drive the
# regex engine into super-linear backtracking. A runaway regex runs in C and
# cannot be interrupted from Python, so capping the INPUT is the only reliable
# denial-of-service guard.
MAX_INPUT_CHARS = 5000

TOKEN_PATTERN = re.compile(
    r"(https?://[^\s]+|[#@][A-Za-z0-9_][A-Za-z0-9_.\-]*)", re.UNICODE
)
MENTION_TOKEN = re.compile(r"@\[([^\]\[\n]+)\]")
EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF☀-➿←-⇿⬀-⯿]")

VARIANT_RANGES = {
    "bold": {"upper": 0x1D5D4, "lower": 0x1D5EE, "digit": 0x1D7EC},
    "italic": {"upper": 0x1D608, "lower": 0x1D622},
    "boldItalic": {"upper": 0x1D63C, "lower": 0x1D656, "digit": 0x1D7EC},
    "monospace": {"upper": 0x1D670, "lower": 0x1D68A, "digit": 0x1D7F6},
}
STRIKE_MARK = "̶"
UNDERLINE_MARK = "̲"


def is_mark(ch: str) -> bool:
    return unicodedata.category(ch).startswith("M")


def is_emoji(ch: str) -> bool:
    return bool(EMOJI_RE.match(ch))


def map_ascii_char(ch: str, variant: str) -> str:
    cp = ord(ch)
    ranges = VARIANT_RANGES[variant]
    if 65 <= cp <= 90:
        return chr(ranges["upper"] + cp - 65)
    if 97 <= cp <= 122:
        return chr(ranges["lower"] + cp - 97)
    if 48 <= cp <= 57 and "digit" in ranges:
        return chr(ranges["digit"] + cp - 48)
    return ch


def apply_combining(text: str, mark: str) -> str:
    out = []
    for ch in text:
        if ch.strip() and not is_emoji(ch) and not is_mark(ch):
            out.append(ch + mark)
        else:
            out.append(ch)
    return "".join(out)


def get_variant(bold: bool, italic: bool, code: bool):
    if code:
        return "monospace"
    if bold and italic:
        return "boldItalic"
    if bold:
        return "bold"
    if italic:
        return "italic"
    return None


def style_segment(text, *, bold=False, italic=False, code=False,
                  strike=False, underline=False):
    variant = get_variant(bold, italic, code)
    mapped = "".join(map_ascii_char(c, variant) for c in text) if variant else text
    if underline:
        mapped = apply_combining(mapped, UNDERLINE_MARK)
    if strike:
        mapped = apply_combining(mapped, STRIKE_MARK)
    return mapped


def style_text(text, **opts):
    if not text:
        return ""
    result = []
    last = 0
    for m in TOKEN_PATTERN.finditer(text):
        result.append(style_segment(text[last:m.start()], **opts))
        result.append(m.group(0))
        last = m.end()
    result.append(style_segment(text[last:], **opts))
    return "".join(result)


INLINE_RULES = [
    (re.compile(r"\*\*\*(.+?)\*\*\*", re.S), dict(bold=True, italic=True)),
    (re.compile(r"___(.+?)___", re.S), dict(bold=True, italic=True)),
    (re.compile(r"\*\*(.+?)\*\*", re.S), dict(bold=True)),
    (re.compile(r"__(.+?)__", re.S), dict(underline=True)),
    (re.compile(r"~~(.+?)~~", re.S), dict(strike=True)),
    (re.compile(r"`(.+?)`", re.S), dict(code=True)),
    (re.compile(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])", re.S), dict(italic=True)),
    (re.compile(r"(?<![_\w])_(?!\s)(.+?)(?<!\s)_(?![_\w])", re.S), dict(italic=True)),
]


def render_markup(text, **active):
    # Pick the EARLIEST match across all rules (ties broken by rule order, i.e.
    # most-specific marker first). Choosing by position rather than by rule lets
    # an outer marker win over an inner one in interleaved cases like ~~__x__~~,
    # so both styles are applied.
    #
    # The scan over the tail is iterative rather than recursive: a post with many
    # sequential markers (e.g. "**a** **b** **c** ...") would otherwise recurse
    # once per marker and overflow Python's stack (RecursionError) on adversarial
    # input. Only genuine *nesting* recurses (m.group(1)), and that depth is tiny.
    out = []
    while True:
        best = None
        for pattern, opts in INLINE_RULES:
            m = pattern.search(text)
            if m and (best is None or m.start() < best[0].start()):
                best = (m, opts)
        if best is None:
            out.append(style_text(text, **active) if active else text)
            return "".join(out)
        m, opts = best
        # Text before the earliest match has no earlier marker, so style it directly.
        before = text[:m.start()]
        out.append(style_text(before, **active) if active else before)
        merged = {**active, **{k: active.get(k, False) or v for k, v in opts.items()}}
        out.append(render_markup(m.group(1), **merged))  # nesting only — shallow
        text = text[m.end():]  # continue scanning the tail iteratively


def flatten_mentions(text):
    def repl(m):
        name = m.group(1).strip()
        return f"@{name}" if name else m.group(0)
    return MENTION_TOKEN.sub(repl, text)


def strip_heading_markers(text):
    out = []
    for line in text.split("\n"):
        hm = re.match(r"^\s{0,3}(#{1,6})\s+(.*)$", line)
        out.append("**" + hm.group(2).strip() + "**" if hm else line)
    return "\n".join(out)


def format_post(text):
    if len(text) > MAX_INPUT_CHARS:
        raise ValueError(
            f"input is {len(text)} characters; refusing to format more than "
            f"{MAX_INPUT_CHARS} (LinkedIn's limit is {LINKEDIN_LIMIT})."
        )
    text = strip_heading_markers(text)
    text = flatten_mentions(text)
    return render_markup(text).strip()


def count_chars(text):
    return len(unicodedata.normalize("NFC", text))


def report(text):
    n = count_chars(text)
    if n > LINKEDIN_LIMIT:
        status = f"OVER LIMIT by {n - LINKEDIN_LIMIT} (max {LINKEDIN_LIMIT})"
    elif n >= LINKEDIN_WARNING:
        status = f"approaching limit (warn at {LINKEDIN_WARNING}, max {LINKEDIN_LIMIT})"
    else:
        status = f"OK (max {LINKEDIN_LIMIT})"
    return f"[char count] {n} / {LINKEDIN_LIMIT} - {status}"


def main(argv=None):
    p = argparse.ArgumentParser(description="Format text into a LinkedIn-ready post.")
    p.add_argument("input", nargs="?", help="input file. Omit to read stdin.")
    p.add_argument("--text", help="inline text to format instead of a file")
    p.add_argument("-o", "--output", help="also write the formatted post here")
    args = p.parse_args(argv)

    if args.text is not None:
        raw = args.text
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()

    try:
        formatted = format_post(raw)
    except ValueError as exc:
        sys.stderr.write(f"[error] {exc}\n")
        return 2
    sys.stdout.write(formatted + "\n")
    sys.stderr.write(report(formatted) + "\n")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(formatted + "\n")
        sys.stderr.write(f"[written] {args.output}\n")

    return 0 if count_chars(formatted) <= LINKEDIN_LIMIT else 1


if __name__ == "__main__":
    raise SystemExit(main())
