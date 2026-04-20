
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
