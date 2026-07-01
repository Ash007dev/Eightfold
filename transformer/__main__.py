from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from transformer.config import AppConfig, load_app_config, load_projection_config
from transformer.confidence import score_from_provenance
from transformer.extractors import extract_file
from transformer.llm import LLMClient
from transformer.merge import merge_observations
from transformer.models import CanonicalRecord, Observation
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


def build_records(inputs: Path, app_config: AppConfig | None = None) -> list[CanonicalRecord]:
    app_config = app_config or load_app_config()
    observations: list[Observation] = []
    for path in _input_files(inputs):
        observations.extend(extract_file(path, app_config))
    return merge_observations(observations, app_config)


def run_pipeline(inputs: Path, projection_config_path: Path | None = None) -> list[dict]:
    records = build_records(inputs)
    projection_config = load_projection_config(projection_config_path)
    return project_records(records, projection_config)


def _explain_records(records: list[CanonicalRecord]) -> str:
    lines: list[str] = []
    for record in records:
        lines.append(f"candidate_id={record.candidate_id} overall_confidence={record.overall_confidence}")
        for skill in record.skills:
            entries = [row for row in record.provenance if row.field == "skills" and row.value == skill.name]
            _, breakdown = score_from_provenance(entries)
            methods = sorted({row.method for row in entries})
            sources = sorted({row.source for row in entries})
            lines.append(
                f"skill={skill.name} confidence={skill.confidence} sources={sources} methods={methods} breakdown={breakdown}"
            )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-source candidate data transformer")
    parser.add_argument("--inputs", type=Path, help="Input directory or manifest JSON")
    parser.add_argument("--config", type=Path, default=Path("configs/default.json"), help="Projection config path")
    parser.add_argument("--out", type=Path, help="Output JSON path")
    parser.add_argument("--explain", action="store_true", help="Print provenance and confidence breakdown to stderr")
    parser.add_argument("--check-llm", action="store_true", help="Probe configured LLM credentials/model and print OK or the exact error")
    parser.add_argument("--batch", action="store_true", help="Treat --inputs as a directory of per-candidate subfolders")
    parser.add_argument("--stats", action="store_true", help="Print batch stats to stderr")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.check_llm:
        ok, message = LLMClient(load_app_config()).selftest()
        print(message)
        return 0 if ok else 1
    if args.inputs is None:
        parser.error("--inputs is required unless --check-llm is used")
        return 2
    try:
        records: list[CanonicalRecord] = []
        stats: dict | None = None
        if args.batch:
            from transformer.batch import run_batch

            output, stats = run_batch(args.inputs, args.config)
        else:
            app_config = load_app_config()
            records = build_records(args.inputs, app_config)
            projection_config = load_projection_config(args.config)
            output = project_records(records, projection_config)
    except Exception as exc:
        parser.error(str(exc))
        return 2

    rendered = json.dumps(output, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    if args.stats and stats is not None:
        print(json.dumps(stats, sort_keys=True), file=sys.stderr)
    if args.explain:
        print(_explain_records(records), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
