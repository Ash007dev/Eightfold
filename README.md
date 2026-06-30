# Multi-Source Candidate Data Transformer

This is a production-style Python 3.11 CLI for the Eightfold assignment. It ingests messy candidate data from structured sources, resumes, notes, and GitHub evidence, then emits one canonical, deduplicated, provenance-tracked, confidence-scored JSON profile per candidate. The key design split is canonical record vs projection config: the merger builds the internal truth, and `configs/*.json` decides the emitted shape without code changes.

## Run

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m transformer --inputs samples\candidate_01 --config configs\default.json
python -m transformer --inputs samples\candidate_01 --config configs\custom_example.json
python -m pytest -q
```

The repository includes `.cache/responses.db`, pre-seeded with content-hash responses for the sample LLM and GitHub calls, so the demo and tests run offline and deterministically.

## PDF Resumes

PDF resumes are supported. Put a text-based PDF in any input folder and the detector treats it as a resume:

```text
my_candidate/
  ats.json
  recruiter.csv
  resume.pdf
  notes.txt
  github.txt
```

Then run:

```powershell
python -m transformer --inputs my_candidate --config configs\default.json
```

There are PDF fixtures under `samples\candidate_pdf\`: one text-based PDF and one scanned/image-only PDF. Text-based PDFs work with `pdfplumber`. Scanned PDFs use OCR through `pytesseract`, which also needs the Tesseract OCR program installed on your machine.

On Windows, install Tesseract first, then install Python requirements:

```powershell
winget install UB-Mannheim.TesseractOCR
python -m pip install -r requirements.txt
```

If Tesseract is missing, scanned pages safely contribute no resume text instead of crashing the run.

## Architecture

```text
files / manifest
  -> detect.py
  -> extractors/*
       CSV + ATS: exact observations
       Resume + notes: LLM proposes JSON, code validates
       GitHub: authored commits gate strong skill evidence
  -> merge.py
       identity match, normalization, conflict resolution
  -> confidence.py
       pure score function from provenance signals
  -> CanonicalRecord
  -> project.py + validate.py
       config-driven output shape
  -> sorted JSON
```

`CanonicalRecord` remains internal. The projection engine is the only output producer, including for the default schema in `configs/default.json`.

## Default Output

```json
[
  {
    "candidate_id": "cand_d97d85b6ef3e",
    "education": [
      {
        "degree": "B.Tech",
        "end_year": 2021,
        "field": "Computer Science",
        "institution": "National Institute of Technology Karnataka"
      }
    ],
    "emails": [
      "ananya.rao@example.com"
    ],
    "experience": [
      {
        "company": "Vector Labs",
        "end": null,
        "start": "2023-01",
        "summary": "Built Python services, Kubernetes deployment workflows, and JavaScript developer tooling.",
        "title": "Senior Backend Engineer"
      }
    ],
    "full_name": "Ananya Rao",
    "headline": "Backend platform engineer",
    "links": {
      "github": "https://github.com/ananyarao",
      "linkedin": null,
      "other": [
        "https://ananya.dev"
      ],
      "portfolio": "https://ananya.dev"
    },
    "location": {
      "city": "Bengaluru",
      "country": "IN",
      "region": "Karnataka"
    },
    "overall_confidence": 0.515,
    "phones": [
      "+919988776655",
      "+919876543210"
    ],
    "provenance": [
      {"field": "education", "method": "llm_extraction", "selected": true, "source": "resume", "value": 2021},
      {"field": "education", "method": "llm_extraction", "selected": true, "source": "resume", "value": "B.Tech"},
      {"field": "education", "method": "llm_extraction", "selected": true, "source": "resume", "value": "Computer Science"},
      {"field": "education", "method": "llm_extraction", "selected": true, "source": "resume", "value": "National Institute of Technology Karnataka"},
      {"field": "emails", "method": "exact", "selected": true, "source": "ats_json", "value": "ananya.rao@example.com"},
      {"field": "emails", "method": "exact", "selected": true, "source": "recruiter_csv", "value": "ananya.rao@example.com"},
      {"field": "emails", "method": "llm_extraction", "selected": true, "source": "resume", "value": "ananya.rao@example.com"},
      {"field": "experience", "method": "exact", "selected": false, "source": "ats_json", "value": "Backend Engineer"},
      {"field": "experience", "method": "exact", "selected": true, "source": "ats_json", "value": "Vector Labs"},
      {"field": "experience", "method": "exact", "selected": true, "source": "recruiter_csv", "value": "Senior Backend Engineer"},
      {"field": "experience", "method": "exact", "selected": true, "source": "recruiter_csv", "value": "Vector Labs"},
      {"field": "experience", "method": "llm_extraction", "selected": true, "source": "resume", "value": "2023-01"},
      {"field": "experience", "method": "llm_extraction", "selected": true, "source": "resume", "value": "Built Python services, Kubernetes deployment workflows, and JavaScript developer tooling."},
      {"field": "experience", "method": "llm_extraction", "selected": true, "source": "resume", "value": "Senior Backend Engineer"},
      {"field": "experience", "method": "llm_extraction", "selected": true, "source": "resume", "value": "Vector Labs"},
      {"field": "full_name", "method": "exact", "selected": true, "source": "ats_json", "value": "Ananya Rao"},
      {"field": "full_name", "method": "exact", "selected": true, "source": "github", "value": "Ananya Rao"},
      {"field": "full_name", "method": "exact", "selected": true, "source": "recruiter_csv", "value": "Ananya Rao"},
      {"field": "full_name", "method": "llm_extraction", "selected": true, "source": "resume", "value": "Ananya Rao"},
      {"field": "headline", "method": "llm_extraction", "selected": false, "source": "notes", "value": "Senior backend engineer"},
      {"field": "headline", "method": "llm_extraction", "selected": true, "source": "resume", "value": "Backend platform engineer"},
      {"field": "links", "method": "exact", "selected": true, "source": "ats_json", "value": "https://github.com/ananyarao"},
      {"field": "links", "method": "regex", "selected": true, "source": "github", "value": "https://ananya.dev"},
      {"field": "links", "method": "regex", "selected": true, "source": "github", "value": "https://ananya.dev"},
      {"field": "links", "method": "regex", "selected": true, "source": "github", "value": "https://github.com/ananyarao"},
      {"field": "location", "method": "exact", "selected": true, "source": "ats_json", "value": "Bengaluru"},
      {"field": "location", "method": "exact", "selected": true, "source": "ats_json", "value": "IN"},
      {"field": "location", "method": "exact", "selected": true, "source": "ats_json", "value": "Karnataka"},
      {"field": "phones", "method": "exact", "selected": true, "source": "ats_json", "value": "+919876543210"},
      {"field": "phones", "method": "exact", "selected": true, "source": "recruiter_csv", "value": "+919988776655"},
      {"field": "phones", "method": "llm_extraction", "selected": true, "source": "resume", "value": "+919876543210"},
      {"field": "skills", "method": "exact", "selected": true, "source": "ats_json", "value": "JavaScript"},
      {"field": "skills", "method": "exact", "selected": true, "source": "ats_json", "value": "Python"},
      {"field": "skills", "method": "github_authored", "selected": true, "source": "github", "value": "Python"},
      {"field": "skills", "method": "github_authored", "selected": true, "source": "github", "value": "TypeScript"},
      {"field": "skills", "method": "github_filesignal", "selected": true, "source": "github", "value": "Docker"},
      {"field": "skills", "method": "github_filesignal", "selected": true, "source": "github", "value": "GitHub Actions"},
      {"field": "skills", "method": "github_filesignal", "selected": true, "source": "github", "value": "Kubernetes"},
      {"field": "skills", "method": "llm_extraction", "selected": true, "source": "notes", "value": "Kubernetes"},
      {"field": "skills", "method": "llm_extraction", "selected": true, "source": "notes", "value": "Python"},
      {"field": "skills", "method": "llm_extraction", "selected": true, "source": "resume", "value": "JavaScript"},
      {"field": "skills", "method": "llm_extraction", "selected": true, "source": "resume", "value": "Kubernetes"},
      {"field": "skills", "method": "llm_extraction", "selected": true, "source": "resume", "value": "Python"}
    ],
    "skills": [
      {"confidence": 0.8, "name": "Python", "sources": ["ats_json", "github", "notes", "resume"]},
      {"confidence": 0.6, "name": "Kubernetes", "sources": ["github", "notes", "resume"]},
      {"confidence": 0.6, "name": "TypeScript", "sources": ["github"]},
      {"confidence": 0.5, "name": "JavaScript", "sources": ["ats_json", "resume"]},
      {"confidence": 0.4, "name": "Docker", "sources": ["github"]},
      {"confidence": 0.4, "name": "GitHub Actions", "sources": ["github"]}
    ],
    "years_experience": null
  }
]
```

## Custom Output

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

## Assumptions

- Eightfold did not provide sample inputs, so `samples/` contains synthetic fixtures.
- Default phone region is `IN`, configurable through `.env`.
- `notes.txt` is treated as anonymous evidence and attached only when the run has exactly one strongly identified candidate group.
- The committed cache fixture is for repeatable demos; live LLM/GitHub calls work when `.env` has the relevant settings.

## Descoped

LinkedIn ingestion, LeetCode, certificates, Neo4j, and model routing are intentionally descoped for the MVP. `LLM_MODEL_CHEAP` is left as a config hook only.

## Design Notes

The design decision I am happiest with is the LLM-proposes/code-disposes boundary plus content-hash caching. Resume and notes extraction can use an LLM, but every proposed value is normalized or rejected before merge, and no LLM decides identity, winners, or scores.

One handled edge case: two people named Sam Patel in `samples/edge_homonym` stay as two profiles because name alone is never an identity key.
