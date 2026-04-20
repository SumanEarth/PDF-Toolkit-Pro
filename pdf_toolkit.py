import streamlit as st
import io
import json
import zipfile
import requests as req_lib

st.set_page_config(
    page_title="PDF Toolkit Pro",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif;}
.stApp{background:#0f1117;color:#e0e0e0;}
[data-testid="stSidebar"]{background:#161b27!important;border-right:1px solid #2a2f3e;}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:#161b27;padding:6px;border-radius:10px;border:1px solid #2a2f3e;}
.stTabs [data-baseweb="tab"]{background:transparent;color:#8892a4;border-radius:7px;padding:8px 12px;
  font-size:12px;font-weight:600;border:none!important;font-family:'IBM Plex Mono',monospace;}
.stTabs [aria-selected="true"]{background:#1e6ef4!important;color:#fff!important;}
.stButton>button{background:#1e6ef4;color:#fff;border:none;border-radius:8px;font-weight:600;
  font-family:'IBM Plex Mono',monospace;font-size:13px;padding:10px 20px;transition:all .2s;}
.stButton>button:hover{background:#3a82f7;transform:translateY(-1px);}
.stDownloadButton>button{background:#12b76a!important;color:#fff!important;border:none!important;
  border-radius:8px;font-weight:600;font-family:'IBM Plex Mono',monospace;}
.stDownloadButton>button:hover{background:#0ea060!important;}
[data-testid="stFileUploader"]{border:2px dashed #2a2f3e;border-radius:12px;background:#161b27;padding:8px;}
[data-testid="stFileUploader"]:hover{border-color:#1e6ef4;}
.stTextInput input,.stTextArea textarea{background:#1c2133!important;border:1px solid #2a2f3e!important;
  border-radius:8px!important;color:#e0e0e0!important;font-family:'IBM Plex Mono',monospace;}
.stProgress>div>div{background:#1e6ef4;border-radius:4px;}
.page-header{background:linear-gradient(135deg,#1e6ef4 0%,#7b3af5 100%);
  border-radius:14px;padding:20px 24px;margin-bottom:20px;}
.page-header h1{color:#fff;margin:0;font-size:22px;}
.page-header p{color:rgba(255,255,255,.75);margin:4px 0 0 0;font-size:13px;}
.key-ok{color:#12b76a;font-size:11px;font-family:'IBM Plex Mono',monospace;}
.key-err{color:#ef4444;font-size:11px;font-family:'IBM Plex Mono',monospace;}
</style>
""", unsafe_allow_html=True)

# ── Library imports ───────────────────────────────────────────────────────────
try:
    from pypdf import PdfReader, PdfWriter
    PYPDF_OK = True
except ImportError:
    st.error("pypdf not found — run: pip install pypdf"); st.stop()

try:
    import fitz
    FITZ_OK = True
except ImportError:
    FITZ_OK = False

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    import pytesseract
    pytesseract.get_tesseract_version()
    OCR_OK = True
except Exception:
    OCR_OK = False

try:
    import anthropic as _anthropic_lib
    ANTHROPIC_OK = True
except ImportError:
    ANTHROPIC_OK = False

# ── Provider config (ported from ATS CV Tailor v6) ───────────────────────────
PROVIDERS = {
    "Claude (Anthropic)": {
        "id": "anthropic",
        "key_placeholder": "sk-ant-…",
        "key_link": "https://console.anthropic.com/settings/keys",
        "models": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"],
        "needs_key": True, "free": False,
    },
    "Gemini (Google)": {
        "id": "gemini",
        "key_placeholder": "AIza…",
        "key_link": "https://aistudio.google.com/app/apikey",
        "models": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "needs_key": True, "free": True,
    },
    "Groq (Fast & Free)": {
        "id": "groq",
        "key_placeholder": "gsk_…",
        "key_link": "https://console.groq.com/keys",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it",
                   "meta-llama/llama-4-scout-17b-16e-instruct"],
        "needs_key": True, "free": True,
    },
    "OpenAI (ChatGPT)": {
        "id": "openai",
        "key_placeholder": "sk-…",
        "key_link": "https://platform.openai.com/api-keys",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "needs_key": True, "free": False,
    },
    "OpenRouter (Free models)": {
        "id": "openrouter",
        "key_placeholder": "sk-or-…",
        "key_link": "https://openrouter.ai/keys",
        "models": [
            "meta-llama/llama-3.2-3b-instruct:free",
            "google/gemma-3-4b-it:free",
            "microsoft/phi-3-mini-128k-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "qwen/qwen-2.5-7b-instruct:free",
        ],
        "needs_key": True, "free": True,
    },
    "Mistral AI": {
        "id": "mistral",
        "key_placeholder": "Paste Mistral key…",
        "key_link": "https://console.mistral.ai/",
        "models": ["mistral-small-latest", "open-mistral-nemo", "open-mistral-7b"],
        "needs_key": True, "free": True,
    },
    "HuggingFace (Free)": {
        "id": "huggingface",
        "key_placeholder": "hf_… (optional for free tier)",
        "key_link": "https://huggingface.co/settings/tokens",
        "models": [
            "meta-llama/Llama-3.1-8B-Instruct:cerebras",
            "Qwen/Qwen2.5-7B-Instruct:cerebras",
            "mistralai/Mistral-7B-Instruct-v0.3:sambanova",
        ],
        "needs_key": False, "free": True,
    },
    "Ollama (Local PC)": {
        "id": "ollama",
        "key_placeholder": None,
        "key_link": "https://ollama.com/download",
        "models": ["llama3.1:8b", "qwen2.5:7b", "mistral", "phi3"],
        "needs_key": False, "free": True,
    },
}

# ── Helper functions ──────────────────────────────────────────────────────────

def parse_page_range(text, total):
    if not text.strip():
        return list(range(total))
    pages = set()
    for part in text.split(','):
        part = part.strip()
        if '-' in part:
            try:
                s, e = part.split('-', 1)
                pages.update(range(max(0, int(s)-1), min(int(e), total)))
            except Exception:
                pass
        else:
            try:
                n = int(part) - 1
                if 0 <= n < total:
                    pages.add(n)
            except Exception:
                pass
    return sorted(pages)


def get_pdf_page_count(file_bytes):
    if FITZ_OK:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        n = len(doc); doc.close(); return n
    return len(PdfReader(io.BytesIO(file_bytes)).pages)


def extract_text_native(file_bytes, page_indices):
    """Read embedded text layer — instant for digital PDFs."""
    parts = []
    if FITZ_OK:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for idx in page_indices:
            parts.append((idx+1, doc[idx].get_text() or ""))
        doc.close()
    else:
        reader = PdfReader(io.BytesIO(file_bytes))
        for idx in page_indices:
            parts.append((idx+1, reader.pages[idx].extract_text() or ""))
    return parts


def extract_text_ocr(file_bytes, page_indices, lang="ben+eng", dpi=200):
    """
    Tesseract OCR — reads scanned/image-based PDFs including Bangla.
    Requires:
      pip install pytesseract
      Linux/Streamlit Cloud packages.txt: tesseract-ocr  tesseract-ocr-ben
      Windows: install from https://github.com/UB-Mannheim/tesseract/wiki
    """
    if not FITZ_OK:
        return [(idx+1, "[OCR needs PyMuPDF — pip install PyMuPDF]") for idx in page_indices]
    if not PIL_OK:
        return [(idx+1, "[OCR needs Pillow — pip install Pillow]") for idx in page_indices]
    if not OCR_OK:
        return [(idx+1, "[Tesseract not found — see sidebar]") for idx in page_indices]

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    parts = []
    scale = dpi / 72.0
    mat = fitz.Matrix(scale, scale)
    for idx in page_indices:
        pix = doc[idx].get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        try:
            text = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
        except pytesseract.TesseractError as e:
            text = f"[OCR error: {e}]"
        parts.append((idx+1, text))
    doc.close()
    return parts


def human_size(b):
    if b < 1024: return f"{b} B"
    if b < 1048576: return f"{b/1024:.1f} KB"
    return f"{b/1048576:.2f} MB"


def fetch_ollama_models(url):
    try:
        r = req_lib.get(f"{url.rstrip('/')}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


# ── Multi-provider streaming AI caller ───────────────────────────────────────

def call_ai_stream(provider_id, model, api_key, system_prompt, user_msg,
                   ollama_url="http://localhost:11434", max_tokens=2000):
    """
    Generator yielding text chunks from any provider.
    Use: st.write_stream(call_ai_stream(...))

    KEY ADVANTAGE vs HTML/browser tools:
    Python runs server-side — no CORS restrictions, no proxy needed.
    OpenRouter, Mistral, HuggingFace are called directly.
    API key never leaves the server.
    """

    # ── Claude / Anthropic ────────────────────────────────────────────────────
    if provider_id == "anthropic":
        if not ANTHROPIC_OK:
            yield "[anthropic library missing — pip install anthropic]"; return
        client = _anthropic_lib.Anthropic(api_key=api_key)
        with client.messages.stream(
            model=model, max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}]
        ) as stream:
            for chunk in stream.text_stream:
                yield chunk
        return

    # ── Gemini ────────────────────────────────────────────────────────────────
    if provider_id == "gemini":
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:streamGenerateContent?key={api_key}&alt=sse")
        body = {
            "contents": [{"parts": [{"text": system_prompt + "\n\n" + user_msg}]}],
            "generationConfig": {"maxOutputTokens": max_tokens}
        }
        try:
            resp = req_lib.post(url, json=body, stream=True, timeout=60)
            resp.raise_for_status()
            for raw in resp.iter_lines():
                if not raw: continue
                line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                if not line.startswith("data: "): continue
                ds = line[6:].strip()
                if not ds or ds == "[DONE]": continue
                try:
                    chunk = json.loads(ds)
                    t = chunk["candidates"][0]["content"]["parts"][0].get("text","")
                    if t: yield t
                except Exception: pass
        except req_lib.HTTPError as e:
            yield f"\n\n❌ Gemini {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            yield f"\n\n❌ {e}"
        return

    # ── OpenAI-compatible (OpenAI, Groq, OpenRouter, Mistral, HuggingFace) ───
    compat = {
        "openai":      ("https://api.openai.com/v1",     {}),
        "groq":        ("https://api.groq.com/openai/v1",{}),
        "openrouter":  ("https://openrouter.ai/api/v1",  {"HTTP-Referer": "https://pdf-toolkit.streamlit.app"}),
        "mistral":     ("https://api.mistral.ai/v1",     {}),
        "huggingface": ("https://router.huggingface.co/v1", {}),
    }
    if provider_id in compat:
        base, extra = compat[provider_id]
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else "",
            **extra
        }
        body = {
            "model": model, "max_tokens": max_tokens, "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg}
            ]
        }
        try:
            resp = req_lib.post(f"{base}/chat/completions", json=body, headers=headers, stream=True, timeout=60)
            resp.raise_for_status()
            for raw in resp.iter_lines():
                if not raw: continue
                line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                if not line.startswith("data: "): continue
                ds = line[6:].strip()
                if ds == "[DONE]": break
                try:
                    delta = json.loads(ds)["choices"][0]["delta"].get("content","")
                    if delta: yield delta
                except Exception: pass
        except req_lib.HTTPError as e:
            yield f"\n\n❌ HTTP {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            yield f"\n\n❌ {e}"
        return

    # ── Ollama (local) ────────────────────────────────────────────────────────
    if provider_id == "ollama":
        body = {
            "model": model, "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg}
            ]
        }
        try:
            resp = req_lib.post(f"{ollama_url.rstrip('/')}/v1/chat/completions",
                                json=body, stream=True, timeout=120)
            resp.raise_for_status()
            for raw in resp.iter_lines():
                if not raw: continue
                line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                if not line.startswith("data: "): continue
                ds = line[6:].strip()
                if ds == "[DONE]": break
                try:
                    delta = json.loads(ds)["choices"][0]["delta"].get("content","")
                    if delta: yield delta
                except Exception: pass
        except req_lib.ConnectionError:
            yield f"\n\n❌ Cannot reach Ollama at {ollama_url}. Make sure Ollama is running."
        except Exception as e:
            yield f"\n\n❌ {e}"
        return

    yield "[Unknown provider]"


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:10px 0 14px 0;'>
        <div style='font-size:32px;'>📄</div>
        <div style='font-size:17px;font-weight:700;color:#e0e0e0;'>PDF Toolkit Pro</div>
        <div style='font-size:10px;color:#8892a4;font-family:IBM Plex Mono,monospace;'>by Md. Suman Miah </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("**🤖 AI Provider**")

    provider_name = st.selectbox("Provider", list(PROVIDERS.keys()), label_visibility="collapsed")
    prov = PROVIDERS[provider_name]
    prov_id = prov["id"]

    ollama_url = "http://localhost:11434"
    if prov_id == "ollama":
        ollama_url = st.text_input("Ollama URL", value="http://localhost:11434")
        if st.button("🔍 Fetch Ollama Models", use_container_width=True):
            with st.spinner("Checking Ollama…"):
                live = fetch_ollama_models(ollama_url)
            if live:
                st.session_state["ollama_models"] = live
                st.success(f"✅ {len(live)} model(s) found")
            else:
                st.error("❌ Ollama unreachable or no models installed")

    api_key = ""
    if prov_id != "ollama":
        api_key = st.text_input("API Key", type="password",
                                placeholder=prov["key_placeholder"] or "")
        if prov["free"]:
            st.caption(f"🆓 Free tier → [Get key]({prov['key_link']})")
        if api_key:
            st.markdown('<span class="key-ok">✓ Key entered</span>', unsafe_allow_html=True)

    model_options = (
        st.session_state.get("ollama_models", prov["models"])
        if prov_id == "ollama" else prov["models"]
    )
    model = st.selectbox("Model", model_options, label_visibility="collapsed",
                         key="sidebar_model")
    max_tokens = st.slider("Max AI tokens", 500, 4096, 2000, step=100)

    st.divider()
    st.markdown("**🔍 OCR (Bangla / Scanned PDFs)**")

    ocr_lang_label = st.selectbox("OCR Language", [
        "ben+eng — Bangla + English",
        "eng — English only",
        "ben — Bangla only",
    ])
    ocr_lang_code = ocr_lang_label.split(" ")[0]
    ocr_dpi = st.select_slider("OCR DPI", [150, 200, 300], value=200,
                               help="Higher = better Bangla accuracy, slower")

    if OCR_OK:
        st.markdown('<span class="key-ok">✅ Tesseract OCR ready</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="key-err">❌ Tesseract not installed</span>', unsafe_allow_html=True)
        with st.expander("📦 Install Tesseract + Bangla"):
            st.markdown("""
**Windows** — download installer:
`https://github.com/UB-Mannheim/tesseract/wiki`
Then download `ben.traineddata` into:
`C:\\Program Files\\Tesseract-OCR\\tessdata\\`

**Ubuntu / Streamlit Cloud**
Create `packages.txt` in repo root:
```
tesseract-ocr
tesseract-ocr-ben
```
Then `pip install pytesseract`
            """)

    st.divider()
    st.markdown("""
    <div style='font-size:10px;color:#8892a4;line-height:1.9;'>
    ✅ Files processed in memory only<br>
    ✅ No proxy — Python calls APIs directly<br>
    ✅ Bangla OCR via Tesseract<br>
    ✅ Large PDF: only requested pages loaded
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class='page-header'>
    <h1>📄 PDF Toolkit Pro</h1>
    <p>Merge · Split · Extract (OCR + Bangla) · Compress · Image↔PDF · Reorder · AI Analysis</p>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs([
    "📤 Merge", "✂️ Split", "📝 Extract Text",
    "🗜️ Compress", "🖼️ Image→PDF", "📸 PDF→Image",
    "🔀 Reorder", "🤖 AI Analysis"
])

# ════════════════════════════════════════════════════════════════
# TAB 1 — MERGE
# ════════════════════════════════════════════════════════════════
with tabs[0]:
    st.subheader("📤 Merge Multiple PDFs")
    files = st.file_uploader("Upload PDFs (multiple)", type="pdf",
                             accept_multiple_files=True, key="mg")
    if files:
        st.markdown(f"**{len(files)} file(s) — set merge order:**")
        order_map = {}
        for i, f in enumerate(files):
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.markdown(f"<span style='color:#8892a4;font-size:13px;'>📄 {f.name}</span>",
                            unsafe_allow_html=True)
            with c2:
                order_map[i] = st.number_input("", 1, len(files), i+1,
                                               key=f"mo{i}", label_visibility="collapsed")
            with c3:
                st.markdown(f"<span style='color:#5a6478;font-size:11px;'>{human_size(f.size)}</span>",
                            unsafe_allow_html=True)

        if st.button("🔗 Merge Now", type="primary", use_container_width=True):
            sorted_i = sorted(range(len(files)), key=lambda i: order_map[i])
            writer = PdfWriter(); bar = st.progress(0, "Merging…"); tp = 0
            for step, idx in enumerate(sorted_i):
                f = files[idx]
                reader = PdfReader(io.BytesIO(f.read()))
                for pg in reader.pages: writer.add_page(pg)
                tp += len(reader.pages)
                bar.progress((step+1)/len(files), f"Adding {f.name}…")
            out = io.BytesIO(); writer.write(out); bar.empty()
            st.success(f"✅ Merged {len(files)} PDFs → {tp} pages total")
            st.download_button("📥 Download Merged PDF", out.getvalue(),
                               "merged.pdf", "application/pdf", use_container_width=True)

# ════════════════════════════════════════════════════════════════
# TAB 2 — SPLIT
# ════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("✂️ Split PDF")
    mode = st.radio("Mode", ["Split every page into separate PDFs",
                             "Extract page range as one PDF"], horizontal=True)
    upl = st.file_uploader("Upload PDF", type="pdf", key="sp")

    if upl:
        raw = upl.read(); total = get_pdf_page_count(raw)
        st.info(f"📄 **{upl.name}** — {total} pages · {human_size(len(raw))}")

        if mode == "Split every page into separate PDFs":
            rng = st.text_input("Pages to include (empty=all)", placeholder="e.g. 1-5, 8")
            if st.button("✂️ Split", type="primary", use_container_width=True):
                idxs = parse_page_range(rng, total) if rng.strip() else list(range(total))
                reader = PdfReader(io.BytesIO(raw))
                zip_buf = io.BytesIO(); bar = st.progress(0)
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for i, pg in enumerate(idxs):
                        w = PdfWriter(); w.add_page(reader.pages[pg])
                        pb = io.BytesIO(); w.write(pb)
                        zf.writestr(f"page_{pg+1:04d}.pdf", pb.getvalue())
                        bar.progress((i+1)/len(idxs))
                bar.empty()
                st.success(f"✅ Split into {len(idxs)} PDFs (zipped)")
                st.download_button("📥 Download ZIP", zip_buf.getvalue(),
                                   "split_pages.zip", "application/zip", use_container_width=True)
        else:
            c1, c2 = st.columns(2)
            with c1: start = st.number_input("Start page", 1, total, 1)
            with c2: end = st.number_input("End page", int(start), total, total)
            if st.button("✂️ Extract Range", type="primary", use_container_width=True):
                reader = PdfReader(io.BytesIO(raw)); w = PdfWriter()
                for i in range(int(start)-1, int(end)): w.add_page(reader.pages[i])
                out = io.BytesIO(); w.write(out)
                st.success(f"✅ Extracted pages {int(start)}–{int(end)}")
                st.download_button("📥 Download PDF", out.getvalue(),
                                   f"pages_{int(start)}-{int(end)}.pdf",
                                   "application/pdf", use_container_width=True)

# ════════════════════════════════════════════════════════════════
# TAB 3 — EXTRACT TEXT (Native + OCR + Bangla)
# ════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("📝 Extract Text — Native + OCR (Bangla supported)")
    st.caption(
        "**Native mode**: reads embedded text layer — instant, works for digital PDFs.  \n"
        "**OCR mode**: scans page as image with Tesseract — for scanned PDFs, "
        "Bangla text, government documents, image-only PDFs."
    )

    upl = st.file_uploader("Upload PDF", type="pdf", key="ex")

    if upl:
        raw = upl.read(); total = get_pdf_page_count(raw)
        st.info(f"📄 **{upl.name}** — {total} pages · {human_size(len(raw))}")

        c1, c2 = st.columns([3, 1])
        with c1:
            pg_input = st.text_input(
                "📌 Pages to extract",
                placeholder="e.g. 1, 3-5, 8  (empty = all)",
                help="Only these pages are read — large PDFs stay fast"
            )
        with c2:
            st.metric("Total pages", total)

        col_a, col_b = st.columns(2)
        with col_a:
            extract_mode = st.radio("Extraction method",
                                    ["🚀 Native (fast)", "🔍 OCR (Bangla / scanned)"])
        with col_b:
            if "OCR" in extract_mode:
                st.markdown(f"""
                **Active OCR settings:**
                - Language: `{ocr_lang_code}`
                - DPI: `{ocr_dpi}`
                - Engine: Tesseract {'✅' if OCR_OK else '❌'}
                """)
                if not OCR_OK:
                    st.warning("Tesseract not found — see sidebar for setup")

        if st.button("📝 Extract Text", type="primary", use_container_width=True):
            idxs = parse_page_range(pg_input, total) if pg_input.strip() else list(range(total))
            if not idxs:
                st.error("No valid pages in your input.")
            elif "OCR" in extract_mode and not OCR_OK:
                st.error("❌ Tesseract not installed. See sidebar.")
            else:
                bar = st.progress(0, "Extracting…")
                if "OCR" in extract_mode:
                    raw_results = extract_text_ocr(raw, idxs, lang=ocr_lang_code, dpi=ocr_dpi)
                else:
                    raw_results = extract_text_native(raw, idxs)

                results = []
                for i, (pg_num, text) in enumerate(raw_results):
                    results.append(f"{'='*50}\nPAGE {pg_num}\n{'='*50}\n{text or '[No text found on this page]'}")
                    bar.progress((i+1)/len(idxs), f"Page {pg_num}…")
                bar.empty()

                full_text = "\n\n".join(results)

                # Hint to switch to OCR if native returned nothing
                if "Native" in extract_mode:
                    non_empty = [t for _, t in raw_results if t.strip()]
                    if not non_empty:
                        st.warning(
                            "⚠️ No text found in native layer. This PDF is likely **scanned or image-based**. "
                            "Switch to **OCR mode** to extract Bangla or image text."
                        )

                st.session_state["shared_text"] = full_text
                st.session_state["shared_source"] = (
                    f"{upl.name} — pages {pg_input or 'all'} "
                    f"[{'OCR' if 'OCR' in extract_mode else 'Native'}]"
                )

                wc = len(full_text.split())
                st.success(f"✅ {len(idxs)} page(s) · {wc:,} words — text sent to AI Analysis tab")
                st.text_area("Preview", full_text, height=380)
                st.download_button("📥 Save as .txt", full_text.encode("utf-8"),
                                   "extracted.txt", "text/plain", use_container_width=True)

# ════════════════════════════════════════════════════════════════
# TAB 4 — COMPRESS
# ════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("🗜️ Compress PDF")
    upl = st.file_uploader("Upload PDF", type="pdf", key="cp")

    if upl:
        raw = upl.read(); orig = len(raw)
        total = get_pdf_page_count(raw)
        st.info(f"📄 **{upl.name}** — {total} pages · {human_size(orig)}")

        level = st.select_slider("Compression level",
                                 ["Minimal","Balanced","Aggressive","Maximum"], value="Balanced")

        if st.button("🗜️ Compress", type="primary", use_container_width=True):
            if FITZ_OK:
                doc = fitz.open(stream=raw, filetype="pdf"); out = io.BytesIO()
                gc = {"Minimal":1,"Balanced":2,"Aggressive":3,"Maximum":4}[level]
                df = level in ("Aggressive","Maximum")
                doc.save(out, garbage=gc, deflate=df, deflate_images=df, deflate_fonts=df)
                doc.close()
                c = out.getvalue(); ns = len(c)
                pct = (1 - ns/orig)*100
                if pct > 0:
                    st.success(f"✅ Reduced by **{pct:.1f}%** ({human_size(orig)} → {human_size(ns)})")
                else:
                    st.warning("PDF already well-optimised. Minimal reduction possible.")
                st.download_button("📥 Download Compressed PDF", c,
                                   "compressed.pdf","application/pdf",use_container_width=True)
            else:
                reader = PdfReader(io.BytesIO(raw)); w = PdfWriter()
                bar = st.progress(0)
                for i, page in enumerate(reader.pages):
                    page.compress_content_streams(); w.add_page(page)
                    bar.progress((i+1)/total)
                out = io.BytesIO(); w.write(out); bar.empty()
                ns = len(out.getvalue())
                st.success(f"✅ Compressed · {(1-ns/orig)*100:.1f}% reduction")
                st.download_button("📥 Download", out.getvalue(),
                                   "compressed.pdf","application/pdf",use_container_width=True)

# ════════════════════════════════════════════════════════════════
# TAB 5 — IMAGE → PDF  (fixed: width= instead of use_column_width=)
# ════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("🖼️ Image → PDF")
    if not PIL_OK:
        st.error("Pillow not installed: `pip install Pillow`")
    else:
        imgs = st.file_uploader("Upload images", type=["jpg","jpeg","png","webp","bmp"],
                                accept_multiple_files=True, key="i2p")
        if imgs:
            st.markdown(f"**{len(imgs)} image(s)** — preview (first 4):")
            cols = st.columns(min(len(imgs), 4))
            for i, img_f in enumerate(imgs[:4]):
                with cols[i]:
                    st.image(img_f, caption=img_f.name, width=180)   # ← fixed deprecation

            c1, c2 = st.columns(2)
            with c1: ps = st.selectbox("Page size", ["Match image","A4 (210×297 mm)","Letter (8.5×11 in)"])
            with c2: dpi_o = st.select_slider("DPI", [72,96,150,200,300], value=150)

            if st.button("🖼️ Convert to PDF", type="primary", use_container_width=True):
                pil_imgs = []; bar = st.progress(0)
                for i, img_f in enumerate(imgs):
                    pil_imgs.append(Image.open(img_f).convert("RGB"))
                    bar.progress((i+1)/len(imgs))
                bar.empty()
                if ps == "A4 (210×297 mm)":
                    pil_imgs = [img.resize((int(210/25.4*dpi_o), int(297/25.4*dpi_o)), Image.LANCZOS) for img in pil_imgs]
                elif ps == "Letter (8.5×11 in)":
                    pil_imgs = [img.resize((int(8.5*dpi_o), int(11*dpi_o)), Image.LANCZOS) for img in pil_imgs]
                out = io.BytesIO()
                pil_imgs[0].save(out, "PDF", save_all=True, append_images=pil_imgs[1:], resolution=dpi_o)
                st.success(f"✅ {len(imgs)} image(s) → PDF ({human_size(len(out.getvalue()))})")
                st.download_button("📥 Download PDF", out.getvalue(),
                                   "images.pdf","application/pdf",use_container_width=True)

# ════════════════════════════════════════════════════════════════
# TAB 6 — PDF → IMAGE  (fixed: width= instead of use_column_width=)
# ════════════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("📸 PDF → Image")
    if not FITZ_OK:
        st.error("PyMuPDF required: `pip install PyMuPDF`")
    else:
        upl = st.file_uploader("Upload PDF", type="pdf", key="p2i")
        if upl:
            raw = upl.read(); total = get_pdf_page_count(raw)
            st.metric("Pages", total)
            c1, c2, c3 = st.columns(3)
            with c1: rng = st.text_input("Pages", placeholder="e.g. 1-3 (empty=all)")
            with c2: dpi = st.select_slider("DPI", [72,96,150,200,300], value=150)
            with c3: fmt = st.selectbox("Format", ["PNG","JPEG","WEBP"])

            if st.button("📸 Convert", type="primary", use_container_width=True):
                idxs = parse_page_range(rng, total) if rng.strip() else list(range(total))
                doc = fitz.open(stream=raw, filetype="pdf")
                zip_buf = io.BytesIO(); bar = st.progress(0,"Converting…"); shown = False
                with zipfile.ZipFile(zip_buf,"w") as zf:
                    for i, pg in enumerate(idxs):
                        mat = fitz.Matrix(dpi/72, dpi/72)
                        pix = doc[pg].get_pixmap(matrix=mat)
                        zf.writestr(f"page_{pg+1:04d}.{fmt.lower()}", pix.tobytes(fmt.lower()))
                        if not shown and PIL_OK:
                            img = Image.frombytes("RGB",[pix.width,pix.height],pix.samples)
                            st.image(img, caption=f"Preview — Page {pg+1}", width=380)  # ← fixed
                            shown = True
                        bar.progress((i+1)/len(idxs), f"Page {pg+1}…")
                doc.close(); bar.empty()
                st.success(f"✅ {len(idxs)} page(s) at {dpi} DPI → {fmt}")
                st.download_button("📥 Download ZIP", zip_buf.getvalue(),
                                   "pdf_images.zip","application/zip",use_container_width=True)

# ════════════════════════════════════════════════════════════════
# TAB 7 — REORDER
# ════════════════════════════════════════════════════════════════
with tabs[6]:
    st.subheader("🔀 Reorder / Organize Pages")
    upl = st.file_uploader("Upload PDF", type="pdf", key="ro")

    if upl:
        raw = upl.read(); total = get_pdf_page_count(raw)
        st.info(f"📄 **{upl.name}** — {total} pages")
        new_order_str = st.text_area(
            "Page order (edit to reorder; omit numbers to delete those pages)",
            value=", ".join(str(i+1) for i in range(total)),
            height=100,
            help="Example: '3, 1, 2' → page 3 first. Ranges work: '1-3, 5'."
        )
        if st.button("🔀 Apply & Save", type="primary", use_container_width=True):
            new_idxs = parse_page_range(new_order_str, total)
            if not new_idxs:
                st.error("No valid pages found.")
            else:
                reader = PdfReader(io.BytesIO(raw)); w = PdfWriter()
                bar = st.progress(0)
                for i, pg in enumerate(new_idxs):
                    w.add_page(reader.pages[pg]); bar.progress((i+1)/len(new_idxs))
                out = io.BytesIO(); w.write(out); bar.empty()
                removed = total - len(new_idxs)
                st.success(f"✅ {len(new_idxs)} pages" + (f" ({removed} removed)" if removed else ""))
                st.download_button("📥 Download PDF", out.getvalue(),
                                   "reordered.pdf","application/pdf",use_container_width=True)

# ════════════════════════════════════════════════════════════════
# TAB 8 — AI ANALYSIS (Multi-provider, streaming)
# ════════════════════════════════════════════════════════════════
with tabs[7]:
    st.subheader(f"🤖 AI Analysis — {provider_name} / {model}")
    st.caption(
        "Extract specific pages (OCR for Bangla), then analyze with any AI provider. "
        "**No proxy needed** — Streamlit Python backend calls all APIs directly."
    )

    # Step 1
    st.markdown("#### Step 1 — Load text")
    if "shared_text" in st.session_state:
        st.success(f"✅ Loaded: **{st.session_state.get('shared_source','Extract tab')}**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear & load new", key="clr"):
                for k in ["shared_text","shared_source"]: st.session_state.pop(k, None)
                st.rerun()
        with col2:
            wc = len(st.session_state["shared_text"].split())
            st.markdown(f"<span style='color:#8892a4;font-size:13px;'>{wc:,} words</span>",
                        unsafe_allow_html=True)
    else:
        upl = st.file_uploader("Upload PDF for AI", type="pdf", key="ai_up")
        if upl:
            raw = upl.read(); total = get_pdf_page_count(raw)
            c1, c2 = st.columns([3,1])
            with c1: pg_input = st.text_input("📌 Pages", placeholder="e.g. 1-3 (empty=all)", key="aipg")
            with c2: st.metric("Pages", total)

            ai_ext = st.radio("Extraction", ["🚀 Native","🔍 OCR (Bangla/scanned)"],
                              horizontal=True, key="ai_ext")

            if st.button("📝 Extract for AI", use_container_width=True):
                idxs = parse_page_range(pg_input, total) if pg_input.strip() else list(range(total))
                bar = st.progress(0)
                if "OCR" in ai_ext:
                    if not OCR_OK:
                        st.error("❌ Tesseract not installed. See sidebar."); st.stop()
                    res = extract_text_ocr(raw, idxs, lang=ocr_lang_code, dpi=ocr_dpi)
                else:
                    res = extract_text_native(raw, idxs)
                parts = []
                for i, (pg_num, text) in enumerate(res):
                    parts.append(f"[Page {pg_num}]\n{text}")
                    bar.progress((i+1)/len(idxs))
                bar.empty()
                st.session_state["shared_text"] = "\n\n".join(parts)
                st.session_state["shared_source"] = (
                    f"{upl.name} — pages {pg_input or 'all'} "
                    f"[{'OCR' if 'OCR' in ai_ext else 'Native'}]"
                )
                st.success(f"✅ {len(idxs)} page(s) loaded. Scroll down.")
                st.rerun()

    # Step 2
    if "shared_text" in st.session_state:
        st.divider()
        st.markdown(f"#### Step 2 — Ask {provider_name}")

        with st.expander("📋 Preview extracted text"):
            prev = st.session_state["shared_text"]
            st.text(prev[:1500] + ("…" if len(prev) > 1500 else ""))

        preset = st.selectbox("Quick prompt templates", [
            "✏️ Custom question…",
            "Summarize this document in bullet points",
            "Extract all key facts, dates, numbers and names",
            "List all action items or tasks mentioned",
            "Identify the document type and purpose",
            "Translate the content to English",
            "Find any risks, issues or problems",
            "Write an executive summary (3-4 sentences)",
            "Extract all tables or structured data as markdown",
            "বাংলায় সারসংক্ষেপ করুন (Summarize in Bangla)",
            "মূল তথ্যগুলি বাংলায় তালিকা করুন (Key points in Bangla)",
        ])

        user_q = st.text_area(
            "Your question or instruction",
            value="" if preset == "✏️ Custom question…" else preset,
            height=110, key="ai_q"
        )

        if st.button("🤖 Analyze Now", type="primary", use_container_width=True):
            if not user_q.strip():
                st.error("Please enter a question or choose a template.")
            elif prov["needs_key"] and not api_key and prov_id != "ollama":
                st.error(f"❌ {provider_name} requires an API key in the sidebar.")
            else:
                text_content = st.session_state["shared_text"]
                MAX_CHARS = 80_000
                if len(text_content) > MAX_CHARS:
                    text_content = text_content[:MAX_CHARS]
                    st.warning(f"⚠️ Text truncated to {MAX_CHARS:,} chars. Extract fewer pages for full coverage.")

                system_prompt = (
                    "You are a precise and helpful PDF document analyst. "
                    "Analyze the provided text and respond with well-structured markdown. "
                    "Support Bangla text — respond in the same language as the user's instruction. "
                    "If the instruction is in Bangla, respond in Bangla."
                )

                st.markdown(f"**{provider_name} · {model}:**")
                try:
                    full_response = st.write_stream(
                        call_ai_stream(
                            prov_id, model, api_key,
                            system_prompt,
                            f"Document:\n\n{text_content}\n\n---\n\n{user_q}",
                            ollama_url=ollama_url,
                            max_tokens=max_tokens
                        )
                    )
                    if full_response:
                        st.download_button("📥 Save Analysis", full_response.encode("utf-8"),
                                           "ai_analysis.txt","text/plain",use_container_width=True)
                except Exception as e:
                    st.error(f"❌ {type(e).__name__}: {e}")
