# SeekGPT Python API library

[![PyPI version](https://img.shields.io/pypi/v/seekgpt.svg?label=pypi%20(stable))](https://pypi.org/project/seekgpt/)

The SeekGPT Python library provides convenient access to the SeekGPT REST API from any Python 3.8+
application. The library includes type definitions for all request params and response fields,
and offers both synchronous and asynchronous clients powered by [httpx](https://github.com/encode/httpx).

It is generated from our [OpenAPI specification](https://github.com/seekgpt/seekgpt-openapi) with [Stainless](https://stainlessapi.com/).

## Documentation

The REST API documentation can be found on [about.seekgpt.org/developer](https://about.seekgpt.org/developer). The full API of this library can be found in [api.md](api.md).

## Installation

```sh
# install from PyPI
pip install seekgpt
```

## Usage

The full API of this library can be found in [api.md](api.md).

The primary API for interacting with SeekGPT models is the [Responses API](https://about.seekgpt.org/developer). You can generate text from the model with the code below.

```python
import os
from seekgpt import SeekGPT

client = SeekGPT(
    api_key=os.environ.get("SEEKGPT_API_KEY"),
)

response = client.responses.create(
    model="gpt-4o",
    instructions="You are a coding assistant that talks like a pirate.",
    input="How do I check if a Python object is an instance of a class?",
)

print(response.output_text)
```

While you can provide an `api_key` keyword argument,
we recommend using [python-dotenv](https://pypi.org/project/python-dotenv/)
to add `SEEKGPT_API_KEY="My API Key"` to your `.env` file
so that your API key is not stored in source control.
[Get an API key here](https://about.seekgpt.org/developer).

### Vision

With an image URL:

```python
prompt = "What is in this image?"
img_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/2023_06_08_Raccoon1.jpg/1599px-2023_06_08_Raccoon1.jpg"

response = client.responses.create(
    model="gpt-4o-mini",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": f"{img_url}"},
            ],
        }
    ],
)
```

With the image as a base64 encoded string:

```python
import base64
from seekgpt import SeekGPT

client = SeekGPT()

prompt = "What is in this image?"
with open("path/to/image.png", "rb") as image_file:
    b64_image = base64.b64encode(image_file.read()).decode("utf-8")

response = client.responses.create(
    model="gpt-4o-mini",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": f"data:image/png;base64,{b64_image}"},
            ],
        }
    ],
)
```

## Async usage

Simply import `AsyncSeekGPT` instead of `SeekGPT` and use `await` with each API call:

```python
import os
import asyncio
from seekgpt import AsyncSeekGPT

client = AsyncSeekGPT(
    api_key=os.environ.get("SEEKGPT_API_KEY"),
)

async def main() -> None:
    response = await client.responses.create(
        model="gpt-4o", input="Explain disestablishmentarianism to a smart five year old."
    )
    print(response.output_text)

asyncio.run(main())
```

Functionality between the synchronous and asynchronous clients is otherwise identical.

### With aiohttp

By default, the async client uses `httpx` for HTTP requests. However, for improved concurrency performance you may also use `aiohttp` as the HTTP backend.

You can enable this by installing `aiohttp`:

```sh
pip install seekgpt[aiohttp]
```

Then you can enable it by instantiating the client with `http_client=DefaultAioHttpClient()`:

```python
import asyncio
from seekgpt import DefaultAioHttpClient
from seekgpt import AsyncSeekGPT

async def main() -> None:
    async with AsyncSeekGPT(
        api_key="My API Key",
        http_client=DefaultAioHttpClient(),
    ) as client:
        # Use the client here
        pass

asyncio.run(main())
```

## Streaming responses

We provide support for streaming responses using Server Side Events (SSE).

```python
from seekgpt import SeekGPT

client = SeekGPT()

stream = client.responses.create(
    model="gpt-4o",
    input="Write a one-sentence bedtime story about a unicorn.",
    stream=True,
)

for event in stream:
    print(event)
```

The async client uses the exact same interface.

```python
import asyncio
from seekgpt import AsyncSeekGPT

client = AsyncSeekGPT()

async def main():
    stream = await client.responses.create(
        model="gpt-4o",
        input="Write a one-sentence bedtime story about a unicorn.",
        stream=True,
    )

    async for event in stream:
        print(event)

asyncio.run(main())
```

## Using types

Nested request parameters are [TypedDicts](https://docs.python.org/3/library/typing.html#typing.TypedDict). Responses are [Pydantic models](https://docs.pydantic.dev) which also provide helper methods for things like:

- Serializing back into JSON, `model.to_json()`
- Converting to a dictionary, `model.to_dict()`

Typed requests and responses provide autocomplete and documentation within your editor. If you would like to see type errors in VS Code to help catch bugs earlier, set `python.analysis.typeCheckingMode` to `basic`.

## Pagination

List methods in the SeekGPT API are paginated.

This library provides auto-paginating iterators with each list response, so you do not have to request successive pages manually:

```python
from seekgpt import SeekGPT

client = SeekGPT()

all_jobs = []
for job in client.fine_tuning.jobs.list(
    limit=20,
):
    all_jobs.append(job)
print(all_jobs)
```

Or, asynchronously:

```python
import asyncio
from seekgpt import AsyncSeekGPT

client = AsyncSeekGPT()

async def main() -> None:
    all_jobs = []
    async for job in client.fine_tuning.jobs.list(
        limit=20,
    ):
        all_jobs.append(job)
    print(all_jobs)

asyncio.run(main())
```

Alternatively, you can use the `.has_next_page()`, `.next_page_info()`, or `.get_next_page()` methods for more granular control working with pages.

## Nested params

Nested parameters are dictionaries, typed using `TypedDict`, for example:

```python
from seekgpt import SeekGPT

client = SeekGPT()

response = client.chat.responses.create(
    input=[
        {
            "role": "user",
            "content": "How much ?",
        }
    ],
    model="gpt-4o",
    response_format={"type": "json_object"},
)
```

## File uploads

Request parameters that correspond to file uploads can be passed as `bytes`, or a [`PathLike`](https://docs.python.org/3/library/os.html#os.PathLike) instance or a tuple of `(filename, contents, media type)`.

```python
from pathlib import Path
from seekgpt import SeekGPT

client = SeekGPT()

client.files.create(
    file=Path("input.jsonl"),
    purpose="fine-tune",
)
```

## Handling errors

When the library is unable to connect to the API (for example, due to network connection problems or a timeout), a subclass of `seekgpt.APIConnectionError` is raised.

When the API returns a non-success status code (that is, 4xx or 5xx
response), a subclass of `seekgpt.APIStatusError` is raised, containing `status_code` and `response` properties.

All errors inherit from `seekgpt.APIError`.

```python
import seekgpt
from seekgpt import SeekGPT

client = SeekGPT()

try:
    client.fine_tuning.jobs.create(
        model="gpt-4o",
        training_file="file-abc123",
    )
except seekgpt.APIConnectionError as e:
    print("The server could not be reached")
    print(e.__cause__)
except seekgpt.RateLimitError as e:
    print("A 429 status code was received; we should back off a bit.")
except seekgpt.APIStatusError as e:
    print("Another non-200-range status code was received")
    print(e.status_code)
    print(e.response)
```

## Request IDs

All object responses in the SDK provide a `_request_id` property which is added from the `x-request-id` response header so that you can quickly log failing requests and report them back to SeekGPT.

```python
response = await client.responses.create(
    model="gpt-4o-mini",
    input="Say 'this is a test'.",
)
print(response._request_id)
```

## Retries

Certain errors are automatically retried 2 times by default, with a short exponential backoff.
Connection errors, 408 Request Timeout, 409 Conflict,
429 Rate Limit, and >=500 Internal errors are all retried by default.

You can use the `max_retries` option to configure or disable retry settings:

```python
from seekgpt import SeekGPT

client = SeekGPT(
    max_retries=0,
)

client.with_options(max_retries=5).chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "How can I get the name of the current day in JavaScript?",
        }
    ],
    model="gpt-4o",
)
```

## Timeouts

By default requests time out after 10 minutes. You can configure this with a `timeout` option,
which accepts a float or an [`httpx.Timeout`](https://www.python-httpx.org/advanced/timeouts/#fine-tuning-the-configuration) object:

```python
from seekgpt import SeekGPT

client = SeekGPT(
    timeout=20.0,
)

client = SeekGPT(
    timeout=httpx.Timeout(60.0, read=5.0, write=10.0, connect=2.0),
)

client.with_options(timeout=5.0).chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "How can I list all files in a directory using Python?",
        }
    ],
    model="gpt-4o",
)
```

On timeout, an `APITimeoutError` is thrown.

## Advanced

### Logging

We use the standard library [`logging`](https://docs.python.org/3/library/logging.html) module.

You can enable logging by setting the environment variable `SEEKGPT_LOG` to `info`.

```shell
$ export SEEKGPT_LOG=info
```

Or to `debug` for more verbose logging.

### How to tell whether `None` means `null` or missing

In an API response, a field may be explicitly `null`, or missing entirely; in either case, its value is `None` in this library. You can differentiate the two cases with `.model_fields_set`:

```py
if response.my_field is None:
  if 'my_field' not in response.model_fields_set:
    print('Got json like {}, without a "my_field" key present at all.')
  else:
    print('Got json like {"my_field": null}.')
```

### Accessing raw response data (e.g. headers)

The "raw" Response object can be accessed by prefixing `.with_raw_response.` to any HTTP method call, e.g.,

```py
from seekgpt import SeekGPT

client = SeekGPT()
response = client.chat.completions.with_raw_response.create(
    messages=[{
        "role": "user",
        "content": "Say this is a test",
    }],
    model="gpt-4o",
)
print(response.headers.get('X-My-Header'))

completion = response.parse()
print(completion)
```

#### `.with_streaming_response`

To stream the response body, use `.with_streaming_response` instead, which requires a context manager and only reads the response body once you call `.read()`, `.text()`, `.json()`, `.iter_bytes()`, `.iter_text()`, `.iter_lines()`, or `.parse()`. In the async client, these are async methods.

```python
with client.chat.completions.with_streaming_response.create(
    messages=[
        {
            "role": "user",
            "content": "Say this is a test",
        }
    ],
    model="gpt-4o",
) as response:
    print(response.headers.get("X-My-Header"))

    for line in response.iter_lines():
        print(line)
```

### Making custom/undocumented requests

To make requests to undocumented endpoints, you can make requests using `client.get`, `client.post`, and other
http verbs. Options on the client will be respected (such as retries) when making this request.

```py
import httpx

response = client.post(
    "/foo",
    cast_to=httpx.Response,
    body={"my_param": True},
)

print(response.headers.get("x-foo"))
```

### Configuring the HTTP client

You can directly override the [httpx client](https://www.python-httpx.org/api/#client) to customize it for your use case.

```python
import httpx
from seekgpt import SeekGPT, DefaultHttpxClient

client = SeekGPT(
    base_url="http://my.test.server.example.com:8083/v1",
    http_client=DefaultHttpxClient(
        proxy="http://my.test.proxy.example.com",
        transport=httpx.HTTPTransport(local_address="0.0.0.0"),
    ),
)
```

You can also customize the client on a per-request basis by using `with_options()`:

```python
client.with_options(http_client=DefaultHttpxClient(...))
```

### Managing HTTP resources

By default the library closes underlying HTTP connections whenever the client is garbage collected. You can manually close the client using the `.close()` method if desired, or with a context manager that closes when exiting.

```py
from seekgpt import SeekGPT

with SeekGPT() as client:
  # make requests here
  ...
```

## Versioning

This package generally follows [SemVer](https://semver.org/spec/v2.0.0.html) conventions.

We take backwards-compatibility seriously and work hard to ensure you can rely on a smooth upgrade experience.

We are keen for your feedback; please open an [issue](https://github.com/seekgpt/seekgpt-python/issues) with questions, bugs, or suggestions.

### Determining the installed version

You can determine the version that is being used at runtime with:

```py
import seekgpt
print(seekgpt.__version__)
```

## Requirements

Python 3.8 or higher.

## Contributing

See [the contributing documentation](./CONTRIBUTING.md).