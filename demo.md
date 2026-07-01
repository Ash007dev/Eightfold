# Two-Minute Demo Checklist

Use PowerShell from the repo root.

## 0. Setup

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m transformer --check-llm
```

For the committed sample, the pre-seeded SQLite cache lets the demo run offline and deterministically.

## 1. Default Profile

```powershell
python -m transformer --inputs samples\candidate_01 --config configs\default.json
```

Say: this emits the full projected profile with normalized contact data, skills, provenance, and confidence.

## 2. Projection Twist

```powershell
python -m transformer --inputs samples\candidate_01 --config configs\custom_example.json
```

Say: same canonical record, different runtime config, no code change.

## 3. Explain One Skill

```powershell
python -m transformer --inputs samples\candidate_01 --config configs\default.json --report
```

Say: Python is high confidence because it appears in multiple sources and has GitHub authored evidence. If LeetCode confirms a language too, the confidence function adds the cross-confirm delta. The LLM never decides the score.
With the committed sample, Python includes the `leetcode_cross_confirm` breakdown because `samples\candidate_01\leetcode.txt` is backed by the seeded cache.

## 4. Batch Scale And Dedup

```powershell
python -m transformer --inputs samples\batch10 --batch --stats --config configs\default.json
```

Say: this runs ten candidate folders through the same single-candidate engine. CSV+ATS records merge by email/phone normalization, while two same-name Sam Patel folders stay separate because name alone never merges.

Then mention the benchmark:

```powershell
python scripts\scale_benchmark.py --n 1000
```

Say: on this machine the structured-source benchmark processed 1,000 synthetic candidates deterministically; the warm pass was about 4.7 seconds, around 4.7 ms per candidate.

## 5. Edge Case

```powershell
python -m transformer --inputs samples\edge_garbage --config configs\default.json
```

Say: the corrupt ATS JSON logs a warning, contributes no observations, and the run still completes from the remaining source.

## 6. Design Decision

Say: the key design is LLM proposes, deterministic validators dispose, plus content-hash caching. This lets the system use LLMs while staying deterministic and never inventing values.
