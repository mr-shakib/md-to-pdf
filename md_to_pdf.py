#!/usr/bin/env python3
"""
md_to_pdf.py — Convert Markdown to a professional, print-ready PDF.

Usage:
    python md_to_pdf.py input.md [output.pdf] [--theme THEME] [--no-toc] [--font-size N]

Themes: default | dark | minimal | technical
"""

import argparse
import os
import re
import sys
from pathlib import Path

import markdown
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration

# ─────────────────────────────────────────────────────────────────────────────
# Syntax-highlighting token colours (zero background anywhere)
# ─────────────────────────────────────────────────────────────────────────────
PYGMENTS_CSS = """
.codehilite .c,.codehilite .cm,.codehilite .c1,.codehilite .cs{color:#6a737d;font-style:italic}
.codehilite .cp{color:#6a737d;font-weight:bold}
.codehilite .k,.codehilite .kd,.codehilite .kn,.codehilite .kp,.codehilite .kr,.codehilite .kt{color:#d73a49;font-weight:bold}
.codehilite .o,.codehilite .ow{color:#d73a49}
.codehilite .s,.codehilite .s1,.codehilite .s2,.codehilite .sb,.codehilite .sc,.codehilite .se,.codehilite .sh,.codehilite .si,.codehilite .sx,.codehilite .sr,.codehilite .ss{color:#032f62}
.codehilite .sd{color:#032f62;font-style:italic}
.codehilite .m,.codehilite .mf,.codehilite .mh,.codehilite .mi,.codehilite .mo,.codehilite .il{color:#005cc5;font-weight:bold}
.codehilite .na{color:#6f42c1}
.codehilite .nb{color:#005cc5}
.codehilite .nc,.codehilite .nd{color:#6f42c1;font-weight:bold}
.codehilite .nf{color:#6f42c1}
.codehilite .nt{color:#22863a;font-weight:bold}
.codehilite .nv,.codehilite .vc,.codehilite .vg,.codehilite .vi{color:#e36209}
.codehilite .ne{color:#d73a49;font-weight:bold}
.codehilite .gd{color:#b31d28}
.codehilite .gi{color:#22863a}
.codehilite .err{color:#d73a49}
.codehilite .p,.codehilite .n,.codehilite .nx{color:#24292e}
"""

THEMES = {
    "default": {
        "margin":       "2.2cm 2.4cm 2.4cm 2.4cm",
        "color":        "#1a1a2e",
        "font_body":    "Georgia, 'Times New Roman', serif",
        "font_head":    "Arial, 'Helvetica Neue', sans-serif",
        "font_mono":    "'Courier New', Courier, monospace",
        "h_color":      "#0f3460",
        "h1_border":    "2.5pt solid #0f3460",
        "h2_border":    "0.75pt solid #c8d0dc",
        "accent":       "#0f3460",
        "code_border":  "0.75pt solid #d1d5db",
        "code_bar":     "3pt solid #0f3460",
        "code_color":   "#24292e",
        "ic_border":    "0.5pt solid #d1d5db",
        "bq_bar":       "3pt solid #0f3460",
        "bq_color":     "#555566",
        "th_bg":        "#0f3460",
        "th_color":     "#ffffff",
        "td_border":    "0.75pt solid #d1d5db",
        "tr_stripe":    "#f6f8fa",
        "hr":           "0.75pt solid #c8d0dc",
        "link_color":   "#0f3460",
        "footer_color": "#8888aa",
    },
    "dark": {
        "margin":       "2.2cm 2.4cm 2.4cm 2.4cm",
        "color":        "#e6edf3",
        "font_body":    "Georgia, serif",
        "font_head":    "Arial, sans-serif",
        "font_mono":    "'Courier New', Courier, monospace",
        "h_color":      "#79c0ff",
        "h1_border":    "2.5pt solid #388bfd",
        "h2_border":    "0.75pt solid #30363d",
        "accent":       "#388bfd",
        "code_border":  "0.75pt solid #30363d",
        "code_bar":     "3pt solid #388bfd",
        "code_color":   "#e6edf3",
        "ic_border":    "0.5pt solid #30363d",
        "bq_bar":       "3pt solid #388bfd",
        "bq_color":     "#adbac7",
        "th_bg":        "#21262d",
        "th_color":     "#79c0ff",
        "td_border":    "0.75pt solid #30363d",
        "tr_stripe":    "#161b22",
        "hr":           "0.75pt solid #30363d",
        "link_color":   "#79c0ff",
        "footer_color": "#6e7681",
    },
    "minimal": {
        "margin":       "2.5cm 2.8cm 2.5cm 2.8cm",
        "color":        "#222222",
        "font_body":    "Georgia, 'Times New Roman', serif",
        "font_head":    "Georgia, 'Times New Roman', serif",
        "font_mono":    "'Courier New', Courier, monospace",
        "h_color":      "#111111",
        "h1_border":    "1.5pt solid #111111",
        "h2_border":    "0.5pt solid #dddddd",
        "accent":       "#444444",
        "code_border":  "0.75pt solid #e0e0e0",
        "code_bar":     "3pt solid #888888",
        "code_color":   "#333333",
        "ic_border":    "0.5pt solid #e0e0e0",
        "bq_bar":       "3pt solid #999999",
        "bq_color":     "#555555",
        "th_bg":        "#111111",
        "th_color":     "#ffffff",
        "td_border":    "0.75pt solid #dddddd",
        "tr_stripe":    "#f9f9f9",
        "hr":           "0.75pt solid #dddddd",
        "link_color":   "#222222",
        "footer_color": "#aaaaaa",
    },
    "technical": {
        "margin":       "1.8cm 2.0cm 2.2cm 2.0cm",
        "color":        "#1e293b",
        "font_body":    "Arial, 'Helvetica Neue', sans-serif",
        "font_head":    "Arial, 'Helvetica Neue', sans-serif",
        "font_mono":    "'Courier New', Courier, monospace",
        "h_color":      "#0f172a",
        "h1_border":    "2pt solid #2563eb",
        "h2_border":    "0.75pt solid #cbd5e1",
        "accent":       "#2563eb",
        "code_border":  "0.75pt solid #cbd5e1",
        "code_bar":     "3pt solid #2563eb",
        "code_color":   "#1e293b",
        "ic_border":    "0.5pt solid #cbd5e1",
        "bq_bar":       "3pt solid #2563eb",
        "bq_color":     "#475569",
        "th_bg":        "#0f172a",
        "th_color":     "#f8fafc",
        "td_border":    "0.75pt solid #cbd5e1",
        "tr_stripe":    "#f8fafc",
        "hr":           "0.75pt solid #cbd5e1",
        "link_color":   "#2563eb",
        "footer_color": "#94a3b8",
    },
}


def get_css(t: dict, font_size: int = 11) -> str:
    return f"""
@page {{
    size: A4;
    margin: {t['margin']};
    @top-left {{
        content: string(doc-title);
        font-family: {t['font_head']};
        font-size: 7.5pt;
        color: {t['footer_color']};
        vertical-align: bottom;
        padding-bottom: 4pt;
    }}
    @top-right {{
        content: string(section-title);
        font-family: {t['font_head']};
        font-size: 7.5pt;
        color: {t['accent']};
        vertical-align: bottom;
        padding-bottom: 4pt;
    }}
    @bottom-center {{
        content: counter(page) " / " counter(pages);
        font-family: {t['font_head']};
        font-size: 7.5pt;
        color: {t['footer_color']};
        vertical-align: top;
        padding-top: 4pt;
    }}
}}
@page :first {{
    @top-left      {{ content: none; }}
    @top-right     {{ content: none; }}
    @bottom-center {{ content: none; }}
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html, body {{
    color: {t['color']};
    font-family: {t['font_body']};
    font-size: {font_size}pt;
    line-height: 1.8;
    width: 100%;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}

h1, h2, h3, h4, h5, h6 {{
    font-family: {t['font_head']};
    color: {t['h_color']};
    line-height: 1.3;
    font-weight: 700;
    page-break-after: avoid;
    margin-top: 1.8em;
    margin-bottom: 0.5em;
}}
h1 {{
    string-set: doc-title content();
    font-size: 2em;
    border-bottom: {t['h1_border']};
    padding-bottom: 0.25em;
    margin-top: 0;
}}
h2 {{
    string-set: section-title content();
    font-size: 1.45em;
    border-bottom: {t['h2_border']};
    padding-bottom: 0.2em;
}}
h3 {{ font-size: 1.2em; }}
h4 {{ font-size: 1.05em; }}
h5 {{ font-size: 1em; color: {t['accent']}; }}
h6 {{ font-size: 0.95em; color: {t['accent']}; font-style: italic; }}

p {{
    margin-bottom: 0.85em;
    text-align: justify;
    hyphens: auto;
    orphans: 3;
    widows: 3;
}}

a {{
    color: {t['link_color']};
    text-decoration: none;
    border-bottom: 0.5pt solid {t['link_color']};
}}
strong {{ font-weight: 700; }}
em     {{ font-style: italic; }}

/* inline code — border only, no fill */
code {{
    font-family: {t['font_mono']};
    font-size: 0.84em;
    color: {t['code_color']};
    border: {t['ic_border']};
    padding: 0.1em 0.35em;
    border-radius: 2pt;
}}

/* fenced blocks — left bar + thin border, NO fill */
pre {{
    font-family: {t['font_mono']};
    font-size: 0.82em;
    line-height: 1.55;
    color: {t['code_color']};
    border: {t['code_border']};
    border-left: {t['code_bar']};
    padding: 0.85em 1em;
    margin: 1.1em 0;
    page-break-inside: avoid;
    white-space: pre-wrap;
    word-wrap: break-word;
}}
pre code {{
    border: none;
    padding: 0;
    font-size: inherit;
    color: inherit;
}}

/* Pygments wrapper — same as pre, NO fill */
.codehilite {{
    border: {t['code_border']};
    border-left: {t['code_bar']};
    padding: 0.85em 1em;
    margin: 1.1em 0;
    page-break-inside: avoid;
}}
.codehilite pre {{
    border: none;
    padding: 0;
    margin: 0;
    font-family: {t['font_mono']};
    font-size: 0.82em;
    line-height: 1.55;
    color: {t['code_color']};
    white-space: pre-wrap;
    word-wrap: break-word;
}}

blockquote {{
    border-left: {t['bq_bar']};
    margin: 1.2em 0;
    padding: 0.1em 0 0.1em 1em;
    color: {t['bq_color']};
    font-style: italic;
    page-break-inside: avoid;
}}
blockquote p {{ margin-bottom: 0.3em; text-align: left; }}
blockquote p:last-child {{ margin-bottom: 0; }}

ul, ol {{ padding-left: 1.6em; margin-bottom: 0.85em; }}
li {{ margin-bottom: 0.25em; line-height: 1.7; }}
li > ul, li > ol {{ margin-top: 0.2em; margin-bottom: 0.2em; }}

table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1.3em 0;
    font-family: {t['font_head']};
    font-size: 0.88em;
    page-break-inside: avoid;
}}
thead tr {{
    background: {t['th_bg']};
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}
thead th {{
    color: {t['th_color']};
    padding: 0.55em 0.85em;
    text-align: left;
    font-weight: 600;
    font-size: 0.82em;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    border: {t['td_border']};
}}
tbody tr:nth-child(even) {{
    background: {t['tr_stripe']};
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}
td {{
    padding: 0.5em 0.85em;
    border: {t['td_border']};
    vertical-align: top;
}}

hr {{ border: none; border-top: {t['hr']}; margin: 1.8em 0; }}

img {{ max-width: 100%; height: auto; display: block; margin: 1em 0; }}

/* TOC — left bar only, no fill */
.toc {{
    border: {t['code_border']};
    border-left: {t['code_bar']};
    padding: 1em 1.3em;
    margin: 1.4em 0 2em;
    page-break-inside: avoid;
}}
.toc::before {{
    content: "Table of Contents";
    display: block;
    font-family: {t['font_head']};
    font-weight: 700;
    font-size: 0.8em;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {t['accent']};
    margin-bottom: 0.7em;
    border-bottom: {t['h2_border']};
    padding-bottom: 0.4em;
}}
.toc ul {{ list-style: none; padding-left: 0; margin: 0; }}
.toc li {{ margin: 0.2em 0; line-height: 1.5; }}
.toc a  {{ color: {t['link_color']}; text-decoration: none; border-bottom: none;
           font-family: {t['font_head']}; font-size: 0.88em; }}
.toc ul ul   {{ padding-left: 1.2em; margin-top: 0.15em; }}
.toc ul ul a {{ font-size: 0.84em; color: {t['bq_color']}; }}

dt {{ font-weight: 700; color: {t['h_color']}; margin-top: 0.6em; }}
dd {{ margin-left: 1.4em; margin-bottom: 0.35em; }}

.footnote {{
    font-size: 0.82em;
    border-top: {t['hr']};
    margin-top: 2em;
    padding-top: 0.7em;
    color: {t['footer_color']};
}}

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
        "markdown.extensions.sane_lists",
        "markdown.extensions.smarty",
    ]
    ext_cfg: dict = {
        "markdown.extensions.codehilite": {
            "css_class": "codehilite",
            "guess_lang": True,
            "linenums": False,
            "noclasses": False,
        },
    }
    if toc_enabled:
        extensions.append("markdown.extensions.toc")
        ext_cfg["markdown.extensions.toc"] = {"toc_depth": "2-4", "title": ""}

    md = markdown.Markdown(extensions=extensions, extension_configs=ext_cfg)
    return md.convert(md_text)


def build_html(body: str, css: str, title: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{body}
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

    output_path = output_path or str(src.with_suffix(".pdf"))
    md_text = src.read_text(encoding="utf-8")

    m = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    title = m.group(1) if m else src.stem

    theme = THEMES.get(theme_name, THEMES["default"])
    css   = get_css(theme, font_size)
    body  = md_to_html(md_text, toc_enabled=toc)
    html  = build_html(body, css, title)

    font_config = FontConfiguration()
    HTML(string=html, base_url=str(src.parent)).write_pdf(
        output_path, font_config=font_config
    )
    return output_path


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Convert Markdown to professional PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("input")
    ap.add_argument("output", nargs="?")
    ap.add_argument("--theme", choices=THEMES.keys(), default="default")
    ap.add_argument("--no-toc", action="store_true")
    ap.add_argument("--font-size", type=int, default=11)
    args = ap.parse_args()

    print(f"  input  : {args.input}")
    print(f"  theme  : {args.theme}")
    print(f"  toc    : {'off' if args.no_toc else 'on'}")

    try:
        out = convert(
            args.input, args.output,
            theme_name=args.theme,
            toc=not args.no_toc,
            font_size=args.font_size,
        )
        print(f"  output : {out}")
        print("  done!")
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
