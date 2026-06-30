# Multi-Source Candidate Data Transformer

<p>
  <img alt="Python 3.11" src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="CLI" src="https://img.shields.io/badge/Surface-CLI-111111?style=for-the-badge">
  <img alt="OpenAI" src="https://img.shields.io/badge/LLM-OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white">
  <img alt="SQLite cache" src="https://img.shields.io/badge/Cache-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white">
  <img alt="Pydantic" src="https://img.shields.io/badge/Schema-Pydantic-E92063?style=for-the-badge">
  <img alt="Pytest" src="https://img.shields.io/badge/Tests-Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white">
</p>

A deterministic Python CLI for the Eightfold multi-source candidate transformer assignment. It ingests messy candidate data from ATS JSON, recruiter CSV, resumes, notes, GitHub, and LeetCode evidence, then emits one canonical, deduplicated, provenance-tracked, confidence-scored JSON profile per candidate.

The important design split is:

```text
canonical record != emitted output
```

The merge layer builds the full internal `CanonicalRecord`. The projection layer in `transformer/project.py` is the only output producer, and even the default output shape is just `configs/default.json`.

## Quick Start

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env

python -m transformer --inputs samples\candidate_01 --config configs\default.json
python -m transformer --inputs samples\candidate_01 --config configs\custom_example.json

python -m pytest -q
```

Or run the demo script:

```powershell
.\demo.ps1
```

The repo includes `.cache/responses.db`, pre-seeded with content-hash responses for the sample OpenAI and GitHub calls. The demo and tests run offline and deterministically.

## Architecture

```mermaid
flowchart LR
  A[Input folder or manifest] --> B[detect.py]
  B --> C[Extractors]
  C --> D[Observation list]
  D --> E[normalize.py + skills.py]
  E --> F[merge.py identity + conflicts]
  F --> G[confidence.py scoring]
  G --> H[CanonicalRecord]
  H --> I[project.py config projection]
  I --> J[validate.py]
  J --> K[Sorted JSON output]

  C --> C1[CSV / ATS exact]
  C --> C2[Resume / notes OpenAI extraction]
  C --> C3[GitHub authored repo evidence]
  C --> C4[LeetCode language cross-check]
```

```mermaid
flowchart TD
  R[CanonicalRecord] --> P1[configs/default.json]
  R --> P2[configs/custom_example.json]
  R --> P3[Any runtime config]
  P1 --> O1[Full profile JSON]
  P2 --> O2[Remapped compact JSON]
  P3 --> O3[No code-change output shape]
```

## What It Supports

| Source | Status | How it is used |
|---|---|---|
| Recruiter CSV | Supported | Exact structured observations. |
| ATS JSON | Supported | Explicit field remap for renamed source fields. |
| Resume TXT/PDF/DOCX | Supported | OpenAI proposes JSON; validators decide what enters the record. |
| Scanned PDF resume | Supported | OCR fallback through `pytesseract` and local Tesseract. |
| Recruiter notes | Supported | Weak free-text skill/seniority hints. |
| GitHub profile | Supported | Authored commits gate strong language evidence. |
| GitHub repo files | Supported | Weak "project uses X" evidence, tiered by taxonomy. |
| GitHub topics | Supported | Weak skill hints only. |
| LeetCode | Supported | Language cross-check through the public GraphQL endpoint; failures return no evidence. |

## Evidence Model

The confidence score is a pure function of provenance rows and recorded signals. No LLM decides identity, winners, or scores.

| Evidence | Score delta |
|---|---:|
| Present in one source | `+3` |
| Present in 2+ independent sources | `+2` |
| GitHub authored language evidence | `+3` |
| LeetCode solved-language evidence and claimed elsewhere | `+2` |
| GitHub file signal in infra, CI/CD, DB/API, or framework tier | `+1` |
| Ownership file confirms login in `.mailmap`, `AUTHORS`, `CONTRIBUTORS`, `CODEOWNERS`, or `CITATION.cff` | `+1` |
| Recent repo activity relative to deterministic `RECENCY_AS_OF` | `+0.5` |
| Stars present across authored repos | `+0.25` |
| Only weak uncorroborated evidence | `-1` |
| Tooling-only file signal, such as `tsconfig.json` | `0 skill credit` |

File signals are intentionally conservative. A Dockerfile means "project uses Docker", not "expert in Docker". Topics, stars, and recency can corroborate or break ties, but they do not create top skills by themselves.

## OpenAI Routing

The LLM wrapper has two deterministic cloud tiers:

| Tier | Config | Used for |
|---|---|---|
| Strong | `LLM_MODEL=gpt-5.5` | Resume and notes extraction. |
| Cheap | `LLM_MODEL_CHEAP=gpt-5.4-mini` | Low-stakes triage, such as choosing which authored GitHub repos to deep-scan. |

Both tiers use temperature `0`, JSON-only prompts, and SQLite content-hash caching. Routing chooses only which model runs or which repos are inspected; validators, merge rules, and confidence scoring remain deterministic.

## PDF And OCR Resumes

Drop a resume PDF into any input folder:

```text
my_candidate/
  ats.json
  recruiter.csv
  resume.pdf
  notes.txt
  github.txt
```

Run:

```powershell
python -m transformer --inputs my_candidate --config configs\default.json
```

Text-based PDFs are read with `pdfplumber`. Scanned/image-only PDFs use OCR through `pytesseract`, which also needs the Tesseract OCR program installed.

```powershell
winget install UB-Mannheim.TesseractOCR
python -m pip install -r requirements.txt
```

If OCR tooling is missing, scanned pages safely contribute no resume text instead of crashing the run.

## Config

`.env.example` contains every runtime knob:

```env
LLM_PROVIDER=OpenAI
LLM_MODEL=gpt-5.5
LLM_MODEL_CHEAP=gpt-5.4-mini
LLM_TEMPERATURE=0
DEFAULT_REGION=IN
MAX_REPOS=30
MAX_FILES_TO_READ=10
RECENCY_DAYS=365
RECENCY_AS_OF=
GITHUB_TOKEN=
LEETCODE_ENABLED=true
CACHE_PATH=./.cache/responses.db
```

`.env` is git-ignored. Do not commit real API keys.

## Output Examples

Full default output is committed here:

- `samples/candidate_01.gold.json`

Custom projection:

```powershell
python -m transformer --inputs samples\candidate_01 --config configs\custom_example.json
```

```json
[
  {
    "_confidence": {
      "full_name": 0.5,
      "phone": 0.5,
      "primary_email": 0.5,
      "skills": 0.9
    },
    "full_name": "Ananya Rao",
    "phone": "+919988776655",
    "primary_email": "ananya.rao@example.com",
    "skills": [
      "Python",
      "Kubernetes",
      "TypeScript",
      "JavaScript",
      "Docker",
      "GitHub Actions"
    ]
  }
]
```

## Repository Layout

```text
transformer/
  __main__.py          CLI entry
  config.py            .env/config loading
  detect.py            source detection
  models.py            pydantic models
  cache.py             SQLite content-hash cache
  llm.py               OpenAI wrapper and routing
  normalize.py         phone/date/country/email normalizers
  skills.py            skill aliases and canonicalization
  merge.py             identity matching and conflict resolution
  confidence.py        pure scoring formula
  project.py           projection engine
  validate.py          projected output validation
  evidence/            file signals and LeetCode evidence
  extractors/          source-specific extractors
configs/
samples/
tests/
```

## Tests

```powershell
python -m pytest -q
```

Current suite covers:

- golden pipeline output
- corrupt source isolation
- phone conflicts and provenance
- homonym non-merge
- normalizers and skill acronyms
- projection path resolver
- PDF and scanned-PDF OCR fallback
- GitHub file-signal tiers
- LeetCode degradation
- cross-confirmed skill confidence
- deterministic recency scoring

## Assumptions

- Eightfold did not provide official sample inputs, so `samples/` contains synthetic fixtures.
- Default phone region is `IN`, configurable through `.env`.
- Name alone never merges two records.
- LeetCode uses a public GraphQL endpoint, so network/API failures fail closed and add no evidence.
- The committed cache fixture exists for repeatable demos.

## Design Decision

The design decision I am happiest with is the LLM-proposes/deterministic-validators-dispose boundary plus content-hash caching. OpenAI can help turn prose into candidate-shaped JSON, but every proposed value is normalized or rejected before merge. Identity, conflict resolution, and confidence are pure code, so the system can use LLMs while staying deterministic and honest about missing data.
