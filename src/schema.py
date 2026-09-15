from pydantic import BaseModel, Field
from typing import Any


class GoldenCase(BaseModel):
    id: str
    input: str
    expected_category: str
    expected_difficulty: str | None = None
    notes: str | None = None


class CaseResult(BaseModel):
    case_id: str
    input: str
    expected_category: str
    actual_category: str
    category_match: bool
    summary: str


class RunResult(BaseModel):
    run_id: str
    prompt_version: str
    pass_rate: float
    results: list[CaseResult]

