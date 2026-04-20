"""
app.py — Flask web server for the MD → PDF converter.
"""

import os
import uuid
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template_string

# Import our converter
import sys
sys.path.insert(0, os.path.dirname(__file__))
from md_to_pdf import convert, THEMES

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MD → PDF · Professional Docs Converter</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #13131a;
    --surface2: #1c1c28;
    --border: #2a2a3d;
    --accent: #6c63ff;
    --accent2: #a78bfa;
    --text: #e2e2f0;
    --text-dim: #8888aa;
    --success: #34d399;
    --error: #f87171;
    --radius: 12px;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  /* ── Header ── */
  header {
    width: 100%;
    padding: 1.5rem 2rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-weight: 700;
    font-size: 1.1rem;
    letter-spacing: -0.02em;
  }

  .logo-icon {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
  }

  .badge {
    margin-left: auto;
    font-size: 0.7rem;
    font-weight: 500;
    padding: 0.25rem 0.6rem;
    border-radius: 99px;
    background: rgba(108,99,255,0.15);
    color: var(--accent2);
    border: 1px solid rgba(108,99,255,0.3);
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  /* ── Main ── */
  main {
    width: 100%;
    max-width: 780px;
    padding: 3rem 1.5rem 4rem;
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .hero { text-align: center; }
  .hero h1 {
    font-size: clamp(1.8rem, 4vw, 2.8rem);
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.15;
    background: linear-gradient(135deg, #fff 40%, var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.6rem;
  }
  .hero p {
    color: var(--text-dim);
    font-size: 1rem;
    line-height: 1.6;
  }

  /* ── Drop zone ── */
  .dropzone {
    border: 2px dashed var(--border);
    border-radius: var(--radius);
    padding: 3rem 2rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    background: var(--surface);
    position: relative;
  }
  .dropzone:hover, .dropzone.dragover {
    border-color: var(--accent);
    background: rgba(108,99,255,0.05);
  }
  .dropzone input[type="file"] {
    position: absolute; inset: 0;
    opacity: 0; cursor: pointer; width: 100%; height: 100%;
  }
  .dropzone-icon { font-size: 2.5rem; margin-bottom: 0.75rem; display: block; }
  .dropzone h2 { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.3rem; }
  .dropzone p { color: var(--text-dim); font-size: 0.875rem; }
  .dropzone .filename {
    margin-top: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: var(--accent2);
    padding: 0.3rem 0.8rem;
    background: rgba(108,99,255,0.1);
    border-radius: 6px;
    display: inline-block;
  }

  /* ── Options ── */
  .options-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .field label {
    display: block;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.45rem;
  }

  select, input[type="number"] {
    width: 100%;
    padding: 0.65rem 0.9rem;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    outline: none;
    transition: border-color 0.2s;
    -webkit-appearance: none;
  }
  select:focus, input[type="number"]:focus {
    border-color: var(--accent);
  }

  /* ── Theme cards ── */
  .theme-picker { grid-column: 1 / -1; }
  .theme-picker label {
    display: block;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.6rem;
  }
  .themes {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.6rem;
  }
  .theme-card {
    border: 2px solid var(--border);
    border-radius: 10px;
    padding: 0.75rem;
    cursor: pointer;
    transition: all 0.15s;
    text-align: center;
    background: var(--surface2);
  }
  .theme-card:hover { border-color: var(--accent2); }
  .theme-card.active { border-color: var(--accent); background: rgba(108,99,255,0.1); }
  .theme-card .swatch {
    height: 36px;
    border-radius: 6px;
    margin-bottom: 0.5rem;
  }
  .theme-card span { font-size: 0.78rem; font-weight: 500; color: var(--text-dim); }
  .theme-card.active span { color: var(--accent2); }

  /* ── Toggle ── */
  .toggle-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    cursor: pointer;
  }
  .toggle-label { font-size: 0.9rem; font-weight: 500; }
  .toggle-desc { font-size: 0.78rem; color: var(--text-dim); margin-top: 0.15rem; }
  .toggle {
    width: 42px; height: 24px;
    background: var(--border);
    border-radius: 99px;
    position: relative;
    transition: background 0.2s;
    flex-shrink: 0;
  }
  .toggle::after {
    content: '';
    width: 18px; height: 18px;
    background: white;
    border-radius: 50%;
    position: absolute;
    top: 3px; left: 3px;
    transition: transform 0.2s;
  }
  .toggle.on { background: var(--accent); }
  .toggle.on::after { transform: translateX(18px); }

  /* ── Button ── */
  .btn-convert {
    width: 100%;
    padding: 1rem;
    background: linear-gradient(135deg, var(--accent), #8b5cf6);
    color: white;
    font-family: 'Inter', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    border: none;
    border-radius: var(--radius);
    cursor: pointer;
    transition: opacity 0.2s, transform 0.1s;
    letter-spacing: 0.01em;
  }
  .btn-convert:hover { opacity: 0.9; }
  .btn-convert:active { transform: scale(0.99); }
  .btn-convert:disabled { opacity: 0.5; cursor: not-allowed; }

  /* ── Progress ── */
  .progress-wrap {
    display: none;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    padding: 2rem;
    background: var(--surface);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    text-align: center;
  }
  .progress-wrap.visible { display: flex; }
  .spinner {
    width: 40px; height: 40px;
    border: 3px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .progress-text { color: var(--text-dim); font-size: 0.9rem; }

  /* ── Result ── */
  .result {
    display: none;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    padding: 2rem;
    background: rgba(52, 211, 153, 0.05);
    border: 1px solid rgba(52, 211, 153, 0.3);
    border-radius: var(--radius);
    text-align: center;
  }
  .result.visible { display: flex; }
  .result-icon { font-size: 2.5rem; }
  .result h3 { font-size: 1.1rem; font-weight: 600; color: var(--success); }
  .result p { font-size: 0.85rem; color: var(--text-dim); }
  .btn-download {
    padding: 0.7rem 1.8rem;
    background: var(--success);
    color: #0a2a1e;
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: opacity 0.2s;
    text-decoration: none;
    display: inline-block;
  }
  .btn-download:hover { opacity: 0.85; }
  .btn-reset {
    background: none;
    border: 1px solid var(--border);
    color: var(--text-dim);
    padding: 0.5rem 1.2rem;
    border-radius: 8px;
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    cursor: pointer;
    transition: border-color 0.2s;
  }
  .btn-reset:hover { border-color: var(--accent2); color: var(--accent2); }

  /* ── Error ── */
  .error-box {
    display: none;
    padding: 1rem 1.2rem;
    background: rgba(248,113,113,0.08);
    border: 1px solid rgba(248,113,113,0.3);
    border-radius: 8px;
    color: var(--error);
    font-size: 0.875rem;
  }
  .error-box.visible { display: block; }

  /* ── Features row ── */
  .features {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    margin-top: 0.5rem;
  }
  .feature {
    padding: 1rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    text-align: center;
  }
  .feature .fi { font-size: 1.4rem; margin-bottom: 0.4rem; }
  .feature h4 { font-size: 0.8rem; font-weight: 600; margin-bottom: 0.2rem; }
  .feature p { font-size: 0.72rem; color: var(--text-dim); line-height: 1.4; }

  footer {
    margin-top: auto;
    padding: 1.5rem;
    color: var(--text-dim);
    font-size: 0.78rem;
    text-align: center;
    border-top: 1px solid var(--border);
    width: 100%;
  }

  @media (max-width: 520px) {
    .options-grid { grid-template-columns: 1fr; }
    .themes { grid-template-columns: repeat(2, 1fr); }
    .features { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">📄</div>
    MD → PDF
  </div>
  <span class="badge">Free Tool</span>
</header>

<main>
  <div class="hero">
    <h1>Markdown to Professional PDF</h1>
    <p>Upload any <code style="background:rgba(255,255,255,0.08);padding:0.1em 0.4em;border-radius:4px;font-family:JetBrains Mono,monospace;font-size:0.9em">.md</code> file and get a beautifully formatted PDF — with syntax highlighting, tables, TOC, and page numbers.</p>
  </div>

  <!-- Drop Zone -->
  <div class="dropzone" id="dropzone">
    <input type="file" id="fileInput" accept=".md,.markdown,.txt">
    <span class="dropzone-icon">📂</span>
    <h2>Drop your Markdown file here</h2>
    <p>or click to browse · .md / .markdown supported</p>
    <span class="filename" id="filename" style="display:none"></span>
  </div>

  <!-- Options -->
  <div class="options-grid">

    <div class="field theme-picker">
      <label>Theme</label>
      <div class="themes" id="themePicker">
        <div class="theme-card active" data-theme="default">
          <div class="swatch" style="background:linear-gradient(135deg,#0f3460,#e94560)"></div>
          <span>Default</span>
        </div>
        <div class="theme-card" data-theme="dark">
          <div class="swatch" style="background:linear-gradient(135deg,#0d1117,#58a6ff)"></div>
          <span>Dark</span>
        </div>
        <div class="theme-card" data-theme="minimal">
          <div class="swatch" style="background:linear-gradient(135deg,#fafafa,#333)"></div>
          <span>Minimal</span>
        </div>
        <div class="theme-card" data-theme="technical">
          <div class="swatch" style="background:linear-gradient(135deg,#1a365d,#2b6cb0)"></div>
          <span>Technical</span>
        </div>
      </div>
    </div>

    <div class="field">
      <label>Font Size (pt)</label>
      <input type="number" id="fontSize" value="11" min="8" max="16">
    </div>

    <div class="field">
      <div class="toggle-row" id="tocToggle">
        <div>
          <div class="toggle-label">Table of Contents</div>
          <div class="toggle-desc">Auto-generate TOC from headings</div>
        </div>
        <div class="toggle on" id="tocSwitch"></div>
      </div>
    </div>

  </div>

  <!-- Convert Button -->
  <button class="btn-convert" id="convertBtn" disabled>
    Convert to PDF
  </button>

  <!-- Error -->
  <div class="error-box" id="errorBox"></div>

  <!-- Progress -->
  <div class="progress-wrap" id="progressWrap">
    <div class="spinner"></div>
    <p class="progress-text">Converting your document…</p>
  </div>

  <!-- Result -->
  <div class="result" id="resultBox">
    <div class="result-icon">✅</div>
    <h3>PDF ready!</h3>
    <p id="resultMeta"></p>
    <a class="btn-download" id="downloadLink" href="#" download>⬇ Download PDF</a>
    <button class="btn-reset" id="resetBtn">Convert another file</button>
  </div>

  <!-- Features -->
  <div class="features">
    <div class="feature">
      <div class="fi">🎨</div>
      <h4>4 Themes</h4>
      <p>Default, Dark, Minimal, Technical</p>
    </div>
    <div class="feature">
      <div class="fi">💻</div>
      <h4>Syntax Highlighting</h4>
      <p>All major languages via Pygments</p>
    </div>
    <div class="feature">
      <div class="fi">📑</div>
      <h4>Auto TOC & Page Numbers</h4>
      <p>Headers, footers, and live TOC</p>
    </div>
  </div>

</main>

<footer>
  Built with WeasyPrint + Python Markdown · 100% free, no sign-up needed
</footer>

<script>
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const filenameEl = document.getElementById('filename');
  const convertBtn = document.getElementById('convertBtn');
  const progressWrap = document.getElementById('progressWrap');
  const resultBox = document.getElementById('resultBox');
  const errorBox = document.getElementById('errorBox');
  const downloadLink = document.getElementById('downloadLink');
  const resultMeta = document.getElementById('resultMeta');
  const themePicker = document.getElementById('themePicker');
  const tocSwitch = document.getElementById('tocSwitch');
  const tocToggle = document.getElementById('tocToggle');
  const fontSizeInput = document.getElementById('fontSize');
  const resetBtn = document.getElementById('resetBtn');

  let selectedTheme = 'default';
  let tocEnabled = true;
  let selectedFile = null;

  // Theme picker
  themePicker.querySelectorAll('.theme-card').forEach(card => {
    card.addEventListener('click', () => {
      themePicker.querySelectorAll('.theme-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      selectedTheme = card.dataset.theme;
    });
  });

  // TOC toggle
  tocToggle.addEventListener('click', () => {
    tocEnabled = !tocEnabled;
    tocSwitch.classList.toggle('on', tocEnabled);
  });

  // File input
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
  });

  dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  });

  function setFile(f) {
    selectedFile = f;
    filenameEl.textContent = f.name;
    filenameEl.style.display = 'inline-block';
    convertBtn.disabled = false;
    hideAll();
  }

  function hideAll() {
    progressWrap.classList.remove('visible');
    resultBox.classList.remove('visible');
    errorBox.classList.remove('visible');
    errorBox.textContent = '';
  }

  // Convert
  convertBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    hideAll();
    convertBtn.disabled = true;
    progressWrap.classList.add('visible');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('theme', selectedTheme);
    formData.append('toc', tocEnabled ? '1' : '0');
    formData.append('font_size', fontSizeInput.value);

    try {
      const res = await fetch('/convert', { method: 'POST', body: formData });
      const data = await res.json();

      progressWrap.classList.remove('visible');

      if (data.error) {
        errorBox.textContent = '⚠ ' + data.error;
        errorBox.classList.add('visible');
        convertBtn.disabled = false;
        return;
      }

      downloadLink.href = '/download/' + data.token;
      downloadLink.download = data.filename;
      resultMeta.textContent = `${data.filename} · ${data.size_kb} KB · ${data.pages} pages`;
      resultBox.classList.add('visible');
    } catch (err) {
      progressWrap.classList.remove('visible');
      errorBox.textContent = '⚠ Network error. Please try again.';
      errorBox.classList.add('visible');
      convertBtn.disabled = false;
    }
  });

  resetBtn.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    filenameEl.style.display = 'none';
    filenameEl.textContent = '';
    convertBtn.disabled = true;
    hideAll();
  });
</script>
</body>
</html>
"""

# ── In-memory file store ───────────────────────────────────────────────────────
FILE_STORE: dict[str, dict] = {}


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/convert", methods=["POST"])
def convert_endpoint():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file uploaded."}), 400

    filename = f.filename or "document.md"
    if not filename.lower().endswith((".md", ".markdown", ".txt")):
        return jsonify({"error": "Only .md / .markdown files are supported."}), 400

    theme = request.form.get("theme", "default")
    toc = request.form.get("toc", "1") == "1"
    try:
        font_size = int(request.form.get("font_size", 11))
        font_size = max(8, min(16, font_size))
    except ValueError:
        font_size = 11

    # Write upload to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tmp_in:
        f.save(tmp_in.name)
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
        os.unlink(tmp_in_path)
        return jsonify({"error": f"Conversion failed: {str(e)}"}), 500
    finally:
        try:
            os.unlink(tmp_in_path)
        except Exception:
            pass

    # Read PDF bytes and store temporarily
    pdf_bytes = Path(tmp_out).read_bytes()
    os.unlink(tmp_out)

    size_kb = round(len(pdf_bytes) / 1024, 1)

    # Rough page estimate: ~3 KB per page for typical docs
    pages = max(1, len(pdf_bytes) // 3000)

    token = uuid.uuid4().hex
    out_filename = Path(filename).stem + ".pdf"
    FILE_STORE[token] = {"bytes": pdf_bytes, "filename": out_filename}

    return jsonify(
        {
            "token": token,
            "filename": out_filename,
            "size_kb": size_kb,
            "pages": pages,
        }
    )


@app.route("/download/<token>")
def download(token):
    entry = FILE_STORE.pop(token, None)
    if not entry:
        return "File not found or already downloaded.", 404

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(entry["bytes"])
        tmp_path = tmp.name

    return send_file(
        tmp_path,
        as_attachment=True,
        download_name=entry["filename"],
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
