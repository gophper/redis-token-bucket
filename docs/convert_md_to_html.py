#!/usr/bin/env python3
"""
Convert a Markdown file to a self-contained HTML file.
All styles are embedded so the result is a single shareable file.

Usage:
    python3 convert_md_to_html.py [input.md] [output.html]

Defaults:
    input  = gateway-ratelimit-plan.md  (same directory as this script)
    output = gateway-ratelimit-plan.html (same directory as this script)
"""

import sys
import os
import re
import markdown
from markdown.extensions.tables import TableExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.toc import TocExtension

# ── Embedded CSS (GitHub-inspired, self-contained) ──────────────────────────
CSS = """
/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, "Noto Sans", sans-serif,
                 "Apple Color Emoji", "Segoe UI Emoji";
    font-size: 16px;
    line-height: 1.7;
    color: #24292f;
    background: #ffffff;
    padding: 0;
    margin: 0;
}

/* ── Page wrapper ── */
.page-wrapper {
    max-width: 960px;
    margin: 0 auto;
    padding: 48px 40px 80px;
}

/* ── Headings ── */
h1, h2, h3, h4, h5, h6 {
    font-weight: 600;
    line-height: 1.25;
    margin-top: 1.5em;
    margin-bottom: .5em;
    color: #1f2328;
}
h1 { font-size: 2em;   border-bottom: 2px solid #d0d7de; padding-bottom: .3em; }
h2 { font-size: 1.5em; border-bottom: 1px solid #d0d7de; padding-bottom: .3em; }
h3 { font-size: 1.25em; }
h4 { font-size: 1em; }
h5 { font-size: .875em; }
h6 { font-size: .85em; color: #636e7b; }

/* ── Paragraphs & inline ── */
p { margin: .8em 0; }
a { color: #0969da; text-decoration: none; }
a:hover { text-decoration: underline; }
strong { font-weight: 600; }
em { font-style: italic; }

/* ── Horizontal rule ── */
hr {
    border: none;
    border-top: 2px solid #d0d7de;
    margin: 2em 0;
}

/* ── Blockquote ── */
blockquote {
    border-left: 4px solid #d0d7de;
    padding: .5em 1em;
    color: #636e7b;
    background: #f6f8fa;
    border-radius: 0 4px 4px 0;
    margin: 1em 0;
}
blockquote p { margin: .3em 0; }

/* ── Code (inline) ── */
code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo,
                 "Courier New", monospace;
    font-size: .875em;
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: .2em .4em;
    color: #c9254e;
}

/* ── Code block ── */
pre {
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 1em 1.2em;
    overflow-x: auto;
    margin: 1em 0;
    line-height: 1.5;
}
pre code {
    font-size: .875em;
    background: transparent;
    border: none;
    padding: 0;
    color: #24292f;
    white-space: pre;          /* preserve ASCII art */
    word-break: normal;
    overflow-wrap: normal;
}

/* ── Tables ── */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
    font-size: .9em;
    overflow-x: auto;
    display: block;
}
thead tr { background: #f6f8fa; }
th, td {
    border: 1px solid #d0d7de;
    padding: .45em .9em;
    text-align: left;
    vertical-align: top;
}
tr:nth-child(even) td { background: #f6f8fa; }

/* ── Lists ── */
ul, ol {
    padding-left: 2em;
    margin: .5em 0;
}
li { margin: .3em 0; }
li > ul, li > ol { margin: .1em 0; }

/* ── Table of Contents (toc extension) ── */
.toc {
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 1em 1.5em;
    display: inline-block;
    min-width: 220px;
    margin-bottom: 1.5em;
}
.toc ul { list-style: none; padding-left: 1em; }
.toc > ul { padding-left: 0; }
.toc a { color: #0969da; }

/* ── Print ── */
@media print {
    body { background: #fff; color: #000; }
    .page-wrapper { padding: 0; max-width: 100%; }
    pre, blockquote { break-inside: avoid; }
    h1, h2, h3 { break-after: avoid; }
    a { color: #000; text-decoration: underline; }
}
"""

# ── HTML template ────────────────────────────────────────────────────────────
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{css}
</style>
</head>
<body>
<div class="page-wrapper">
{body}
</div>
</body>
</html>
"""


def extract_title(md_text: str) -> str:
    """Return the first H1 heading text, or a fallback string."""
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            # strip leading '# ' and any markdown bold/emphasis markers
            title = line[2:].strip()
            title = re.sub(r"[*_`]", "", title)
            return title
    return "Document"


def convert(input_path: str, output_path: str) -> None:
    with open(input_path, encoding="utf-8") as f:
        md_text = f.read()

    title = extract_title(md_text)

    extensions = [
        TableExtension(),
        FencedCodeExtension(),
        # TocExtension adds anchor IDs to every heading so in-page links work;
        # it also renders a table of contents wherever `[TOC]` appears in the
        # source.  The current document does not use `[TOC]`, but the heading
        # anchors are still useful for browser navigation.
        TocExtension(permalink=False),
        "nl2br",           # newlines inside paragraphs become <br>
        "sane_lists",      # saner list behaviour
    ]

    html_body = markdown.markdown(md_text, extensions=extensions)

    output = HTML_TEMPLATE.format(
        title=title,
        css=CSS,
        body=html_body,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"✓  Written to: {output_path}  ({len(output):,} bytes)")


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))

    input_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        script_dir, "gateway-ratelimit-plan.md"
    )
    output_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        script_dir,
        os.path.splitext(os.path.basename(input_path))[0] + ".html",
    )

    if not os.path.isfile(input_path):
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    convert(input_path, output_path)


if __name__ == "__main__":
    main()
