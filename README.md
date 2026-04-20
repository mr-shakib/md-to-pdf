# MD → PDF Converter · Web App

A free, self-hosted tool for converting Markdown files to professional PDFs.
Upload a `.md` file, pick a theme, and download a polished PDF instantly.

---

## 🚀 Deploy Free on Render.com (Recommended)

**No credit card required. Takes ~5 minutes.**

### Step 1 — Push to GitHub

1. Create a free account at [github.com](https://github.com) if you don't have one.
2. Create a **new repository** (e.g. `md-to-pdf`).
3. Upload all files from this folder into the repo (drag & drop in the GitHub UI, or use Git):

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/md-to-pdf.git
git push -u origin main
```

### Step 2 — Deploy on Render

1. Go to [render.com](https://render.com) and sign up (free).
2. Click **"New +"** → **"Web Service"**.
3. Connect your GitHub account and select your `md-to-pdf` repo.
4. Render will auto-detect `render.yaml` — just click **"Create Web Service"**.
5. Wait ~3 minutes for the first build to finish.
6. Your app will be live at `https://md-to-pdf.onrender.com` (or similar).

> ⚠️ **Free tier note:** The app "sleeps" after 15 min of inactivity.
> First visit after sleep takes ~15-30 seconds to wake up. This is normal.

---

## 🐳 Deploy with Docker (any server)

```dockerfile
FROM python:3.12-slim

# Install WeasyPrint system dependencies
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev shared-mime-info fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120"]
```

Build and run:
```bash
docker build -t md-to-pdf .
docker run -p 5000:5000 md-to-pdf
# Open http://localhost:5000
```

---

## 💻 Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py

# Open http://localhost:5000
```

---

## 📁 File Structure

```
md-to-pdf/
├── app.py            ← Flask web server + UI
├── md_to_pdf.py      ← Core Markdown → PDF converter
├── requirements.txt  ← Python dependencies
├── render.yaml       ← Render.com deploy config
├── Procfile          ← Gunicorn start command
└── README.md         ← This file
```

---

## ✨ Features

- 4 themes: Default, Dark, Minimal, Technical
- Syntax highlighting for all major languages
- Auto Table of Contents from headings
- Page numbers, chapter headers/footers
- Tables, blockquotes, footnotes, code blocks
- Up to 5 MB file upload
- No sign-up, no storage — files are never saved on the server

---

## CLI Usage

You can also use the converter directly from the command line:

```bash
# Basic usage
python md_to_pdf.py README.md

# With options
python md_to_pdf.py guide.md output.pdf --theme dark --font-size 12
python md_to_pdf.py report.md --theme minimal --no-toc
```

---

## Free Hosting Alternatives

| Platform | Free Tier | Notes |
|----------|-----------|-------|
| **Render.com** | 750 hrs/mo | ✅ Best choice, auto-deploy from Git |
| **PythonAnywhere** | 1 app | Good but slower builds |
| **Fly.io** | 3 shared VMs | Requires Docker |
| **Railway** | Trial credit only | No permanent free tier |
