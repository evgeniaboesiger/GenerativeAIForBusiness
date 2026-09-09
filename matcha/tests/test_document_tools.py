"""
MATCHA - Automated tests for the document-processing tool used by the
Profile Agent.

Covers: fast PDF text extraction, OCR fallback for image-based (scanned)
PDFs, heuristic for insufficient text, graceful behaviour when the OCR
engine is missing, and ProfileAgent.extract_profile_from_document().

OCR is tested with an injected fake engine, so the tests do NOT require the
Tesseract binary to be installed.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))

from document_tools import CVTextResult, OCREngine, extract_cv_text, is_insufficient  # noqa: E402
from profile_agent import ProfileAgent  # noqa: E402

pymupdf = pytest.importorskip("pymupdf")


# ---------------------------------------------------------------------- #
#  PDF fixtures built with PyMuPDF (no reportlab needed)
# ---------------------------------------------------------------------- #
FAKE_CV = """ANNA WEBER
Data Analyst
Bern
anna.weber@example.com +41 76 555 12 12

SUMMARY
Data analyst with 4 years of experience in Power BI, SQL and Python.

EXPERIENCE
Senior Data Analyst, BKW Energie, Bern, 2022 - Present
Power BI dashboards, SQL queries, Python automation.

EDUCATION
Master of Science, Business Analytics, University of Bern, 2018 - 2020
Bachelor of Science, Economics, University of Basel, 2014 - 2017

SKILLS
Power BI, SQL, Python, Tableau, Data Analysis

LANGUAGES
German (native), English (fluent), French (intermediate)

CERTIFICATIONS
Microsoft Power BI Data Analyst
"""


def make_text_pdf(body):
    """A normal PDF with a real text layer (extracts fine)."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), body, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def make_scan_pdf():
    """An image-only PDF with no text layer (needs OCR)."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.draw_rect(pymupdf.Rect(0, 0, 595, 842), color=(1, 1, 1), fill=(0.92, 0.92, 0.92))
    data = doc.tobytes()
    doc.close()
    return data


class FakeOCR:
    """Deterministic fake OCR engine so tests don't need Tesseract."""

    def __init__(self, output):
        self.output = output
        self.calls = 0

    def available(self):
        return True

    def pdf_to_text(self, data):
        self.calls += 1
        return self.output


# ---------------------------------------------------------------------- #
#  is_insufficient heuristic
# ---------------------------------------------------------------------- #
def test_is_insufficient_empty():
    assert is_insufficient("") is True
    assert is_insufficient(None) is True


def test_is_insufficient_short_garbage():
    assert is_insufficient("Sophie M\xfcller Software 078 123 45 67") is True


def test_is_insufficient_realistic_cv():
    assert is_insufficient(FAKE_CV) is False


# ---------------------------------------------------------------------- #
#  Fast text extraction (txt / docx)
# ---------------------------------------------------------------------- #
def test_extract_txt():
    result = extract_cv_text(b"Hello CV\nSecond line", "cv.txt")
    assert result.source == "txt"
    assert result.text == "Hello CV\nSecond line"


def test_extract_txt_fallback_encoding():
    result = extract_cv_text(b"\xff\xfe garbled", "cv.txt")
    assert result.source == "txt"


def test_extract_unsupported_type():
    result = extract_cv_text(b"data", "resume.odt")
    assert result.source == "unsupported"
    assert result.text == ""


def test_extract_docx():
    from docx import Document

    buffer = os.path.join(os.path.dirname(__file__), "sample.docx")
    doc = Document()
    doc.add_paragraph("LUKAS MEIER - Business Analyst")
    doc.save(buffer)
    try:
        with open(buffer, "rb") as fh:
            data = fh.read()
        result = extract_cv_text(data, "cv.docx")
        assert result.source == "docx"
        assert "LUKAS MEIER" in result.text
    finally:
        os.remove(buffer)


# ---------------------------------------------------------------------- #
#  PDF: fast path vs OCR fallback
# ---------------------------------------------------------------------- #
def test_pdf_text_fast_path():
    engine = FakeOCR("should not be called")
    result = extract_cv_text(make_text_pdf(FAKE_CV), "anna.pdf", ocr_engine=engine)
    assert result.source == "pdf_text"
    assert "ANNA WEBER" in result.text
    assert engine.calls == 0


def test_pdf_scanned_uses_ocr_fallback():
    engine = FakeOCR(FAKE_CV)
    result = extract_cv_text(make_scan_pdf(), "anna.pdf", ocr_engine=engine)
    assert result.source == "pdf_ocr"
    assert "ANNA WEBER" in result.text
    assert result.ocr_used is True
    assert engine.calls == 1


def test_pdf_ocr_missing_engine():
    class UnavailableEngine:
        def available(self) -> bool:
            return False

    result = extract_cv_text(make_scan_pdf(), "anna.pdf", ocr_engine=UnavailableEngine())
    # OCR engine unavailable -> reported clearly instead of misreporting.
    assert result.source == "pdf_ocr_missing"
    assert result.text == ""


def test_pdf_ocr_result_too_weak_keeps_fast_text():
    engine = FakeOCR("")
    result = extract_cv_text(make_scan_pdf(), "anna.pdf", ocr_engine=engine)
    assert result.source == "pdf_text"
    assert result.text == ""


def test_force_ocr_triggers_even_when_text_sufficient():
    engine = FakeOCR(FAKE_CV)
    result = extract_cv_text(make_text_pdf(FAKE_CV), "anna.pdf", force_ocr=True, ocr_engine=engine)
    assert result.source == "pdf_ocr"
    assert engine.calls == 1


# ---------------------------------------------------------------------- #
#  ProfileAgent integration (OCR as a tool of the Profile Agent)
# ---------------------------------------------------------------------- #
def test_profile_agent_extract_from_text_pdf():
    agent = ProfileAgent()
    profile, meta = agent.extract_profile_from_document(make_text_pdf(FAKE_CV), "anna.pdf")
    assert meta["text_source"] == "pdf_text"
    assert meta["ocr_used"] is False
    assert meta["characters"] > 0
    assert "ANNA" in profile["personal_info"]["name"].upper()


def test_profile_agent_extract_from_scanned_pdf():
    agent = ProfileAgent()
    profile, meta = agent.extract_profile_from_document(
        make_scan_pdf(), "anna.pdf", ocr_engine=FakeOCR(FAKE_CV))
    assert meta["text_source"] == "pdf_ocr"
    assert meta["ocr_used"] is True
    assert "ANNA" in profile["personal_info"]["name"].upper()
    assert "weber" in profile["personal_info"]["email"]


# ---------------------------------------------------------------------- #
#  Tesseract binary resolution
# ---------------------------------------------------------------------- #
def test_resolve_tesseract_cmd_uses_path(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/tesseract")
    assert OCREngine._resolve_tesseract_cmd() == "/usr/bin/tesseract"


def test_resolve_tesseract_cmd_uses_standard_windows_path(monkeypatch):
    exe = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setattr("os.path.isfile", lambda p: p == exe)
    assert OCREngine._resolve_tesseract_cmd() == exe


def test_resolve_tesseract_cmd_falls_back_to_bare_command(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setattr("os.path.isfile", lambda _p: False)
    assert OCREngine._resolve_tesseract_cmd() == "tesseract"