"""Readable single-column resumes in selectable ATS-friendly styles."""
import io
import re
from xml.sax.saxutils import escape
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
from .models import Resume, SECTIONS

TITLES = {
    "summary": "PROFESSIONAL SUMMARY", "experience": "EXPERIENCE", "skills": "SKILLS",
    "projects": "PROJECTS", "education": "EDUCATION", "achievements": "ACHIEVEMENTS",
    "certifications": "CERTIFICATIONS", "additional": "ADDITIONAL INFORMATION",
}
ORDERS = ["summary", "skills", "experience", "projects", "education", "achievements", "certifications", "additional"]
THEMES = {
    "classic": {"accent": "252525", "font": "Times New Roman", "size": 10.5, "margin": 0.75},
    "modern": {"accent": "2456AB", "font": "Aptos", "size": 10.0, "margin": 0.72},
    "compact": {"accent": "384657", "font": "Arial", "size": 9.5, "margin": 0.62},
}


def clean_lines(text: str):
    return [line.strip() for line in text.splitlines() if line.strip()]


def is_bullet(line: str):
    return bool(re.match(r"^(?:[-*•–]|\d+[.)])\s+", line))


def strip_bullet(line: str) -> str:
    return re.sub(r"^(?:[-*•–]|\d+[.)])\s+", "", line)


def export_docx(resume: Resume, template: str) -> bytes:
    theme = THEMES[template]
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(theme["margin"])
    section.bottom_margin = Inches(theme["margin"])
    section.left_margin = Inches(theme["margin"])
    section.right_margin = Inches(theme["margin"])
    base = doc.styles["Normal"]
    base.font.name = theme["font"]
    base.font.size = Pt(theme["size"])
    base.paragraph_format.space_after = Pt(3 if template == "compact" else 5)
    base.paragraph_format.line_spacing = 1.07
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER if template == "classic" else WD_ALIGN_PARAGRAPH.LEFT
    run = title.add_run(resume.name or "Your Name")
    run.bold = True
    run.font.size = Pt(18 if template == "classic" else 21)
    run.font.color.rgb = RGBColor.from_string(theme["accent"])
    if resume.headline:
        p = doc.add_paragraph(resume.headline)
        p.alignment = title.alignment
        p.paragraph_format.space_after = Pt(3)
    contact = "  |  ".join(x for x in [resume.email, resume.phone, resume.location, resume.links] if x)
    if contact:
        p = doc.add_paragraph(contact)
        p.alignment = title.alignment
        p.paragraph_format.space_after = Pt(11)
        for r in p.runs:
            r.font.size = Pt(9)
    for key in ORDERS:
        content = resume.sections.get(key, "").strip()
        if not content:
            continue
        heading = doc.add_paragraph()
        heading.paragraph_format.space_before = Pt(12 if template != "compact" else 7)
        heading.paragraph_format.space_after = Pt(4)
        heading.paragraph_format.keep_with_next = True
        run = heading.add_run(TITLES[key])
        run.bold = True
        run.font.size = Pt(10.5)
        run.font.color.rgb = RGBColor.from_string(theme["accent"])
        for line in clean_lines(content):
            bullet = is_bullet(line)
            p = doc.add_paragraph(style="List Bullet" if bullet else "Normal")
            p.add_run(strip_bullet(line) if bullet else line)
            p.paragraph_format.space_after = Pt(2 if bullet else 4)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def export_pdf(resume: Resume, template: str) -> bytes:
    theme = THEMES[template]
    accent = colors.HexColor("#" + theme["accent"])
    out = io.BytesIO()
    margin = theme["margin"] * 72
    doc = SimpleDocTemplate(out, pagesize=letter, leftMargin=margin, rightMargin=margin,
                            topMargin=margin, bottomMargin=margin,
                            title=(resume.name or "Resume") + " - Resume")
    base = ParagraphStyle("Body", fontName="Helvetica" if template != "classic" else "Times-Roman",
                          fontSize=theme["size"], leading=theme["size"] * 1.36, spaceAfter=3)
    name_style = ParagraphStyle("Name", parent=base, fontName="Helvetica-Bold" if template != "classic" else "Times-Bold",
                                fontSize=20 if template != "compact" else 18, leading=24, textColor=accent,
                                alignment=TA_CENTER if template == "classic" else TA_LEFT, spaceAfter=5)
    small = ParagraphStyle("Small", parent=base, fontSize=9, leading=12,
                           alignment=TA_CENTER if template == "classic" else TA_LEFT, spaceAfter=7)
    head = ParagraphStyle("Head", parent=base, fontName="Helvetica-Bold" if template != "classic" else "Times-Bold",
                          fontSize=10.5, leading=13, textColor=accent,
                          spaceBefore=11 if template != "compact" else 7, spaceAfter=5, keepWithNext=True)
    bullet_style = ParagraphStyle("Bullet", parent=base, leftIndent=12, firstLineIndent=-9, spaceAfter=2)
    body = [Paragraph(escape(resume.name or "Your Name"), name_style)]
    if resume.headline:
        body.append(Paragraph(escape(resume.headline), small))
    contact = "  |  ".join(x for x in [resume.email, resume.phone, resume.location, resume.links] if x)
    if contact:
        body.append(Paragraph(escape(contact), small))
    body.append(Spacer(1, 6))
    for key in ORDERS:
        content = resume.sections.get(key, "").strip()
        if not content:
            continue
        body.append(Paragraph(TITLES[key], head))
        for line in clean_lines(content):
            if is_bullet(line):
                body.append(Paragraph("&#8226; " + escape(strip_bullet(line)), bullet_style))
            else:
                body.append(Paragraph(escape(line), base))
    doc.build(body)
    return out.getvalue()
