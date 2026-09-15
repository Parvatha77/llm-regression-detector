# Golden Dataset

Human-verified ground truth for the customer support email classifier. Every label
in `cases.json` is a judgment call, and the `notes` field records the reasoning so a
reviewer can agree or overrule it.

## Schema

`cases.json` is a versioned object:

```json
{
  "dataset_version": "1.0.0",
  "schema_version": 1,
  "updated_at": "2026-09-15",
  "cases": [ { ... } ]
}
```

Each case:

| Field | Required | Description |
|---|---|---|
| `id` | yes | Stable identifier, `case_N`. Never reused or renumbered. |
| `input` | yes | The raw customer email, verbatim. |
| `expected_category` | yes | One of `billing`, `technical`, `account`, `general`. |
| `expected_difficulty` | yes | One of `easy`, `medium`, `hard`. |
| `notes` | yes | Why this label is correct, and what the trap is. |

`src/runner.py::load_cases` also accepts a bare JSON array, so older dataset files
keep working. Prefer the wrapped form for anything new.

## Rules

1. **Never mutate the `input` or `expected_category` of an existing `id`.** Runs
   already on disk reference these IDs. Changing a label silently invalidates every
   comparison against those runs.
2. **To change a label, that is a dataset version event.** Add a new case with a new
   ID instead, or bump `dataset_version` and treat it as a deliberate re-baseline.
3. **Adding cases is safe** and does not invalidate prior runs. The comparison logic
   matches on `case_id`, so a case present only in the newer run is skipped rather
   than counted as a regression.
4. **Bump `dataset_version`** when labels change, and update `updated_at`.

## Adding a case

Append to `cases` with the next unused `case_N`, then confirm the set still loads:

```bash
uv run python -c "from src.runner import load_cases; print(len(load_cases('golden_dataset/cases.json')))"
```

## Why the labels matter more than the count

A regression system is only as good as its ground truth. If a label is wrong, the
pipeline will confidently report a regression that is actually correct behavior. When
a real failure surfaces in production, add it here as a new case — that is how this
dataset is meant to grow over time.

## Current composition

80 cases: 21 account, 21 technical, 20 billing, 18 general — with difficulty spread
across easy (32), medium (35), and hard (13). The hard cases are deliberately
ambiguous (billing vs account, technical vs account), sarcastic, typo-laden, terse,
and mixed-language; each carries a `notes` entry explaining the tie-break.
