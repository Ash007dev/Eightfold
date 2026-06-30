from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from transformer.config import load_app_config, load_projection_config
from transformer.extractors import extract_file
from transformer.merge import merge_observations
from transformer.models import Observation
from transformer.project import project_records


def _input_files(inputs: Path) -> list[Path]:
    if not inputs.exists():
        raise FileNotFoundError(f"inputs path does not exist: {inputs}")
    if inputs.is_dir():
        return sorted(path for path in inputs.iterdir() if path.is_file())
    if inputs.suffix.lower() == ".json":
        data = json.loads(inputs.read_text(encoding="utf-8"))
        files = data.get("files", data) if isinstance(data, dict) else data
        if not isinstance(files, list):
            raise ValueError("manifest must be a list or {\"files\": [...]}")
        base = inputs.parent
        return sorted((base / item).resolve() for item in files)
    return [inputs]


def collect_observations(inputs: Path) -> list[Observation]:
    app_config = load_app_config()
    observations: list[Observation] = []
    for path in _input_files(inputs):
        observations.extend(extract_file(path, app_config))
    return observations


def run_pipeline(inputs: Path, projection_config_path: Path | None = None) -> list[dict]:
    app_config = load_app_config()
    observations: list[Observation] = []
    for path in _input_files(inputs):
        observations.extend(extract_file(path, app_config))
    records = merge_observations(observations, app_config)
    projection_config = load_projection_config(projection_config_path)
    return project_records(records, projection_config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-source candidate data transformer")
    parser.add_argument("--inputs", required=True, type=Path, help="Input directory or manifest JSON")
    parser.add_argument("--config", type=Path, default=Path("configs/default.json"), help="Projection config path")
    parser.add_argument("--out", type=Path, help="Output JSON path")
    parser.add_argument("--explain", action="store_true", help="Print provenance and confidence breakdown to stderr")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output = run_pipeline(args.inputs, args.config)
    except Exception as exc:
        parser.error(str(exc))
        return 2

    rendered = json.dumps(output, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    if args.explain:
        print(rendered, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
