"""The unofficial LeetCode source must fail closed and leave the pipeline usable."""

from pathlib import Path

from transformer.__main__ import run_pipeline
from transformer.config import load_app_config
from transformer.evidence.leetcode import extract_username


class _Response500:
    status_code = 500
    text = "{}"

    def raise_for_status(self) -> None:
        raise RuntimeError("server error")


def test_leetcode_500_returns_empty(monkeypatch) -> None:
    def fake_post(*args, **kwargs):
        del args, kwargs
        return _Response500()

    monkeypatch.setattr("transformer.evidence.leetcode.requests.post", fake_post)
    config = load_app_config()
    assert extract_username("someone", config) == []


def test_pipeline_completes_with_bad_leetcode(tmp_path, monkeypatch) -> None:
    def fake_post(*args, **kwargs):
        del args, kwargs
        return _Response500()

    monkeypatch.setattr("transformer.evidence.leetcode.requests.post", fake_post)
    (tmp_path / "recruiter.csv").write_text(
        "name,email,phone,current_company,title\nLeela Shah,leela@example.com,+91 91234 56789,Acme,Engineer\n",
        encoding="utf-8",
    )
    (tmp_path / "leetcode.txt").write_text("leetcode-user", encoding="utf-8")
    output = run_pipeline(Path(tmp_path), Path("configs/default.json"))
    assert len(output) == 1
    assert output[0]["emails"] == ["leela@example.com"]
