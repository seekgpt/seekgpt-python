# Example for Anyscale Endpoints
# export ANYSCALE_API_KEY="your-anyscale-key"

from seekgpt import SeekGPT

client = SeekGPT(
   
    # BaseClient will try ANYSCALE_API_KEY if SEEKGPT_API_KEY/OPENAI_API_KEY are not set
    # Or pass explicitly: api_key="your-anyscale-key"
    default_model="SeekGPT-mini"
)

response = client.chat(
    messages=[
        {"role": "user", "content": "What is the capital of France?"}
    ]
)

print(response)
# ... use client.chat(...) ...
