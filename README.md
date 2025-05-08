# SeekGPT Python Client Library

[![PyPI version](https://badge.fury.io/py/seekgpt.svg)](https://badge.fury.io/py/seekgpt) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) `seekgpt` is a Python library designed to provide a simple and unified interface for interacting with various Large Language Model (LLM) APIs, focusing on compatibility with the OpenAI API standard. It defaults to connecting to `https://api.seekgpt.org/v1` but can be easily configured for other services.

## Features

* Connect to the default SeekGPT API (`https://api.seekgpt.org/v1`).
* Connect to any OpenAI-compatible API endpoint (OpenAI, Ollama, vLLM, Anyscale, Together AI, etc.) using `SeekGPT`.
* Simple `chat` interface following the `chat/completions` standard.
* Support for streaming responses.
* Handles API key authentication (Bearer token).
* Basic error handling and custom exceptions.
* Configurable API base URL, API key, default model, and timeout.
* Uses environment variables for configuration (`SEEKGPT_API_KEY`, `SEEKGPT_API_BASE`, etc.).

## Installation

```bash
pip install seekgpt
````

## Quick Start

### Connecting to SeekGPT (Default)

Make sure you have your SeekGPT API key set as an environment variable:

```bash
export SEEKGPT_API_KEY="your-seekgpt-api-key"
# Optional: Set a default model
# export SEEKGPT_DEFAULT_MODEL="seekgpt-model-name"
```

Then use the `SeekGPT`:

```python
from seekgpt import SeekGPT

# Client automatically picks up SEEKGPT_API_KEY from environment
# You can also pass it directly: SeekGPTClient(api_key="your-key")
client = SeekGPT(api_key="", api_base="https://api.seekgpt.org/v1")

try:
    response = client.chat(
        model="SeekGPT-mini", # Or rely on SEEKGPT_DEFAULT_MODEL env var
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ]
    )
    print(response['choices'][0]['message']['content'])

    # Streaming example
    stream = client.chat(
        model="SeekGPT-mini",
        messages=[{"role": "user", "content": "Tell me a short story."}],
        stream=True
    )

    print("\nStreaming response:")
    for chunk in stream:
        # Process each line (chunk) of the stream
        # Note: Parsing SSE data might require additional logic depending on the exact format
        print(chunk, end="") # Raw SSE line, may need parsing
    print()

except Exception as e:
    print(f"An error occurred: {e}")

```

### Connecting to OpenAI

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

```python
from seekgpt import SeekGPT

# SeekGPT will fallback to OPENAI_API_KEY if SEEKGPT_API_KEY is not set
client = SeekGPT(
    api_base="https://api.openai.com/v1](https://api.openai.com/v1)",
    default_model="gpt-4o" # Set a default model for this client instance
)

response = client.chat(
    messages=[{"role": "user", "content": "Hello OpenAI!"}]
)
print(response['choices'][0]['message']['content'])
```

### Connecting to Ollama (Local)

Ensure Ollama is running (usually at `http://localhost:11434`).

```python
from seekgpt import SeekGPT, APIConnectionError

# Ollama typically doesn't require an API key for local access,
# but some libraries expect *something*, so we pass a dummy key.
# The client automatically detects localhost and won't raise an Auth error if key is None.
client = SeekGPT(
    api_base="http://localhost:11434/v1",
    api_key="ollama", # Dummy key often needed, but can also try api_key=None
    default_model="llama3" # Specify the local model you want to use
)

try:
    response = client.chat(
        messages=[{"role": "user", "content": "Hi Ollama! Write a haiku about code."}]
    )
    print(response['choices'][0]['message']['content'])
except APIConnectionError as e:
    print(f"Could not connect to Ollama. Is the server running? Error: {e}")
except Exception as e:
    print(f"An error occurred: {e}")

```

### Connecting to Other OpenAI-Compatible Services (vLLM, Anyscale, Together AI, etc.)

Set the appropriate API key environment variable (e.g., `ANYSCALE_API_KEY`, `TOGETHER_API_KEY`) or pass the `api_key` directly. Use the `SeekGPT` and provide the correct `api_base` for the service.

```python
# Example for Anyscale Endpoints
# export ANYSCALE_API_KEY="your-anyscale-key"

from seekgpt import SeekGPT

client = SeekGPT(
    api_base="https://api.endpoints.anyscale.com/v1",
    # SeekGPT will try ANYSCALE_API_KEY if SEEKGPT_API_KEY/OPENAI_API_KEY are not set
    # Or pass explicitly: api_key="your-anyscale-key"
    default_model="mistralai/Mixtral-8x7B-Instruct-v0.1"
)

# ... use client.chat(...) ...
```

## Configuration

The clients can be configured via:

1.  **Environment Variables:**
      * `SEEKGPT_API_KEY`: API Key (used by `SeekGPTClient` and `SeekGPT` priority).
      * `SEEKGPT_API_BASE`: API Base URL (used by `SeekGPT` if `api_base` argument is not provided). Defaults to `https://api.seekgpt.org/v1`.
      * `SEEKGPT_DEFAULT_MODEL`: Default model name.
      * `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.: Fallback keys used by `SeekGPT` if `SEEKGPT_API_KEY` is missing.
      * `SEEKGPT_LOGLEVEL`: Set logging level (e.g., `DEBUG`, `INFO`, `WARNING`). Default is `WARNING`.
2.  **Client Initialization Arguments:** Pass `api_key`, `api_base`, `default_model`, `timeout` directly when creating `SeekGPTClient` or `SeekGPT`.

## Connecting to Non-OpenAI-Compatible APIs

This library focuses on the OpenAI API standard (`/v1/chat/completions`). For services with significantly different APIs, authentication methods, or response structures, using their **official Python SDKs** is strongly recommended:

  * **Google Generative AI (Gemini):** Use the [`google-generativeai`](https://pypi.org/project/google-generativeai/) or [`google-cloud-aiplatform`](https://pypi.org/project/google-cloud-aiplatform/) libraries.
  * **Anthropic (Claude):** Use the [`anthropic`](https://pypi.org/project/anthropic/) library. It requires specific headers (`x-api-key`, `anthropic-version`) and has a different request/response structure.
  * **Cohere:** Use the [`cohere`](https://pypi.org/project/cohere/) library.

While you *could* potentially adapt `SeekGPT._request` or create new client classes within this library for them, it often involves reimplementing logic already handled well by their official SDKs.

## Error Handling

The library defines custom exceptions inheriting from `SeekGPTError`:

  * `AuthenticationError`: For 401/403 errors.
  * `APIConnectionError`: For network issues (timeout, connection refused).
  * `InvalidRequestError`: For 400/422/429 errors (bad request, rate limit).
  * `APIError`: For other non-2xx API errors.

Wrap API calls in `try...except` blocks to handle potential issues.

## Contributing

[Details on how to contribute - optional]

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```

**6. `LICENSE`:**

Choose a license (e.g., MIT) and add the corresponding text to the `LICENSE` file.

**7. Build and Upload to PyPI (When Ready):**

1.  Install build tools: `pip install build twine`
2.  Build the package: `python -m build`
3.  Check the built distributions in the `dist/` folder.
4.  Upload to TestPyPI first: `twine upload --repository testpypi dist/*`
5.  Test installation from TestPyPI: `pip install --index-url https://test.pypi.org/simple/ --no-deps seekgpt`
6.  Upload to PyPI: `twine upload dist/*`

This structure provides a functional client library that meets your requirements, is ready for packaging, and offers guidance on connecting to various LLM backends. Remember to replace placeholder names and URLs with your actual project details.
