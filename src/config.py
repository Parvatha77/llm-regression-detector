from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field


class ClassificationOutput(BaseModel):
    category: str
    summary: str

    model_config = {"extra": "ignore"}


class PromptConfig(BaseModel):
    system_prompt: str
    few_shot_examples: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"extra": "ignore"}

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PromptConfig":
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

