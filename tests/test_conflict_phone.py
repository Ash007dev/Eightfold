from pathlib import Path

from transformer.__main__ import run_pipeline


ROOT = Path(__file__).resolve().parents[1]


def test_conflicting_phones_are_normalized_ordered_and_provenanced() -> None:
    output = run_pipeline(ROOT / "samples" / "candidate_01", ROOT / "configs" / "default.json")
    record = output[0]
    assert record["phones"] == ["+919988776655", "+919876543210"]
    phone_values = {
        row["value"]
        for row in record["provenance"]
        if row["field"] == "phones"
    }
    assert {"+919988776655", "+919876543210"} <= phone_values
