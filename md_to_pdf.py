#!/usr/bin/env python3
"""
md_to_pdf.py — Convert Markdown files to professional PDF documentation.

Usage:
    python md_to_pdf.py input.md [output.pdf] [--theme THEME] [--toc]

Themes: default, dark, minimal, technical
"""

import argparse
import os
import sys
import re
from pathlib import Path

import markdown
from markdown.extensions import codehilite, toc, tables, fenced_code
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

# ── Pygments CSS for syntax highlighting ──────────────────────────────────────
PYGMENTS_CSS = """
.codehilite .hll { background-color: #ffffcc }
.codehilite  { background: #f8f8f8; }
.codehilite .c { color: #8f5902; font-style: italic }
.codehilite .err { color: #a40000; border: 1px solid #ef2929 }
.codehilite .g { color: #000000 }
.codehilite .k { color: #204a87; font-weight: bold }
.codehilite .l { color: #000000 }
.codehilite .n { color: #000000 }
.codehilite .o { color: #ce5c00; font-weight: bold }
.codehilite .x { color: #000000 }
.codehilite .p { color: #000000; font-weight: bold }
.codehilite .cm { color: #8f5902; font-style: italic }
.codehilite .cp { color: #8f5902; font-style: italic }
.codehilite .c1 { color: #8f5902; font-style: italic }
.codehilite .cs { color: #8f5902; font-style: italic }
.codehilite .gd { color: #a40000 }
.codehilite .ge { color: #000000; font-style: italic }
.codehilite .gr { color: #ef2929 }
.codehilite .gh { color: #000080; font-weight: bold }
.codehilite .gi { color: #00a000 }
.codehilite .go { color: #000000; font-style: italic }
.codehilite .gp { color: #8f5902 }
.codehilite .gs { color: #000000; font-weight: bold }
.codehilite .gu { color: #800080; font-weight: bold }
.codehilite .gt { color: #a40000; font-weight: bold }
.codehilite .kc { color: #204a87; font-weight: bold }
.codehilite .kd { color: #204a87; font-weight: bold }
.codehilite .kn { color: #204a87; font-weight: bold }
.codehilite .kp { color: #204a87; font-weight: bold }
.codehilite .kr { color: #204a87; font-weight: bold }
.codehilite .kt { color: #204a87; font-weight: bold }
.codehilite .ld { color: #000000 }
.codehilite .m { color: #0000cf; font-weight: bold }
.codehilite .s { color: #4e9a06 }
.codehilite .na { color: #c4a000 }
.codehilite .nb { color: #204a87 }
.codehilite .nc { color: #000000 }
.codehilite .no { color: #000000 }
.codehilite .nd { color: #5c35cc; font-weight: bold }
.codehilite .ni { color: #ce5c00 }
.codehilite .ne { color: #cc0000; font-weight: bold }
.codehilite .nf { color: #000000 }
.codehilite .nl { color: #f57900 }
.codehilite .nn { color: #000000 }
.codehilite .nx { color: #000000 }
.codehilite .py { color: #000000 }
.codehilite .nt { color: #204a87; font-weight: bold }
.codehilite .nv { color: #000000 }
.codehilite .ow { color: #204a87; font-weight: bold }
.codehilite .w { color: #f8f8f8; text-decoration: underline }
.codehilite .mf { color: #0000cf; font-weight: bold }
.codehilite .mh { color: #0000cf; font-weight: bold }
.codehilite .mi { color: #0000cf; font-weight: bold }
.codehilite .mo { color: #0000cf; font-weight: bold }
.codehilite .sb { color: #4e9a06 }
.codehilite .sc { color: #4e9a06 }
.codehilite .sd { color: #8f5902; font-style: italic }
.codehilite .s2 { color: #4e9a06 }
.codehilite .se { color: #4e9a06 }
.codehilite .sh { color: #4e9a06 }
.codehilite .si { color: #4e9a06 }
.codehilite .sx { color: #4e9a06 }
.codehilite .sr { color: #4e9a06 }
.codehilite .s1 { color: #4e9a06 }
.codehilite .ss { color: #4e9a06 }
.codehilite .bp { color: #3465a4 }
.codehilite .vc { color: #000000 }
.codehilite .vg { color: #000000 }
.codehilite .vi { color: #000000 }
.codehilite .il { color: #0000cf; font-weight: bold }
"""

# ── Themes ─────────────────────────────────────────────────────────────────────
THEMES = {
    "default": {
        "bg": "#ffffff",
        "text": "#1a1a2e",
        "heading": "#0f3460",
        "accent": "#e94560",
        "accent2": "#0f3460",
        "code_bg": "#f4f6f9",
        "code_text": "#24292f",
        "border": "#e2e8f0",
        "link": "#0f3460",
        "blockquote_bg": "#f0f4ff",
        "blockquote_border": "#0f3460",
        "table_header_bg": "#0f3460",
        "table_header_text": "#ffffff",
        "table_stripe": "#f8fafc",
        "page_margin": "2.5cm 3cm",
    },
    "dark": {
        "bg": "#0d1117",
        "text": "#e6edf3",
        "heading": "#58a6ff",
        "accent": "#f78166",
        "accent2": "#58a6ff",
        "code_bg": "#161b22",
        "code_text": "#e6edf3",
        "border": "#30363d",
        "link": "#58a6ff",
        "blockquote_bg": "#161b22",
        "blockquote_border": "#58a6ff",
        "table_header_bg": "#161b22",
        "table_header_text": "#58a6ff",
        "table_stripe": "#0d1117",
        "page_margin": "2.5cm 3cm",
    },
    "minimal": {
        "bg": "#fafafa",
        "text": "#333333",
        "heading": "#111111",
        "accent": "#666666",
        "accent2": "#111111",
        "code_bg": "#f0f0f0",
        "code_text": "#333333",
        "border": "#dddddd",
        "link": "#000000",
        "blockquote_bg": "#f5f5f5",
        "blockquote_border": "#cccccc",
        "table_header_bg": "#222222",
        "table_header_text": "#ffffff",
        "table_stripe": "#f5f5f5",
        "page_margin": "3cm 4cm",
    },
    "technical": {
        "bg": "#ffffff",
        "text": "#2d3748",
        "heading": "#1a365d",
        "accent": "#2b6cb0",
        "accent2": "#1a365d",
        "code_bg": "#edf2f7",
        "code_text": "#1a202c",
        "border": "#bee3f8",
        "link": "#2b6cb0",
        "blockquote_bg": "#ebf8ff",
        "blockquote_border": "#2b6cb0",
        "table_header_bg": "#2b6cb0",
        "table_header_text": "#ffffff",
        "table_stripe": "#f7fafc",
        "page_margin": "2cm 2.5cm",
    },
}


def get_css(theme: dict, font_size: int = 11) -> str:
    t = theme
    return f"""
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

@page {{
    size: A4;
    margin: {t['page_margin']};
    @top-center {{
        content: string(chapter-title);
        font-family: 'Inter', sans-serif;
        font-size: 8pt;
        color: {t['accent']};
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }}
    @bottom-center {{
        content: counter(page) " / " counter(pages);
        font-family: 'Inter', sans-serif;
        font-size: 8pt;
        color: {t['accent']};
    }}
    @bottom-left {{
        content: string(doc-title);
        font-family: 'Inter', sans-serif;
        font-size: 8pt;
        color: {t['border']};
    }}
}}

@page :first {{
    @top-center {{ content: none; }}
    @bottom-center {{ content: none; }}
    @bottom-left {{ content: none; }}
}}

html, body {{
    background: {t['bg']};
    color: {t['text']};
    font-family: 'Source Serif 4', Georgia, serif;
    font-size: {font_size}pt;
    line-height: 1.75;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}

/* ── Headings ── */
h1, h2, h3, h4, h5, h6 {{
    font-family: 'Inter', sans-serif;
    color: {t['heading']};
    line-height: 1.25;
    margin-top: 1.6em;
    margin-bottom: 0.5em;
    font-weight: 700;
    page-break-after: avoid;
}}

h1 {{
    string-set: doc-title content();
    font-size: 2em;
    border-bottom: 3px solid {t['accent']};
    padding-bottom: 0.3em;
    margin-top: 0;
}}

h2 {{
    string-set: chapter-title content();
    font-size: 1.5em;
    border-bottom: 1.5px solid {t['border']};
    padding-bottom: 0.2em;
}}

h3 {{ font-size: 1.2em; }}
h4 {{ font-size: 1.05em; font-weight: 600; }}
h5, h6 {{ font-size: 1em; font-weight: 600; color: {t['accent']}; }}

/* ── Paragraph & text ── */
p {{
    margin-bottom: 0.9em;
    orphans: 3;
    widows: 3;
}}

strong {{ font-weight: 700; color: {t['heading']}; }}
em {{ font-style: italic; }}

/* ── Links ── */
a {{ color: {t['link']}; text-decoration: underline; text-underline-offset: 2px; }}

/* ── Code ── */
code {{
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 0.85em;
    background: {t['code_bg']};
    color: {t['code_text']};
    padding: 0.15em 0.4em;
    border-radius: 3px;
    border: 1px solid {t['border']};
}}

pre {{
    background: {t['code_bg']};
    border: 1px solid {t['border']};
    border-left: 4px solid {t['accent']};
    border-radius: 4px;
    padding: 1em 1.2em;
    overflow-x: auto;
    margin: 1.2em 0;
    page-break-inside: avoid;
}}

pre code {{
    background: none;
    border: none;
    padding: 0;
    font-size: 0.82em;
    line-height: 1.6;
    color: {t['code_text']};
}}

.codehilite {{
    background: {t['code_bg']};
    border: 1px solid {t['border']};
    border-left: 4px solid {t['accent']};
    border-radius: 4px;
    padding: 1em 1.2em;
    margin: 1.2em 0;
    page-break-inside: avoid;
    overflow-x: auto;
}}

.codehilite pre {{
    background: none;
    border: none;
    padding: 0;
    margin: 0;
}}

/* ── Blockquote ── */
blockquote {{
    background: {t['blockquote_bg']};
    border-left: 4px solid {t['blockquote_border']};
    border-radius: 0 4px 4px 0;
    margin: 1.2em 0;
    padding: 0.8em 1.2em;
    color: {t['heading']};
    font-style: italic;
    page-break-inside: avoid;
}}

blockquote p {{ margin-bottom: 0; }}

/* ── Lists ── */
ul, ol {{
    padding-left: 1.8em;
    margin-bottom: 0.9em;
}}

li {{
    margin-bottom: 0.3em;
    line-height: 1.65;
}}

li > ul, li > ol {{
    margin-top: 0.3em;
    margin-bottom: 0.3em;
}}

/* ── Tables ── */
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1.4em 0;
    font-family: 'Inter', sans-serif;
    font-size: 0.9em;
    page-break-inside: avoid;
    border: 1px solid {t['border']};
    border-radius: 4px;
    overflow: hidden;
}}

thead tr {{
    background: {t['table_header_bg']};
    color: {t['table_header_text']};
}}

thead th {{
    padding: 0.7em 1em;
    text-align: left;
    font-weight: 600;
    letter-spacing: 0.03em;
    font-size: 0.85em;
    text-transform: uppercase;
    border: none;
}}

tbody tr:nth-child(even) {{ background: {t['table_stripe']}; }}
tbody tr:hover {{ background: {t['blockquote_bg']}; }}

td {{
    padding: 0.6em 1em;
    border-top: 1px solid {t['border']};
    vertical-align: top;
}}

/* ── Horizontal rule ── */
hr {{
    border: none;
    border-top: 2px solid {t['border']};
    margin: 2em 0;
}}

/* ── Images ── */
img {{
    max-width: 100%;
    height: auto;
    border-radius: 4px;
    display: block;
    margin: 1em auto;
}}

/* ── TOC ── */
.toc {{
    background: {t['blockquote_bg']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 1.2em 1.5em;
    margin: 1.5em 0 2em;
    page-break-inside: avoid;
}}

.toc::before {{
    content: "Contents";
    display: block;
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 0.85em;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {t['accent']};
    margin-bottom: 0.8em;
}}

.toc ul {{ list-style: none; padding-left: 0; margin: 0; }}
.toc li {{ margin: 0.25em 0; }}
.toc a {{
    color: {t['heading']};
    text-decoration: none;
    font-family: 'Inter', sans-serif;
    font-size: 0.9em;
}}

.toc ul ul {{ padding-left: 1.2em; }}
.toc ul ul a {{ color: {t['accent']}; font-size: 0.85em; }}

/* ── Admonition-like callouts (> [!NOTE] style) ── */
.admonition {{
    border-left: 4px solid {t['accent']};
    background: {t['blockquote_bg']};
    padding: 0.8em 1.2em;
    margin: 1.2em 0;
    border-radius: 0 4px 4px 0;
}}

/* ── Definition lists ── */
dt {{ font-weight: 700; color: {t['heading']}; margin-top: 0.6em; }}
dd {{ margin-left: 1.5em; margin-bottom: 0.4em; }}

/* ── Footnotes ── */
.footnote {{ font-size: 0.85em; border-top: 1px solid {t['border']}; margin-top: 2em; padding-top: 0.8em; }}

/* ── Cover page helper ── */
.cover {{ text-align: center; padding: 4em 2em; page-break-after: always; }}
.cover h1 {{ border-bottom: none; font-size: 3em; margin-bottom: 0.3em; }}
.cover .subtitle {{ font-size: 1.2em; color: {t['accent']}; font-family: 'Inter'; }}

{PYGMENTS_CSS}
"""


def md_to_html(md_text: str, toc_enabled: bool = True) -> str:
    extensions = [
        "markdown.extensions.tables",
        "markdown.extensions.fenced_code",
        "markdown.extensions.codehilite",
        "markdown.extensions.attr_list",
        "markdown.extensions.def_list",
        "markdown.extensions.footnotes",
        "markdown.extensions.abbr",
        "markdown.extensions.meta",
        "markdown.extensions.nl2br",
        "markdown.extensions.sane_lists",
        "markdown.extensions.smarty",
    ]
    ext_configs = {
        "markdown.extensions.codehilite": {
            "css_class": "codehilite",
            "guess_lang": True,
            "linenums": False,
        },
    }
    if toc_enabled:
        extensions.append("markdown.extensions.toc")
        ext_configs["markdown.extensions.toc"] = {
            "title": "",
            "toc_depth": 3,
        }

    md = markdown.Markdown(extensions=extensions, extension_configs=ext_configs)
    return md.convert(md_text)


def build_full_html(body_html: str, css: str, title: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{body_html}
</body>
</html>"""


def convert(
    input_path: str,
    output_path: str | None = None,
    theme_name: str = "default",
    toc: bool = True,
    font_size: int = 11,
) -> str:
    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        output_path = str(src.with_suffix(".pdf"))

    md_text = src.read_text(encoding="utf-8")

    # Extract title from first H1 if present
    title_match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    title = title_match.group(1) if title_match else src.stem

    theme = THEMES.get(theme_name, THEMES["default"])
    css = get_css(theme, font_size)
    body_html = md_to_html(md_text, toc_enabled=toc)
    full_html = build_full_html(body_html, css, title)

    font_config = FontConfiguration()
    html_obj = HTML(string=full_html, base_url=str(src.parent))
    css_obj = CSS(string="", font_config=font_config)
    html_obj.write_pdf(output_path, font_config=font_config)

    return output_path


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Convert Markdown to professional PDF documentation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python md_to_pdf.py README.md
  python md_to_pdf.py docs/guide.md output/guide.pdf --theme technical
  python md_to_pdf.py report.md --theme dark --no-toc --font-size 12

Themes: default, dark, minimal, technical
        """,
    )
    parser.add_argument("input", help="Input Markdown file")
    parser.add_argument("output", nargs="?", help="Output PDF file (optional)")
    parser.add_argument(
        "--theme",
        choices=THEMES.keys(),
        default="default",
        help="Color theme (default: default)",
    )
    parser.add_argument(
        "--no-toc", action="store_true", help="Disable table of contents"
    )
    parser.add_argument(
        "--font-size", type=int, default=11, help="Base font size in pt (default: 11)"
    )

    args = parser.parse_args()

    print(f"  Converting: {args.input}")
    print(f"  Theme:      {args.theme}")
    print(f"  TOC:        {'off' if args.no_toc else 'on'}")

    try:
        out = convert(
            args.input,
            args.output,
            theme_name=args.theme,
            toc=not args.no_toc,
            font_size=args.font_size,
        )
        print(f"  Output:     {out}")
        print("  Done!")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
