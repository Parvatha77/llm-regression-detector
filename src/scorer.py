from src.schema import CaseResult, GoldenCase
from src.config import ClassificationOutput


def score_case(case: GoldenCase | dict, output: ClassificationOutput) -> CaseResult:
    if isinstance(case, dict):
        case_id = case["id"]
        email_input = case["input"]
        expected_category = case["expected_category"]
    else:
        case_id = case.id
        email_input = case.input
        expected_category = case.expected_category

    actual_category = output.category.strip()
    category_match = actual_category.lower() == expected_category.strip().lower()

    return CaseResult(
        case_id=case_id,
        input=email_input,
        expected_category=expected_category,
        actual_category=actual_category,
        category_match=category_match,
        summary=output.summary,
    )
