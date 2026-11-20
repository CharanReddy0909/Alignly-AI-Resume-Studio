"""Extract and retain all recognizable resume sections without an LLM."""
import io
import re
from pathlib import Path
from docx import Document
from pypdf import PdfReader
from .models import Resume, SECTIONS

MAX_UPLOAD = 5 * 1024 * 1024
MAX_PAGES = 20
ALIASES = {
    "summary": ["professional summary", "executive summary", "profile summary", "career summary", "about me", "summary", "profile", "objective"],
    "experience": ["professional experience", "employment history", "work experience", "relevant experience", "career history", "experience", "employment"],
    "skills": ["technical skills", "core competencies", "areas of expertise", "technologies", "tools & technologies", "key skills", "skills"],
    "projects": ["professional projects", "personal projects", "key projects", "selected projects", "projects"],
    "education": ["academic qualifications", "educational background", "education", "academics"],
    "achievements": ["awards and achievements", "achievements", "honors and awards", "awards", "accomplishments", "honors"],
    "certifications": ["licenses and certifications", "certifications", "certificates", "licenses"],
    "additional": ["additional information", "volunteering", "publications", "languages", "interests", "other information"],
}
ALL_ALIASES = {re.sub(r"\s+", " ", x).lower(): k for k, aliases in ALIASES.items() for x in aliases}
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
URL_RE = re.compile(r"(?:https?://|www\.|linkedin\.com/|github\.com/)[^\s|,;]+", re.I)


def read_upload(filename: str, data: bytes) -> str:
    if not data:
        raise ValueError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD:
        raise ValueError("Maximum file size is 5 MB.")
    ext = Path(filename).suffix.lower()
    if ext in {".txt", ".md"}:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("cp1252", errors="replace")
    elif ext == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ValueError("Password-protected PDFs are not supported. Please unlock the file first.")
            if len(reader.pages) > MAX_PAGES:
                raise ValueError(f"PDF files are limited to {MAX_PAGES} pages.")
            text = "\n".join((p.extract_text(extraction_mode="layout") or "") for p in reader.pages)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Could not read this PDF. Try exporting it again as a text PDF.") from exc
    elif ext == ".docx":
        try:
            doc = Document(io.BytesIO(data))
            blocks = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    cells = [cell.text.strip().replace("\n", " / ") for cell in row.cells if cell.text.strip()]
                    if cells:
                        blocks.append(" | ".join(cells))
            text = "\n".join(blocks)
        except Exception as exc:
            raise ValueError("Could not read this Word document. Please upload a valid .docx file.") from exc
    else:
        raise ValueError("Use a .pdf, .docx, .txt, or .md file.")
    text = text.replace("\x00", "").strip()
    if len(text) < 15:
        raise ValueError("No selectable text was found. Scanned/image-only PDFs require OCR; please upload a text-based resume.")
    return text[:80000]


def identify_heading(line: str) -> str | None:
    normalized = re.sub(r"\s+", " ", line.strip().strip("#:-–—_ |\t•"))
    if not normalized or len(normalized) > 55:
        return None
    return ALL_ALIASES.get(normalized.lower())


def parse_resume(text: str) -> Resume:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.replace("\r", "").splitlines()]
    header, sections = [], {key: [] for key in SECTIONS}
    current = None
    for line in lines:
        heading = identify_heading(line)
        if heading:
            current = heading
            continue
        if current is None:
            header.append(line)
        else:
            sections[current].append(line)
    header_lines = [line for line in header if line]
    full_header = " | ".join(header_lines[:12])
    email_match = EMAIL_RE.search(full_header)
    phone_match = PHONE_RE.search(full_header)
    url_matches = URL_RE.findall(full_header)
    name = next((l for l in header_lines[:5] if not EMAIL_RE.search(l) and not PHONE_RE.fullmatch(l) and not URL_RE.search(l) and len(l) <= 85), "")
    headline = ""
    if name:
        ix = header_lines.index(name)
        if ix + 1 < len(header_lines):
            candidate = header_lines[ix + 1]
            if len(candidate) <= 85 and not EMAIL_RE.search(candidate) and not PHONE_RE.search(candidate):
                headline = candidate
    location = ""
    # Recognize locations only when explicitly labeled; don't guess based on delimiters.
    location_match = re.search(r"(?:location|address)\s*:\s*([^|\n]{2,80})", full_header, re.I)
    if location_match:
        location = location_match.group(1).strip()
    # Keep unrecognized header text rather than silently discarding it.
    used_header = {name, headline}
    extras = [l for l in header_lines if l not in used_header and not EMAIL_RE.search(l) and not URL_RE.search(l) and not PHONE_RE.search(l)]
    if extras:
        sections["additional"] = extras + sections["additional"]
    # If a file has no standard headings, preserve source text in experience for manual reassignment.
    if not any(sections.values()):
        sections["experience"] = lines[len(header):] or lines
    return Resume(
        name=name, headline=headline,
        email=email_match.group() if email_match else "",
        phone=phone_match.group().strip() if phone_match else "",
        location=location,
        links=" | ".join(url_matches),
        sections={k: "\n".join(v).strip() for k, v in sections.items()},
    )
