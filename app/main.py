import os
from io import BytesIO
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from .models import AnalysisRequest, EnhanceRequest, ExportRequest
from .parser import MAX_UPLOAD, parse_resume, read_upload
from .analyzer import analyze, audit_proposals
from .llm import improve
from .exporter import export_docx, export_pdf

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
app = FastAPI(title="Alignly Resume Studio", version="1.0.0", docs_url="/api/docs")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")


@app.get("/")
async def home():
    return FileResponse(ROOT / "app" / "static" / "index.html")


@app.get("/api/health")
async def health():
    return {"ok": True, "gemini_configured": bool(os.getenv("GEMINI_API_KEY", "").strip()),
            "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
            "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.2:3b")}


@app.post("/api/parse")
async def parse(file: UploadFile = File(...)):
    if file.size is not None and file.size > MAX_UPLOAD:
        raise HTTPException(413, detail="Maximum upload size is 5 MB.")
    data = await file.read(MAX_UPLOAD + 1)
    try:
        text = read_upload(file.filename or "", data)
        resume = parse_resume(text)
        return {"resume": resume.model_dump(), "characters": len(text)}
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc


@app.post("/api/extract-jd")
async def extract_jd(file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD + 1)
    try:
        return {"text": read_upload(file.filename or "", data)[:60000]}
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc


@app.post("/api/analyze")
async def get_analysis(req: AnalysisRequest):
    return analyze(req.resume, req.job_description)


@app.post("/api/enhance")
async def enhance(req: EnhanceRequest):
    result = await improve(req)
    new_resume = req.resume.model_copy(deep=True)
    new_resume.sections.update(result)
    return {"proposed_sections": result, "risk_warnings": audit_proposals(req.resume, req.job_description, result), "updated_alignment": analyze(new_resume, req.job_description),
            "reminder": "AI suggestions can be inaccurate. Review every change before accepting or exporting."}


@app.post("/api/export")
async def export(req: ExportRequest):
    data = export_pdf(req.resume, req.template) if req.format == "pdf" else export_docx(req.resume, req.template)
    stem = "".join(c for c in (req.resume.name or "My_Resume").replace(" ", "_") if c.isalnum() or c in "_- ")[:70] or "Resume"
    fname = f"{stem}_{req.template}.{req.format}"
    mediatype = ("application/pdf" if req.format == "pdf" else
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    return StreamingResponse(BytesIO(data), media_type=mediatype,
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})
