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
python -m transformer --inputs samples\candidate_01 --config configs\default.json --explain
```

Say: Python is high confidence because it appears in multiple sources and has GitHub authored evidence. If LeetCode confirms a language too, the confidence function adds the cross-confirm delta. The LLM never decides the score.
With the committed sample, Python includes the `leetcode_cross_confirm` breakdown because `samples\candidate_01\leetcode.txt` is backed by the seeded cache.

## 4. Edge Case

```powershell
python -m transformer --inputs samples\edge_garbage --config configs\default.json
```

Say: the corrupt ATS JSON logs a warning, contributes no observations, and the run still completes from the remaining source.

## 5. Design Decision

Say: the key design is LLM proposes, deterministic validators dispose, plus content-hash caching. This lets the system use LLMs while staying deterministic and never inventing values.
