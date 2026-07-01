#!/usr/bin/env bash
set -euo pipefail

mkdir -p out
python -m transformer --inputs samples/candidate_01 --config configs/default.json       --out out/candidate_01.default.json
python -m transformer --inputs samples/candidate_01 --config configs/custom_example.json --out out/candidate_01.custom.json
python -m pytest -q

echo "Wrote out/candidate_01.default.json and out/candidate_01.custom.json"
