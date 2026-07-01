"""Batch mode proves multiple candidate folders run independently and robustly."""

from pathlib import Path

from transformer.batch import run_batch


ROOT = Path(__file__).resolve().parents[1]


def test_batch_returns_profiles_and_stats_for_subfolders(tmp_path) -> None:
    for name in ("cand_01", "cand_02"):
        src = ROOT / "samples" / "batch10" / name
        dst = tmp_path / name
        dst.mkdir()
        for file_path in src.iterdir():
            dst.joinpath(file_path.name).write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")

    profiles, stats = run_batch(tmp_path, ROOT / "configs" / "default.json")
    assert stats["candidates"] == 2
    assert stats["profiles"] == len(profiles)
    assert len(profiles) == 2


def test_batch_dedup_folder_normalizes_phone_and_resolves_company() -> None:
    profiles, _ = run_batch(ROOT / "samples" / "batch10", ROOT / "configs" / "default.json")
    asha = next(profile for profile in profiles if profile["full_name"] == "Asha Mehta")
    assert asha["phones"] == ["+919876543210"]
    assert all(phone.startswith("+") for phone in asha["phones"])
    assert asha["experience"][0]["company"] == "Vector Labs ATS"


def test_batch_homonym_folders_stay_distinct() -> None:
    profiles, _ = run_batch(ROOT / "samples" / "batch10", ROOT / "configs" / "default.json")
    sams = [profile for profile in profiles if profile["full_name"] == "Sam Patel"]
    assert len(sams) == 2
    assert sorted(profile["emails"][0] for profile in sams) == ["sam.backend@example.com", "sam.data@example.com"]
