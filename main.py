from src.classifier import classify_email
from src.config import PromptConfig

if __name__ == "__main__":
    config = PromptConfig.from_yaml("prompts/v1.yaml")
    email = "Hi, I was charged twice for my subscription this month. Please fix this."
    result = classify_email(email, config)
    print(result.model_dump_json(indent=2))