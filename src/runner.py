import json
from datetime import datetime
from pathlib import Path

from src.classifier import classify_email
from src.config import PromptConfig
from src.scorer import score_case


def load_cases(cases_path: str | Path) -> list[dict]:
    """
    Load golden dataset cases from disk.

    Supports both the versioned wrapper shape::

        {"dataset_version": "1.0.0", "cases": [...]}

    and a bare JSON array::

        [{...}, {...}]

    Returning a plain list either way keeps older dataset files working.
    """
    with open(cases_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        cases = data.get("cases")
        if cases is None:
            raise ValueError(
                f"Dataset {cases_path} is an object but has no 'cases' key."
            )
    else:
        cases = data

    if not isinstance(cases, list):
        raise ValueError(f"Dataset {cases_path} did not resolve to a list of cases.")

    return cases


def run_eval(
    cases_path: str = "golden_dataset/cases.json",
    prompt_path: str = "prompts/v1.yaml",
    output_dir: str = "runs",
) -> dict:
    prompt_config = PromptConfig.from_yaml(prompt_path)

    cases = load_cases(cases_path)

    results = []
    passed_count = 0

    for case in cases:
        output = classify_email(case["input"], prompt_config)
        scored = score_case(case, output)
        results.append(scored.model_dump())
        if scored.category_match:
            passed_count += 1

    total = len(cases)
    pass_rate = round(passed_count / total, 4) if total > 0 else 0.0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    run_id = f"run_{timestamp}"

    run_payload = {
        "run_id": run_id,
        "prompt_version": getattr(prompt_config, "version", "v1"),
        "pass_rate": pass_rate,
        "results": results,
    }

    runs_folder = Path(output_dir)
    runs_folder.mkdir(parents=True, exist_ok=True)
    run_file = runs_folder / f"{run_id}.json"
    run_file.write_text(json.dumps(run_payload, indent=2), encoding="utf-8")

    print(f"Run complete: {run_id} | Pass rate: {pass_rate * 100:.1f}% ({passed_count}/{total})")
    print(f"Saved to: {run_file}")
    return run_payload


if __name__ == "__main__":
    import sys

    prompt_path = sys.argv[1] if len(sys.argv) > 1 else "prompts/v1.yaml"
    run_eval(prompt_path=prompt_path)

