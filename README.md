# Alignly — AI Resume Studio

A complete, **Cursor-ready** web application that tailors an existing resume to a job description, or builds a resume through an interactive questionnaire. Designed for local development with a modern responsive frontend, Python/FastAPI backend, and three ATS-readable PDF/DOCX export themes.

**No Node.js build step required.** Gemini is optional: you can use Gemini's limited free API tier, or Ollama on your own laptop. Without either model, the parser, live editor, questionnaire builder, keyword analysis and PDF/DOCX exports still work.

## Start in Cursor (Windows)

1. Extract the ZIP and use **Cursor → File → Open Folder → `Alignly_Resume_Studio`**.
2. Install [Python 3.10+](https://www.python.org/downloads/) if needed; when installing on Windows, enable **Add Python to PATH**.
3. Double-click **`start_windows.bat`** (or open Cursor's integrated terminal and run `./start_windows.bat`). This creates `.venv` and installs dependencies on the first run.
4. Visit **http://127.0.0.1:8000**.
5. Optional AI: open `.env` (automatically copied from `.env.example`) and set `GEMINI_API_KEY=YOUR_KEY`, then stop and restart the server. Obtain an API key from [Google AI Studio](https://aistudio.google.com/apikey).

### PowerShell manual setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and optionally add GEMINI_API_KEY
.\.venv\Scripts\python.exe run.py
```

### Mac / Linux

```bash
./start_mac_linux.sh
# or: python3 -m venv .venv; source .venv/bin/activate; pip install -r requirements.txt; python run.py
```

## AI choices

| Provider | Setup | Cost / tradeoff |
| --- | --- | --- |
| **Gemini (default)** | Create Google AI Studio API key; add to `.env`; restart | Selected Gemini models have limited **free-tier usage**, subject to eligibility, quotas and Google's terms. Requests leave your machine and free-tier content may be used to improve Google's products. |
| **Ollama** | Install [Ollama](https://ollama.com/download), run `ollama pull llama3.2:3b`, keep it running, select Ollama | No per-token cloud API charge; uses local RAM/CPU/GPU and works only while your host runs. The local server must be reachable at `OLLAMA_URL`. |

Default model names live in `.env`: `GEMINI_MODEL=gemini-2.5-flash-lite`, `OLLAMA_MODEL=llama3.2:3b`. They can be changed to other models you have access to. If an API request fails due to quota/model access, choose another available model, check the key, or use Ollama. **API keys must stay server-side; do not commit `.env` to GitHub.**

Current Gemini model pricing / free-tier details: https://ai.google.dev/gemini-api/docs/pricing

## Use the app

**Tailor existing resume**
1. Upload your PDF, DOCX, TXT, or Markdown resume, or select **Try sample** to explore a fictional profile. Resume parsing is heuristic; open **Edit** to verify any imported details.
2. Paste a job description or upload a document.
3. Select **exactly which sections may change**: summary, experience, skills, projects, education, achievements, certifications, additional info. Contact details are never auto-rewritten.
4. Run **Analyze keyword match** for a free, transparent heuristic. Missing keywords indicate text not found in the resume, **not** skills you necessarily have.
5. Choose Gemini or Ollama and **Generate tailored draft**. Review side-by-side original/proposed sections and automatic flags for new numbers or unsupported keywords, then **Accept edit** or **Keep original** for each. You can also provide custom rewrite directions.
6. Select Modern, Classic, or Compact and export **PDF** or **DOCX**. The live editor lets you edit all fields before exporting.

**Build a resume from scratch**
1. Open **Build from scratch**, select a template and answer eight progressive questionnaires.
2. Enter verified facts about your contact info, summary, job history, skills, projects, education, achievements/certifications and additional details. The resume preview updates while you type.
3. Finish to create the resume, edit it, or tailor it against a specific job description.

**Saved versions**
- Click **Save version** to store a snapshot in **your browser's localStorage**. Snapshots are not synced across computers or browsers and can be deleted from **AI setup & privacy**.
- Open **Saved versions** to restore, delete, or **export JSON backup** for a snapshot. A maximum of 20 are kept. Refreshing the page without saving a version discards unsaved work.

## Features / architecture

- `app/main.py` — FastAPI routes, minimal stateless document handling
- `app/parser.py` — text extraction for PDF (pypdf), Word (python-docx), TXT and MD; section normalization
- `app/analyzer.py` — transparent keyword-overlap analysis; **not** a real ATS ranking predictor
- `app/llm.py` — Gemini via Google’s REST API and Ollama via its local HTTP API; requests explicitly limit edits to selected sections; structured JSON responses; candidate details and unselected sections stay unchanged
- `app/exporter.py` — ATS-friendly single-column PDF (ReportLab) and editable Word (python-docx) exports
- `app/static/` — responsive, zero-build HTML/CSS/vanilla JS frontend
- `tests/` — automated backend checks

Run tests from the project folder:

```bash
.venv/Scripts/python.exe -m pytest -q   # Windows
# or: .venv/bin/python -m pytest -q     # Mac/Linux
```

If `pytest` isn't installed, run `.venv/Scripts/python.exe -m pip install pytest` first. Tests never call paid AI APIs.

## Important accuracy, privacy, and product limitations

- **AI suggestions can be wrong.** Always verify companies, achievements, dates, skills and quantities. The AI prompt forbids inventions but cannot guarantee them. Accepting a suggestion is your decision.
- A percentage displayed for keyword alignment represents only *job-description keyword overlap*. It is **not** an ATS scan, job match probability, or guarantee of interview.
- This is a **local-first developer app, not a production multi-user SaaS**. It has no logins, user database, audit trail, abuse controls, or rate limits. Before exposing it on a public internet endpoint, add authentication, per-user quota limits, TLS, robust file validation and privacy disclosures, operational logging without personal data, and a secure deployment model.
- Uploaded files must contain selectable text. **Scanned/image-only PDFs do not undergo OCR**; convert them to searchable documents first. Complex Word tables or elaborate PDFs may need manual correction.
- The app does not intentionally persist resume uploads on the server. Session contents are held in your browser and sent to the backend when you request processing; Gemini requests pass resume and JD text to Google's API. Locally stored versions remain until you delete them or clear browser storage.
- Ollama runs on the same machine as the backend by default. If you shut off the machine hosting the app/model, a hosted frontend cannot continue calling that local model.

## Troubleshooting

- **Module not found**: use the `.venv` Python interpreter and run `pip install -r requirements.txt`.
- **Cannot reach localhost**: start `python run.py` and keep its terminal open; check that port 8000 is free.
- **Gemini key missing**: add `GEMINI_API_KEY` to `.env` at the project root (no extra spaces around the `=`), then restart.
- **Gemini 429/quota/model issue**: check Google AI Studio quotas and model availability; free access is limited and can vary by account/region.
- **Cannot connect to Ollama**: ensure Ollama is running and the chosen model is downloaded; optionally set `OLLAMA_URL` and `OLLAMA_MODEL` in `.env`.
- **PDF import empty**: scanned PDFs need OCR externally; the built-in parser reads only selectable text.

---
Built for learning, portfolio demonstrations, and responsible personal use.
