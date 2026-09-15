import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class RunComparison:
    baseline_run_id: str
    current_run_id: str
    pass_rate_delta: float
    per_category_delta: dict
    regressions: list  # pass -> fail
    improvements: list  # fail -> pass
    status: str  # "ok", "warning", "critical"


WARNING_THRESHOLD = 0.03  # 3%
CRITICAL_THRESHOLD = 0.08  # 8%


def get_latest_two_runs(runs_dir: str = "runs") -> tuple[dict, dict] | None:
    files = sorted(Path(runs_dir).glob("*.json"))
    if len(files) < 2:
        return None
    baseline = json.loads(files[-2].read_text())
    current = json.loads(files[-1].read_text())
    return baseline, current


def _category_pass_rates(run: dict) -> dict:
    by_cat = {}
    for r in run["results"]:
        cat = r["expected_category"]
        by_cat.setdefault(cat, [0, 0])  # [pass, total]
        by_cat[cat][1] += 1
        if r["category_match"]:
            by_cat[cat][0] += 1
    return {cat: p / t for cat, (p, t) in by_cat.items()}


def compare_runs(baseline: dict, current: dict) -> RunComparison:
    baseline_by_id = {r["case_id"]: r for r in baseline["results"]}
    current_by_id = {r["case_id"]: r for r in current["results"]}

    regressions, improvements = [], []
    for case_id, cur in current_by_id.items():
        base = baseline_by_id.get(case_id)
        if base is None:
            continue
        if base["category_match"] and not cur["category_match"]:
            regressions.append({"case_id": case_id, "input": cur["input"],
                                 "old_output": base["actual_category"],
                                 "new_output": cur["actual_category"]})
        elif not base["category_match"] and cur["category_match"]:
            improvements.append({"case_id": case_id, "input": cur["input"],
                                  "old_output": base["actual_category"],
                                  "new_output": cur["actual_category"]})

    pass_rate_delta = current["pass_rate"] - baseline["pass_rate"]

    base_cat_rates = _category_pass_rates(baseline)
    cur_cat_rates = _category_pass_rates(current)
    per_category_delta = {
        cat: round(cur_cat_rates.get(cat, 0) - base_cat_rates.get(cat, 0), 4)
        for cat in set(base_cat_rates) | set(cur_cat_rates)
    }

    abs_delta = abs(pass_rate_delta)
    if abs_delta >= CRITICAL_THRESHOLD:
        status = "critical"
    elif abs_delta >= WARNING_THRESHOLD:
        status = "warning"
    else:
        status = "ok"

    return RunComparison(
        baseline_run_id=baseline["run_id"],
        current_run_id=current["run_id"],
        pass_rate_delta=round(pass_rate_delta, 4),
        per_category_delta=per_category_delta,
        regressions=regressions,
        improvements=improvements,
        status=status,
    )