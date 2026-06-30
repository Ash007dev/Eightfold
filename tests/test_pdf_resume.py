from pathlib import Path

from transformer.detect import detect_source
from transformer.extractors.resume import _read_text


ROOT = Path(__file__).resolve().parents[1]


def test_pdf_resume_is_detected_and_text_is_read() -> None:
    path = ROOT / "samples" / "candidate_pdf" / "resume.pdf"
    assert detect_source(path) == "resume"
    text = _read_text(path)
    assert "Mira Sharma PDF Resume" in text
    assert "mira.sharma@example.com" in text
