import io
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from docx import Document
from pypdf import PdfReader
from app.main import app
from app.models import Resume, EnhanceRequest
from app.parser import parse_resume
from app.analyzer import analyze, audit_proposals
from app.exporter import export_docx, export_pdf

client = TestClient(app)

SAMPLE = Resume(name="Alex Morgan",headline="Software Engineer",email="alex@example.com",
                sections={"summary":"Engineer experienced in Python and SQL.","experience":"Engineer at Example Co | 2023 - Present\n- Built Python REST APIs","skills":"Python, SQL, Git", "projects":"Inventory API built in Python"})
JD = "We're hiring a Python developer with REST API, Git, AWS, Docker, PostgreSQL and SQL skills for backend engineering."


def test_health():
    r=client.get('/api/health');assert r.status_code==200 and r.json()['ok']


def test_parse_plaintext():
    text="Alex Morgan\nalex@example.com\nProfessional Summary\nBackend engineer\nEXPERIENCE\nEngineer at Acme\n- Built APIs\nSkills\nPython, SQL"
    r=client.post('/api/parse',files={'file':('resume.txt',text.encode(),'text/plain')})
    assert r.status_code==200
    data=r.json()['resume']
    assert data['name']=='Alex Morgan' and data['email']=='alex@example.com'
    assert 'Engineer at Acme' in data['sections']['experience']
    assert 'Python' in data['sections']['skills']


def test_parse_docx():
    doc=Document();doc.add_paragraph('Alex Morgan');doc.add_paragraph('Experience');doc.add_paragraph('Software Engineer at Acme');doc.add_paragraph('Skills');doc.add_paragraph('Python and Git')
    io_=io.BytesIO();doc.save(io_)
    r=client.post('/api/parse',files={'file':('sample.docx',io_.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
    assert r.status_code==200 and 'Python' in r.json()['resume']['sections']['skills']


def test_validation_and_injection_protection():
    assert client.post('/api/parse',files={'file':('evil.exe',b'Not a supported file')}).status_code==400
    assert client.post('/api/parse',files={'file':('huge.txt',b'A'* (5*1024*1024+1))}).status_code in (400,413)
    assert 'script' not in parse_resume('Jane Doe\nExperience\nPython').sections


def test_analysis_only_reports_keyword_overlap():
    data=analyze(SAMPLE,JD)
    assert 'Python' in data['matched'] and 'Docker' in data['missing']
    assert data['score'] < 100 and data['score'] >= 0


def test_export_pdf_docx():
    for template in ('modern','classic','compact'):
        pdf=export_pdf(SAMPLE,template);assert pdf[:4]==b'%PDF'
        assert len(PdfReader(io.BytesIO(pdf)).pages)>=1
        word=export_docx(SAMPLE,template)
        d=Document(io.BytesIO(word))
        assert any('Alex Morgan' in p.text for p in d.paragraphs)
        assert any('REST APIs' in p.text for p in d.paragraphs)


def test_analyze_endpoint():
    res=client.post('/api/analyze',json={'resume':SAMPLE.model_dump(),'job_description':JD})
    assert res.status_code==200 and 'matched' in res.json()


def test_export_endpoint():
    res=client.post('/api/export',json={'resume':SAMPLE.model_dump(),'format':'pdf','template':'modern'})
    assert res.status_code==200 and res.content.startswith(b'%PDF')


def test_enhance_changes_only_selected_sections():
    req={'resume':SAMPLE.model_dump(),'job_description':JD,'sections_to_change':['summary'],'provider':'gemini'}
    with patch('app.main.improve',new_callable=AsyncMock,return_value={'summary':'Engineer skilled in Python and SQL.'}):
        r=client.post('/api/enhance',json=req)
    assert r.status_code==200
    assert r.json()['proposed_sections']=={'summary':'Engineer skilled in Python and SQL.'}
    assert r.json()['updated_alignment']['score']>=0


def test_invalid_section_rejected():
    req={'resume':SAMPLE.model_dump(),'job_description':JD,'sections_to_change':['contact'],'provider':'gemini'}
    assert client.post('/api/enhance',json=req).status_code==422


def test_risk_audit_detects_added_unverified_numbers_and_skills():
    warning=audit_proposals(SAMPLE,JD,{'summary':'Built Docker services for 50000 users, helping in Python.'})['summary']
    assert any('50000' in x for x in warning)
    assert any('Docker' in x for x in warning)
