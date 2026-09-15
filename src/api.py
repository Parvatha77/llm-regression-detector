"""
FastAPI application for the LLM Regression Detector.

Browser-facing API is mounted under /api so the Vite frontend can talk to it
cross-origin from http://localhost:5173:

  POST /api/run                 — run the evaluator against the golden dataset
  GET  /api/runs                — run summaries (array, chart-ready)
  GET  /api/comparison/latest   — diff of the latest two runs
  GET  /api/drift               — gradual pass-rate drift across recent runs

The original root-level routes (/run, /runs, /compare, /drift) are kept so
existing scripts and curl commands keep working.
"""

import json
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .compare import compare_runs, get_latest_two_runs, RunComparison
from .drift import check_drift
from .runner import run_eval

RUNS_DIR = "runs"

app = FastAPI(
    title="LLM Regression Detector",
    description="Evaluate, compare, and monitor LLM classifier quality across prompt versions.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _run_files() -> list[Path]:
    """All run JSON files in chronological (filename) order."""
    return sorted(Path(RUNS_DIR).glob("*.json"))


def _load_run(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_summary(data: dict) -> dict:
    """Flatten a run payload into the shape the dashboard chart consumes."""
    results = data.get("results", [])
    passed = sum(1 for r in results if r.get("category_match"))
    return {
        "run_id": data.get("run_id"),
        "prompt_version": data.get("prompt_version", "unknown"),
        "pass_rate": data.get("pass_rate", 0.0),
        "total_cases": len(results),
        "passed_cases": passed,
    }


def _comparison_payload() -> dict:
    pair = get_latest_two_runs(runs_dir=RUNS_DIR)
    if pair is None:
        raise HTTPException(
            status_code=404,
            detail="Need at least two runs in runs/. Run POST /run first.",
        )
    baseline, current = pair
    result: RunComparison = compare_runs(baseline, current)
    return {
        "baseline_run_id": result.baseline_run_id,
        "current_run_id": result.current_run_id,
        "pass_rate_delta": result.pass_rate_delta,
        "per_category_delta": result.per_category_delta,
        "regressions": result.regressions,
        "improvements": result.improvements,
        "status": result.status,
    }


def _drift_payload(alpha: float, threshold: float, window: int) -> dict:
    files = _run_files()
    if not files:
        raise HTTPException(status_code=404, detail="No runs found in runs/.")

    pass_rates, run_ids = [], []
    for f in files:
        data = _load_run(f)
        pass_rates.append(data["pass_rate"])
        run_ids.append(data["run_id"])

    drift = check_drift(pass_rates, alpha=alpha, threshold=threshold, window=window)
    recent = pass_rates[-window:]
    return {
        # Frontend-facing aliases
        "drift_detected": drift.is_drifting,
        "drop": drift.delta_from_start,
        # Raw detection detail
        "ewma": drift.ewma,
        "delta_from_start": drift.delta_from_start,
        "is_drifting": drift.is_drifting,
        "status": drift.status,
        "window": window,
        "run_ids_considered": run_ids[-window:],
        "pass_rates": recent,
        "window_pass_rates": recent,
    }


# ---------------------------------------------------------------------------
# /api  — mounted router used by the React frontend
# ---------------------------------------------------------------------------

api = APIRouter(prefix="/api")


@api.get("/runs", summary="Run summaries for the trend chart")
def api_runs() -> list[dict]:
    return [_run_summary(_load_run(f)) for f in _run_files()]


@api.get("/comparison/latest", summary="Compare the latest two runs")
def api_comparison_latest() -> dict:
    return _comparison_payload()


@api.get("/drift", summary="Check for gradual pass-rate drift")
def api_drift(
    alpha: float = 0.3, threshold: float = 0.05, window: int = 7
) -> dict:
    return _drift_payload(alpha=alpha, threshold=threshold, window=window)


@api.post("/run", summary="Run evaluation against golden dataset")
def api_trigger_run(
    prompt_path: str = "prompts/v1.yaml",
    cases_path: str = "golden_dataset/cases.json",
) -> dict:
    try:
        return run_eval(
            cases_path=cases_path, prompt_path=prompt_path, output_dir=RUNS_DIR
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


app.include_router(api)


# ---------------------------------------------------------------------------
# Legacy root-level routes (unchanged behaviour)
# ---------------------------------------------------------------------------

@app.post("/run", summary="Run evaluation against golden dataset")
def trigger_run(
    prompt_path: str = "prompts/v1.yaml",
    cases_path: str = "golden_dataset/cases.json",
) -> dict:
    """Execute the eval runner and return the run result."""
    try:
        result = run_eval(
            cases_path=cases_path,
            prompt_path=prompt_path,
            output_dir=RUNS_DIR,
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/runs", summary="List all saved run IDs")
def list_runs() -> dict:
    """Return a sorted list of run IDs available in the runs/ directory."""
    files = _run_files()
    run_ids = [f.stem for f in files]
    return {"runs": run_ids, "count": len(run_ids)}


@app.get("/compare", summary="Compare the latest two runs")
def compare_latest() -> dict:
    """Diff the two most recent runs and return regressions, improvements, and status."""
    return _comparison_payload()


@app.get("/drift", summary="Check for gradual pass-rate drift across all runs")
def drift_check_root(
    alpha: float = 0.3, threshold: float = 0.05, window: int = 7
) -> dict:
    """
    Load all saved runs in chronological order, extract pass rates, and
    run EWMA drift detection.
    """
    return _drift_payload(alpha=alpha, threshold=threshold, window=window)
