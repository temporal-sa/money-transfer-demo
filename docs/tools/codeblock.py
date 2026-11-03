# /// script
# requires-python = ">=3.10"
# dependencies = ["pygments>=2.18"]
# ///
"""Copied from pick-a-card-demo-python/walkthrough/codeblock.py (2026-10-28) and extended: the
highlighter follows the file's extension (Java here), or --lang for stdin, instead of always Python.

A walkthrough's code panel: the build's own lines, coloured, numbered in a left gutter, wrapping
instead of running off the page. Paste its output where the panel goes; the CSS is in README.md.

  uv run walkthrough/codeblock.py builds/<card>/workflows.py --from "import asyncio" \\
      --mark "from desk import ask=1" --mark "@workflow.defn=2" --title workflows.py
  uv run walkthrough/codeblock.py desk.py --range "def validate::self.answers[a[" --range "wait = ::return desk" \\
      --mark "def validate=9" --title "desk.py (the parts that matter)"
  echo 'worker = Worker(...)' | uv run walkthrough/codeblock.py - --title worker.py

--range FROM::TO picks the lines from the first containing FROM to the next containing TO (FROM can
span lines: "@activity.defn\nasync def pay" finds that decorator on that function); several
ranges are joined by a "…" line. --mark TEXT=N puts number N beside the first shown line containing
TEXT. The common indent is removed, so a method body starts at the left edge."""

import argparse
import html
import re
import sys
import textwrap
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer, get_lexer_by_name, get_lexer_for_filename
from pygments.util import ClassNotFound

LEXER = PythonLexer()

GAP = "…"


def starts(lines: list[str], n: int, text: str) -> bool:
    """Line n contains text; a text with newlines matches that many lines from n."""
    parts = text.split("\n")
    return n + len(parts) <= len(lines) and all(p in lines[n + k] for k, p in enumerate(parts))


def pick(lines: list[str], start: str | None, end: str | None) -> list[str]:
    i = next((n for n in range(len(lines)) if starts(lines, n, start)), None) if start else 0
    if i is None:
        sys.exit(f"codeblock: no line contains {start!r}")
    if not end:
        return lines[i:]
    j = next((n for n in range(i, len(lines)) if end in lines[n]), None)
    if j is None:
        sys.exit(f"codeblock: no line after {start!r} contains {end!r}")
    return lines[i:j + 1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("file", help="the build's file, or - for stdin")
    ap.add_argument("--from", dest="start", help="start at the first line containing this")
    ap.add_argument("--to", dest="end", help="end at the next line containing this")
    ap.add_argument("--range", action="append", default=[], metavar="FROM::TO")
    ap.add_argument("--mark", action="append", default=[], metavar="TEXT=N")
    ap.add_argument("--title", default="")
    ap.add_argument("--lang", default="", help="the language for stdin (default: from the file name, else Python)")
    ap.add_argument("--after", type=int, default=0, metavar="N",
                    help="the last note number in the panels above this one: numbers here must follow it")
    a = ap.parse_args()
    global LEXER
    try:
        LEXER = get_lexer_by_name(a.lang) if a.lang else get_lexer_for_filename(a.file if a.file != "-" else "x.py")
    except ClassNotFound:
        LEXER = PythonLexer()

    src = (sys.stdin.read() if a.file == "-" else Path(a.file).read_text()).rstrip("\n").split("\n")
    if a.range:
        shown: list[str] = []
        for r in a.range:
            start, _, end = r.partition("::")
            if shown:
                shown.append(GAP)
            shown += pick(src, start, end or None)
    else:
        shown = pick(src, a.start, a.end)
    while shown and not shown[-1].strip():
        shown.pop()

    # Dedent around the gap lines, then colour the whole excerpt at once so multi-line constructs
    # keep their colours, and split it back into lines. A prefix keeps Pygments' classes (n, m, ...)
    # from clashing with the page's own.
    body = [l for l in shown if l != GAP]
    indent = len(body[0]) - len(textwrap.dedent("\n".join(body)).split("\n")[0]) if body else 0
    plain = [l if l == GAP else l[indent:] for l in shown]
    coloured = highlight("\n".join(plain), LEXER, HtmlFormatter(nowrap=True, classprefix="tok-"))
    coloured = coloured.rstrip("\n").split("\n")
    # A long line wraps after an opening bracket, a comma or an =, as you'd split it by hand.
    coloured = [re.sub(r'(<span class="tok-(?:p|o)">(?:\(|\[|,|=)</span>)', r"\1<wbr>", l) for l in coloured]

    marks: dict[int, str] = {}
    for m in a.mark:
        text, _, n = m.rpartition("=")
        i = next((k for k, l in enumerate(plain) if text in l and k not in marks), None)
        if i is None:
            sys.exit(f"codeblock: no shown line contains {text!r} for mark {n}")
        marks[i] = n

    # Notes are read in page order, so the numbers down this panel must rise and follow the panels above.
    order = [int(marks[k]) for k in sorted(marks) if marks[k].isdigit()]
    if order and (order != sorted(order) or order[0] <= a.after):
        sys.exit(f"codeblock: the numbers read {', '.join(map(str, order))} down the panel"
                 + (f" after {a.after} above it" if a.after else "")
                 + ": number the notes in the order they appear on the page")

    rows = []
    for k, (raw, col) in enumerate(zip(plain, coloured)):
        lead = len(raw) - len(raw.lstrip(" "))
        gutter = f'<span class="gm">{marks[k]}</span>' if k in marks else ""
        if raw == GAP:
            text, cls = GAP, "t gap"
        else:
            text, cls = (col.lstrip(" ") or "&nbsp;"), "t"
        # The line's own indent becomes padding; a wrapped remainder hangs 4ch further in.
        rows.append(f'<div class="ln"><span class="g">{gutter}</span>'
                    f'<span class="{cls}" style="padding-left:min({lead + 4}ch, 45%);text-indent:-4ch">{text}</span></div>')
    title = f'<div class="file">{html.escape(a.title)}</div>' if a.title else ""
    print(f'<div class="code">{title}<div class="lines">\n' + "\n".join(rows) + "\n</div></div>")


if __name__ == "__main__":
    main()
