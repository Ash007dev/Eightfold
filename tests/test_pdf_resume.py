from pathlib import Path
import shutil

from transformer.detect import detect_source
from transformer.extractors import resume


ROOT = Path(__file__).resolve().parents[1]


def test_pdf_resume_is_detected_and_text_is_read() -> None:
    path = ROOT / "samples" / "candidate_pdf" / "resume.pdf"
    assert detect_source(path) == "resume"
    text = resume._read_text(path)
    assert "Mira Sharma PDF Resume" in text
    assert "mira.sharma@example.com" in text


def test_scanned_pdf_uses_ocr_fallback(monkeypatch) -> None:
    path = ROOT / "samples" / "candidate_pdf" / "scanned_resume.pdf"
    calls = {"count": 0}

    def fake_ocr_page(page) -> str:
        del page
        calls["count"] += 1
        return "Rohan Mehta Scanned Resume\nEmail: rohan.mehta@example.com"

    monkeypatch.setattr(resume, "_ocr_pdf_page", fake_ocr_page)
    text = resume._read_text(path)
    assert calls["count"] >= 1
    assert "rohan.mehta@example.com" in text


def test_scanned_pdf_real_ocr_when_tesseract_is_available() -> None:
    if shutil.which("tesseract") is None:
        return
    path = ROOT / "samples" / "candidate_pdf" / "scanned_resume.pdf"
    text = resume._read_text(path)
    assert "rohan" in text.lower()
