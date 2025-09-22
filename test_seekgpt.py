import os
from seekgpt import SeekGPT

os.environ["SEEKGPT_API_KEY"] = "sk-WXD60Gu1uQarEAe62NkmLG1UMjewq8GoxkVkwbkRPaKNmDYk"


client = SeekGPT(
    base_url="https://api.seekgpt.org/v1",
)

# List all available models
try:
    models = client.models.list()
    print("Available models:")
    for model in models.data:
        print(f"- {model.id}")
except Exception as e:
    print(f"Error listing models: {e}")
