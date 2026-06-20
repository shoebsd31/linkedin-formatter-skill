#!/usr/bin/env python3
"""Offline test suite for the LinkedIn formatter.

Pure standard library — no pytest, no pip install. Run it directly:

    python tests/test_format_linkedin.py

It exits 0 if every check passes, 1 otherwise, and prints a summary. The cases
cover (a) Polypost's own reference outputs, so we know the Unicode code points
match what LinkedIn renders, and (b) the skill's behavioural rules: mentions,
untouched links/hashtags, heading conversion, character counting, and the
over-limit signal.
"""
import importlib.util
import os
import sys

# Import format_linkedin.py from the sibling scripts/ directory.
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "format_linkedin.py")
spec = importlib.util.spec_from_file_location("format_linkedin", SCRIPT)
fl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fl)

passed = 0
failed = 0


def check(name, got, expected):
    global passed, failed
    if got == expected:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")
        print(f"          expected: {expected!r}")
        print(f"          got:      {got!r}")


def check_true(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")


print("Polypost reference cases (exact Unicode must match):")
check("bold maps to sans-serif bold", fl.format_post("**Abc 123**"), "𝗔𝗯𝗰 𝟭𝟮𝟯")
check("italic maps to sans-serif italic", fl.format_post("*Ahz*"), "𝘈𝘩𝘻")
check("bold italic", fl.format_post("***Hi!***"), "𝙃𝙞!")
check("monospace", fl.format_post("`Code 9`"), "𝙲𝚘𝚍𝚎 𝟿")
check("underline via combining mark", fl.format_post("__Underlined #LinkedIn__"),
      "U̲n̲d̲e̲r̲l̲i̲n̲e̲d̲ #LinkedIn")
check("URLs and #/@ tokens stay unstyled inside bold",
      fl.format_post("**Post #LinkedIn @Ada https://example.com**"),
      "𝗣𝗼𝘀𝘁 #LinkedIn @Ada https://example.com")
check("nested strike+underline both apply",
      fl.format_post("~~__Ship now__~~"), "S̶̲h̶̲i̶̲p̶̲ n̶̲o̶̲w̶̲")

print("\nSkill behaviour rules:")
check("mention flattens, spaces kept", fl.format_post("Thanks @[Scott Hanselman]!"),
      "Thanks @Scott Hanselman!")
check("## heading becomes a bold line",
      fl.format_post("## Title"), "𝗧𝗶𝘁𝗹𝗲")
check_true("a plain URL is preserved verbatim",
           "https://acme.example.com/x" in fl.format_post("See https://acme.example.com/x"))
check_true("no literal ** left after formatting",
           "**" not in fl.format_post("Make this **bold** please"))
check("char count is NFC code points", fl.count_chars("hello"), 5)
check_true("report flags an over-limit post",
           "OVER LIMIT" in fl.report("a" * 3001))
check_true("report says OK for a short post",
           "OK" in fl.report("a short post"))

print("\nSecurity hardening regressions:")
# Call render_markup directly (bypassing the input-size guard) to prove the
# parser itself no longer overflows the stack on many sequential markers.
check_true("2000 sequential markers parse without RecursionError",
           isinstance(fl.render_markup("**a**" * 2000), str))
check_true("a heavily-marked-up in-range post formats fine",
           isinstance(fl.format_post("**a** *b* ~~c~~ " * 250), str))
try:
    fl.format_post("x" * (fl.MAX_INPUT_CHARS + 1))
    _guard_ok = False
except ValueError:
    _guard_ok = True
check_true("oversized input is refused with ValueError (DoS guard)", _guard_ok)

print(f"\n{passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
