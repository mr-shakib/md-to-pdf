"""
app.py — MD→PDF converter with live split-pane editor + preview.
"""

import base64
import os
import re
import sys
import tempfile
import uuid
from pathlib import Path

import markdown
from flask import Flask, jsonify, render_template_string, request, send_file

sys.path.insert(0, os.path.dirname(__file__))
from md_to_pdf import convert, THEMES, get_css, md_to_html

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

FILE_STORE: dict[str, dict] = {}

# ── Shared preview CSS (clean white, full-width, same rules as PDF) ────────────
def get_preview_html(md_text: str, theme_name: str = "default") -> str:
    theme = THEMES.get(theme_name, THEMES["default"])
    t = theme
    body = md_to_html(md_text, toc_enabled=True)

    # Build a standalone HTML page that looks like the PDF page
    css = f"""
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ background: #e8e8e8; }}
    body {{
        background: white;
        color: {t['color']};
        font-family: {t['font_body']};
        font-size: 11pt;
        line-height: 1.8;
        max-width: 210mm;
        margin: 0 auto;
        padding: 2.2cm 2.4cm 2.4cm 2.4cm;
        min-height: 297mm;
        box-shadow: 0 2px 24px rgba(0,0,0,0.18);
    }}
    h1,h2,h3,h4,h5,h6 {{
        font-family: {t['font_head']};
        color: {t['h_color']};
        line-height: 1.3;
        font-weight: 700;
        margin-top: 1.8em;
        margin-bottom: 0.5em;
    }}
    h1 {{
        font-size: 2em;
        border-bottom: {t['h1_border']};
        padding-bottom: 0.25em;
        margin-top: 0;
    }}
    h2 {{
        font-size: 1.45em;
        border-bottom: {t['h2_border']};
        padding-bottom: 0.2em;
    }}
    h3  {{ font-size: 1.2em; }}
    h4  {{ font-size: 1.05em; }}
    h5  {{ font-size: 1em;  color: {t['accent']}; }}
    h6  {{ font-size: .95em; color: {t['accent']}; font-style: italic; }}
    p   {{ margin-bottom: .85em; text-align: justify; hyphens: auto; }}
    a   {{ color: {t['link_color']}; text-decoration: none; border-bottom: 0.5pt solid {t['link_color']}; }}
    strong {{ font-weight: 700; }}
    em     {{ font-style: italic; }}

    code {{
        font-family: {t['font_mono']};
        font-size: .85em;
        color: {t['code_color']};
        border: {t['ic_border']};
        padding: .1em .35em;
        border-radius: 2pt;
    }}
    pre {{
        font-family: {t['font_mono']};
        font-size: .82em;
        line-height: 1.55;
        color: {t['code_color']};
        border: {t['code_border']};
        border-left: {t['code_bar']};
        padding: .85em 1em;
        margin: 1.1em 0;
        white-space: pre-wrap;
        word-wrap: break-word;
    }}
    pre code {{ border:none; padding:0; font-size:inherit; color:inherit; }}
    .codehilite {{
        border: {t['code_border']};
        border-left: {t['code_bar']};
        padding: .85em 1em;
        margin: 1.1em 0;
    }}
    .codehilite pre {{ border:none; padding:0; margin:0; font-family:{t['font_mono']}; font-size:.82em; line-height:1.55; color:{t['code_color']}; white-space:pre-wrap; word-wrap:break-word; }}
    blockquote {{
        border-left: {t['bq_bar']};
        margin: 1.2em 0;
        padding: .1em 0 .1em 1em;
        color: {t['bq_color']};
        font-style: italic;
    }}
    blockquote p {{ margin-bottom:.3em; text-align:left; }}
    ul,ol {{ padding-left:1.6em; margin-bottom:.85em; }}
    li {{ margin-bottom:.25em; line-height:1.7; }}
    table {{ width:100%; border-collapse:collapse; margin:1.3em 0; font-family:{t['font_head']}; font-size:.88em; }}
    thead tr {{ background:{t['th_bg']}; }}
    thead th {{ color:{t['th_color']}; padding:.55em .85em; text-align:left; font-weight:600; font-size:.82em; letter-spacing:.04em; text-transform:uppercase; border:{t['td_border']}; }}
    tbody tr:nth-child(even) {{ background:{t['tr_stripe']}; }}
    td {{ padding:.5em .85em; border:{t['td_border']}; vertical-align:top; }}
    hr {{ border:none; border-top:{t['hr']}; margin:1.8em 0; }}
    img {{ max-width:100%; height:auto; display:block; margin:1em 0; }}
    .toc {{ border:{t['code_border']}; border-left:{t['code_bar']}; padding:1em 1.3em; margin:1.4em 0 2em; }}
    .toc::before {{ content:"Table of Contents"; display:block; font-family:{t['font_head']}; font-weight:700; font-size:.8em; letter-spacing:.08em; text-transform:uppercase; color:{t['accent']}; margin-bottom:.7em; border-bottom:{t['h2_border']}; padding-bottom:.4em; }}
    .toc ul {{ list-style:none; padding-left:0; margin:0; }}
    .toc li {{ margin:.2em 0; line-height:1.5; }}
    .toc a  {{ color:{t['link_color']}; text-decoration:none; border-bottom:none; font-family:{t['font_head']}; font-size:.88em; }}
    .toc ul ul {{ padding-left:1.2em; }}
    .toc ul ul a {{ font-size:.84em; color:{t['bq_color']}; }}
    dt {{ font-weight:700; color:{t['h_color']}; margin-top:.6em; }}
    dd {{ margin-left:1.4em; margin-bottom:.35em; }}
    .footnote {{ font-size:.82em; border-top:{t['hr']}; margin-top:2em; padding-top:.7em; color:{t['footer_color']}; }}

    /* Pygments colours */
    .codehilite .c,.codehilite .cm,.codehilite .c1,.codehilite .cs{{color:#6a737d;font-style:italic}}
    .codehilite .cp{{color:#6a737d;font-weight:bold}}
    .codehilite .k,.codehilite .kd,.codehilite .kn,.codehilite .kp,.codehilite .kr,.codehilite .kt{{color:#d73a49;font-weight:bold}}
    .codehilite .o,.codehilite .ow{{color:#d73a49}}
    .codehilite .s,.codehilite .s1,.codehilite .s2,.codehilite .sb,.codehilite .sc,.codehilite .se,.codehilite .sh,.codehilite .si,.codehilite .sx,.codehilite .sr,.codehilite .ss{{color:#032f62}}
    .codehilite .m,.codehilite .mf,.codehilite .mh,.codehilite .mi,.codehilite .mo,.codehilite .il{{color:#005cc5;font-weight:bold}}
    .codehilite .na{{color:#6f42c1}}
    .codehilite .nb{{color:#005cc5}}
    .codehilite .nc,.codehilite .nd{{color:#6f42c1;font-weight:bold}}
    .codehilite .nf{{color:#6f42c1}}
    .codehilite .nt{{color:#22863a;font-weight:bold}}
    .codehilite .nv,.codehilite .vc,.codehilite .vg,.codehilite .vi{{color:#e36209}}
    .codehilite .ne{{color:#d73a49;font-weight:bold}}
    .codehilite .gd{{color:#b31d28}}
    .codehilite .gi{{color:#22863a}}
    .codehilite .err{{color:#d73a49}}
    .codehilite .p,.codehilite .n,.codehilite .nx{{color:#24292e}}
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>{css}</style>
</head>
<body>{body}</body>
</html>"""


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(MAIN_PAGE)


@app.route("/preview", methods=["POST"])
def preview():
    """Return styled HTML for the live preview iframe."""
    data = request.get_json(silent=True) or {}
    md_text   = data.get("content", "")
    theme     = data.get("theme", "default")
    if theme not in THEMES:
        theme = "default"
    html = get_preview_html(md_text, theme)
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/convert", methods=["POST"])
def convert_endpoint():
    """Convert markdown text or uploaded file → PDF, return download token."""
    # Support both JSON body (from editor) and multipart (from file upload)
    if request.is_json:
        data      = request.get_json()
        md_text   = data.get("content", "")
        theme     = data.get("theme", "default")
        toc       = bool(data.get("toc", True))
        font_size = int(data.get("font_size", 11))
        filename  = data.get("filename", "document") + ".md"
    else:
        f = request.files.get("file")
        if not f:
            return jsonify({"error": "No content provided."}), 400
        filename  = f.filename or "document.md"
        md_text   = f.read().decode("utf-8", errors="replace")
        theme     = request.form.get("theme", "default")
        toc       = request.form.get("toc", "1") == "1"
        try:
            font_size = int(request.form.get("font_size", 11))
        except ValueError:
            font_size = 11

    if theme not in THEMES:
        theme = "default"
    font_size = max(8, min(16, font_size))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode="w", encoding="utf-8") as tmp_in:
        tmp_in.write(md_text)
        tmp_in_path = tmp_in.name

    tmp_out = tmp_in_path.replace(".md", ".pdf")

    try:
        convert(
            input_path=tmp_in_path,
            output_path=tmp_out,
            theme_name=theme,
            toc=toc,
            font_size=font_size,
        )
    except Exception as e:
        return jsonify({"error": f"Conversion failed: {str(e)}"}), 500
    finally:
        try: os.unlink(tmp_in_path)
        except: pass

    pdf_bytes = Path(tmp_out).read_bytes()
    try: os.unlink(tmp_out)
    except: pass

    token = uuid.uuid4().hex
    out_filename = Path(filename).stem + ".pdf"
    FILE_STORE[token] = {"bytes": pdf_bytes, "filename": out_filename}

    return jsonify({
        "token":    token,
        "filename": out_filename,
        "size_kb":  round(len(pdf_bytes) / 1024, 1),
        "pages":    max(1, len(pdf_bytes) // 3000),
    })


@app.route("/download/<token>")
def download(token):
    entry = FILE_STORE.pop(token, None)
    if not entry:
        return "File not found or already downloaded.", 404
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(entry["bytes"])
        tmp_path = tmp.name
    return send_file(tmp_path, as_attachment=True,
                     download_name=entry["filename"],
                     mimetype="application/pdf")


# ── Main HTML page ─────────────────────────────────────────────────────────────
MAIN_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MD → PDF · Live Editor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:       #0d0d14;
  --panel:    #12121c;
  --toolbar:  #16161f;
  --border:   #252535;
  --accent:   #6c63ff;
  --accent2:  #a78bfa;
  --text:     #e0e0f0;
  --dim:      #7777aa;
  --success:  #34d399;
  --error:    #f87171;
  --font-ui:  'Inter', sans-serif;
  --font-mono:'JetBrains Mono', monospace;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  height: 100%; overflow: hidden;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-ui);
  font-size: 14px;
}

/* ── Top bar ── */
#topbar {
  height: 52px;
  background: var(--toolbar);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 12px;
  flex-shrink: 0;
  z-index: 10;
}

.logo {
  display: flex; align-items: center; gap: 8px;
  font-weight: 700; font-size: 15px; letter-spacing: -.02em;
  flex-shrink: 0;
}
.logo-box {
  width: 28px; height: 28px; border-radius: 7px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
}

.sep { width: 1px; height: 28px; background: var(--border); flex-shrink: 0; }

/* theme pills */
#theme-row { display: flex; gap: 6px; align-items: center; }
.theme-btn {
  padding: 4px 11px; border-radius: 99px; font-size: 12px; font-weight: 500;
  border: 1px solid var(--border); background: none; color: var(--dim);
  cursor: pointer; transition: all .15s; font-family: var(--font-ui);
}
.theme-btn:hover  { border-color: var(--accent2); color: var(--accent2); }
.theme-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }

/* toc + font-size */
#toc-toggle {
  display: flex; align-items: center; gap: 7px;
  font-size: 12px; color: var(--dim); cursor: pointer; user-select: none;
  flex-shrink: 0;
}
.pill-switch {
  width: 36px; height: 20px; background: var(--border);
  border-radius: 99px; position: relative; transition: background .2s;
}
.pill-switch::after {
  content:''; width:14px; height:14px; background:#fff; border-radius:50%;
  position:absolute; top:3px; left:3px; transition: transform .2s;
}
.pill-switch.on { background: var(--accent); }
.pill-switch.on::after { transform: translateX(16px); }

#font-size-wrap {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--dim); flex-shrink: 0;
}
#font-size-wrap input {
  width: 44px; padding: 3px 7px; border-radius: 6px;
  border: 1px solid var(--border); background: var(--panel);
  color: var(--text); font-family: var(--font-ui); font-size: 12px;
  outline: none;
}
#font-size-wrap input:focus { border-color: var(--accent); }

.spacer { flex: 1; }

/* upload / download buttons */
.btn {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 600;
  border: none; cursor: pointer; font-family: var(--font-ui); transition: opacity .15s;
  flex-shrink: 0;
}
.btn:hover { opacity: .85; }
.btn:disabled { opacity: .45; cursor: not-allowed; }
.btn-ghost {
  background: none; border: 1px solid var(--border); color: var(--dim);
}
.btn-ghost:hover { border-color: var(--accent2); color: var(--accent2); }
.btn-primary { background: linear-gradient(135deg, var(--accent), #7c3aed); color: #fff; }
.btn-success { background: var(--success); color: #0a2a1e; }

/* status pill */
#status {
  font-size: 11px; padding: 3px 10px; border-radius: 99px;
  background: rgba(108,99,255,.12); color: var(--accent2);
  border: 1px solid rgba(108,99,255,.25);
  transition: all .3s; flex-shrink: 0;
}
#status.ok  { background: rgba(52,211,153,.1); color: var(--success); border-color: rgba(52,211,153,.3); }
#status.err { background: rgba(248,113,113,.1); color: var(--error);  border-color: rgba(248,113,113,.3); }

/* ── Layout ── */
#workspace {
  display: flex;
  height: calc(100vh - 52px);
  overflow: hidden;
}

/* ── Editor pane ── */
#editor-pane {
  display: flex; flex-direction: column;
  width: 50%; min-width: 280px;
  border-right: 1px solid var(--border);
  flex-shrink: 0;
}

#editor-header {
  height: 36px; background: var(--toolbar);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 14px;
  gap: 8px; flex-shrink: 0;
}
#editor-header span { font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--dim); }

#editor-header .file-name {
  font-family: var(--font-mono); font-size: 11px; color: var(--accent2);
  background: rgba(108,99,255,.1); padding: 2px 8px; border-radius: 4px;
}

#editor {
  flex: 1; width: 100%;
  background: var(--panel);
  color: #c9d1d9;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.7;
  padding: 20px 22px;
  border: none; outline: none; resize: none;
  tab-size: 2;
  overflow-y: auto;
}
#editor::placeholder { color: var(--dim); }

/* editor footer */
#editor-footer {
  height: 28px; background: var(--toolbar);
  border-top: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 14px;
  gap: 12px; flex-shrink: 0;
}
#editor-footer span { font-size: 11px; color: var(--dim); }
#char-count { font-family: var(--font-mono); font-size: 11px; color: var(--dim); }

/* ── Divider ── */
#divider {
  width: 5px; background: var(--border); cursor: col-resize; flex-shrink: 0;
  transition: background .15s;
}
#divider:hover, #divider.dragging { background: var(--accent); }

/* ── Preview pane ── */
#preview-pane {
  display: flex; flex-direction: column;
  flex: 1; min-width: 200px; overflow: hidden;
}

#preview-header {
  height: 36px; background: var(--toolbar);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 14px;
  gap: 8px; flex-shrink: 0;
}
#preview-header span { font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--dim); }

.live-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--success);
  animation: pulse 2s ease infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

#preview-scroll {
  flex: 1; overflow-y: auto;
  background: #e0e0e0;
  padding: 24px 20px;
}

#preview-frame {
  width: 100%; height: 100%;
  border: none;
  /* actual size is set by JS to fill the scroll container */
}

/* Spinner overlay on preview */
#preview-spinner {
  display: none;
  position: absolute; inset: 36px 0 0 0;
  background: rgba(13,13,20,.6);
  align-items: center; justify-content: center;
  z-index: 5;
}
#preview-pane { position: relative; }
#preview-spinner.visible { display: flex; }
.spin { width:32px;height:32px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite; }
@keyframes spin { to{transform:rotate(360deg)} }

/* ── Toast ── */
#toast {
  position: fixed; bottom: 24px; right: 24px;
  padding: 10px 18px; border-radius: 10px;
  font-size: 13px; font-weight: 500;
  background: var(--panel); border: 1px solid var(--border);
  box-shadow: 0 8px 32px rgba(0,0,0,.4);
  opacity: 0; transform: translateY(8px);
  transition: all .25s; pointer-events: none; z-index: 999;
}
#toast.show { opacity: 1; transform: translateY(0); }
#toast.success { border-color: rgba(52,211,153,.4); color: var(--success); }
#toast.error   { border-color: rgba(248,113,113,.4); color: var(--error); }

/* hidden file input */
#file-input { display: none; }

/* scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3a3a55; }
</style>
</head>
<body>

<!-- ── Top Bar ── -->
<div id="topbar">
  <div class="logo">
    <div class="logo-box">📄</div>
    MD → PDF
  </div>

  <div class="sep"></div>

  <!-- Theme -->
  <div id="theme-row">
    <button class="theme-btn active" data-theme="default">Default</button>
    <button class="theme-btn"        data-theme="dark">Dark</button>
    <button class="theme-btn"        data-theme="minimal">Minimal</button>
    <button class="theme-btn"        data-theme="technical">Technical</button>
  </div>

  <div class="sep"></div>

  <!-- TOC -->
  <label id="toc-toggle" title="Toggle Table of Contents">
    <div class="pill-switch on" id="toc-switch"></div>
    TOC
  </label>

  <!-- Font size -->
  <div id="font-size-wrap">
    Font <input type="number" id="font-size" value="11" min="8" max="16"> pt
  </div>

  <div class="spacer"></div>

  <!-- Status -->
  <span id="status">ready</span>

  <!-- Actions -->
  <label class="btn btn-ghost" title="Upload a .md file">
    📂 Upload
    <input type="file" id="file-input" accept=".md,.markdown,.txt">
  </label>

  <button class="btn btn-primary" id="btn-convert">⚡ Generate PDF</button>
  <button class="btn btn-success" id="btn-download" disabled>⬇ Download</button>
</div>

<!-- ── Workspace ── -->
<div id="workspace">

  <!-- Editor -->
  <div id="editor-pane">
    <div id="editor-header">
      <span>Editor</span>
      <span class="file-name" id="file-name-label">untitled.md</span>
      <span style="flex:1"></span>
      <span id="char-count">0 chars</span>
    </div>
    <textarea id="editor" spellcheck="false" placeholder="# Hello World

Start typing or paste your Markdown here…

## Features
- **Bold**, *italic*, `code`
- Tables, code blocks, blockquotes
- Auto Table of Contents

```python
def hello():
    print('Hello, PDF!')
```
"></textarea>
    <div id="editor-footer">
      <span id="line-count">0 lines</span>
      <span>·</span>
      <span>Live preview updates automatically</span>
    </div>
  </div>

  <!-- Drag divider -->
  <div id="divider"></div>

  <!-- Preview -->
  <div id="preview-pane">
    <div id="preview-header">
      <div class="live-dot"></div>
      <span>Live Preview</span>
      <span style="flex:1"></span>
      <span id="preview-label" style="font-size:11px;color:var(--dim)">A4 · PDF layout</span>
    </div>
    <div id="preview-scroll">
      <iframe id="preview-frame" scrolling="yes" sandbox="allow-same-origin"></iframe>
    </div>
    <div id="preview-spinner"><div class="spin"></div></div>
  </div>
</div>

<!-- Toast -->
<div id="toast"></div>

<script>
const editor      = document.getElementById('editor');
const previewFrame= document.getElementById('preview-frame');
const previewScroll=document.getElementById('preview-scroll');
const statusEl    = document.getElementById('status');
const charCount   = document.getElementById('char-count');
const lineCount   = document.getElementById('line-count');
const fileLabel   = document.getElementById('file-name-label');
const fileInput   = document.getElementById('file-input');
const btnConvert  = document.getElementById('btn-convert');
const btnDownload = document.getElementById('btn-download');
const tocSwitch   = document.getElementById('toc-switch');
const tocToggle   = document.getElementById('toc-toggle');
const fontSizeEl  = document.getElementById('font-size');
const divider     = document.getElementById('divider');
const editorPane  = document.getElementById('editor-pane');
const toastEl     = document.getElementById('toast');
const spinner     = document.getElementById('preview-spinner');

let currentTheme  = 'default';
let tocEnabled    = true;
let previewTimer  = null;
let lastToken     = null;
let currentFile   = 'untitled';
let isDragging    = false;

// ── Theme picker ──────────────────────────────────────────────────────────────
document.getElementById('theme-row').querySelectorAll('.theme-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentTheme = btn.dataset.theme;
    schedulePreview(0);
  });
});

// ── TOC toggle ────────────────────────────────────────────────────────────────
tocToggle.addEventListener('click', () => {
  tocEnabled = !tocEnabled;
  tocSwitch.classList.toggle('on', tocEnabled);
  schedulePreview(0);
});

// ── Font size ─────────────────────────────────────────────────────────────────
fontSizeEl.addEventListener('change', () => schedulePreview(0));

// ── File upload ───────────────────────────────────────────────────────────────
fileInput.addEventListener('change', () => {
  const f = fileInput.files[0];
  if (!f) return;
  currentFile = f.name.replace(/\.(md|markdown|txt)$/i, '');
  fileLabel.textContent = f.name;
  const reader = new FileReader();
  reader.onload = e => {
    editor.value = e.target.result;
    updateCounts();
    schedulePreview(0);
  };
  reader.readAsText(f);
  fileInput.value = '';
});

// ── Editor typing ─────────────────────────────────────────────────────────────
editor.addEventListener('input', () => {
  updateCounts();
  schedulePreview(600); // debounce 600ms
});

// Tab key → insert spaces
editor.addEventListener('keydown', e => {
  if (e.key === 'Tab') {
    e.preventDefault();
    const s = editor.selectionStart, end = editor.selectionEnd;
    editor.value = editor.value.substring(0, s) + '  ' + editor.value.substring(end);
    editor.selectionStart = editor.selectionEnd = s + 2;
  }
});

function updateCounts() {
  const v = editor.value;
  charCount.textContent = v.length.toLocaleString() + ' chars';
  lineCount.textContent = (v.split('\n').length).toLocaleString() + ' lines';
}

// ── Preview ───────────────────────────────────────────────────────────────────
function schedulePreview(delay = 600) {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(refreshPreview, delay);
}

async function refreshPreview() {
  const content = editor.value.trim();
  if (!content) {
    previewFrame.srcdoc = '<html><body style="background:#e0e0e0;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:#aaa;font-size:14px">Start typing to see preview…</body></html>';
    setStatus('ready', '');
    return;
  }

  setStatus('updating', 'updating…');
  try {
    const res = await fetch('/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, theme: currentTheme })
    });
    if (!res.ok) throw new Error('Preview failed');
    const html = await res.text();

    // Preserve scroll position
    let scrollY = 0;
    try { scrollY = previewFrame.contentWindow.scrollY || 0; } catch(e){}

    previewFrame.srcdoc = html;
    previewFrame.onload = () => {
      try { previewFrame.contentWindow.scrollTo(0, scrollY); } catch(e){}
      // size the iframe to its content
      resizeFrame();
    };
    setStatus('ok', 'preview updated');
  } catch(err) {
    setStatus('err', 'preview error');
  }
}

function resizeFrame() {
  try {
    const body = previewFrame.contentDocument?.body;
    if (body) {
      const h = body.scrollHeight;
      previewFrame.style.height = Math.max(h, previewScroll.clientHeight) + 'px';
    }
  } catch(e) {}
}

// Keep frame sized when window resizes
window.addEventListener('resize', resizeFrame);

// ── Generate PDF ──────────────────────────────────────────────────────────────
btnConvert.addEventListener('click', async () => {
  const content = editor.value.trim();
  if (!content) { showToast('Nothing to convert — editor is empty.', 'error'); return; }

  btnConvert.disabled = true;
  btnDownload.disabled = true;
  lastToken = null;
  setStatus('updating', 'generating…');

  try {
    const res = await fetch('/convert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content,
        theme:     currentTheme,
        toc:       tocEnabled,
        font_size: parseInt(fontSizeEl.value) || 11,
        filename:  currentFile,
      })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    lastToken = data.token;
    btnDownload.disabled = false;
    setStatus('ok', `${data.pages}p · ${data.size_kb}KB`);
    showToast(`✅ PDF ready — ${data.pages} pages, ${data.size_kb} KB`, 'success');
  } catch(err) {
    setStatus('err', 'failed');
    showToast('⚠ ' + err.message, 'error');
  } finally {
    btnConvert.disabled = false;
  }
});

// ── Download ──────────────────────────────────────────────────────────────────
btnDownload.addEventListener('click', () => {
  if (!lastToken) return;
  const a = document.createElement('a');
  a.href = '/download/' + lastToken;
  a.download = currentFile + '.pdf';
  a.click();
  btnDownload.disabled = true;
  lastToken = null;
  setStatus('ready', 'downloaded');
});

// ── Status pill ───────────────────────────────────────────────────────────────
function setStatus(type, text) {
  statusEl.className = type === 'ok' ? 'ok' : type === 'err' ? 'err' : '';
  statusEl.textContent = text || 'ready';
}

// ── Toast ─────────────────────────────────────────────────────────────────────
let toastTimer;
function showToast(msg, type = 'success') {
  toastEl.textContent = msg;
  toastEl.className = 'show ' + type;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toastEl.className = ''; }, 3500);
}

// ── Drag-to-resize divider ────────────────────────────────────────────────────
divider.addEventListener('mousedown', e => {
  isDragging = true;
  divider.classList.add('dragging');
  document.body.style.cursor = 'col-resize';
  document.body.style.userSelect = 'none';
  e.preventDefault();
});

document.addEventListener('mousemove', e => {
  if (!isDragging) return;
  const ws = document.getElementById('workspace');
  const rect = ws.getBoundingClientRect();
  let pct = (e.clientX - rect.left) / rect.width * 100;
  pct = Math.min(80, Math.max(20, pct));
  editorPane.style.width = pct + '%';
  resizeFrame();
});

document.addEventListener('mouseup', () => {
  if (!isDragging) return;
  isDragging = false;
  divider.classList.remove('dragging');
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
});

// ── Init ──────────────────────────────────────────────────────────────────────
const SAMPLE = `# Project Documentation

A quick demo of the live Markdown editor.

## Getting Started

Install dependencies and run:

\`\`\`bash
pip install -r requirements.txt
python app.py
\`\`\`

## Features

| Feature | Status |
|---------|--------|
| Live preview | ✅ |
| Syntax highlight | ✅ |
| 4 Themes | ✅ |
| PDF export | ✅ |

> **Tip:** Edit this text — the preview updates automatically.

## Code Example

\`\`\`python
def greet(name: str) -> str:
    return f"Hello, {name}!"

print(greet("World"))
\`\`\`

## Lists

- Item one
- Item two
  - Nested item
  - Another nested
- Item three

1. First step
2. Second step
3. Third step
`;

editor.value = SAMPLE;
updateCounts();
schedulePreview(200);
</script>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
