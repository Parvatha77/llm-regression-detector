import os
import json
from groq import Groq
from dotenv import load_dotenv
from .config import PromptConfig, ClassificationOutput

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])


def classify_email(email_text: str, prompt_config: PromptConfig) -> ClassificationOutput:
    messages = [{"role": "system", "content": prompt_config.system_prompt}]
    messages.extend(prompt_config.few_shot_examples)
    messages.append({"role": "user", "content": email_text})

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    parsed = json.loads(raw)
    return ClassificationOutput(**parsed)