# PDF Toolkit Pro — Deployment Guide

## Run Locally (PC)

```bash
# Install dependencies
pip install -r requirements.txt

# Run
streamlit run pdf_toolkit.py
```

Opens at: http://localhost:8501

---

## Deploy Free on Streamlit Community Cloud

1. Push both files to a **GitHub repo** (public or private)
2. Go to https://share.streamlit.io → **New app**
3. Connect your GitHub repo
4. Main file path: `pdf_toolkit.py`
5. Click **Deploy** — done. Works from any browser/device.

> No proxy needed. API key entered in sidebar stays server-side (Streamlit backend).
> Unlike your HTML tools, the key is never exposed in the browser.

---

## Features

| Feature            | Engine Used        |
|--------------------|--------------------|
| Merge PDFs         | pypdf              |
| Split PDF          | pypdf              |
| Extract Text       | PyMuPDF (fast) / pypdf fallback |
| Compress PDF       | PyMuPDF (garbage collect + deflate) |
| Image → PDF        | Pillow             |
| PDF → Image        | PyMuPDF            |
| Reorder Pages      | pypdf              |
| AI Analysis        | Anthropic Claude API (direct, no proxy) |

## Performance Notes for Large PDFs

- Text extraction reads **only requested pages** — a 500-page PDF with pages 3-5 requested
  loads just 3 pages, not the whole file.
- PyMuPDF is 3-5x faster than pypdf for text extraction and conversion.
- Compression uses PyMuPDF's garbage collector levels (1-4) + deflate streams.
- All operations run in memory (BytesIO) — no temp files written to disk.
