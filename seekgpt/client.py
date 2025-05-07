# seekgpt/client.py
import os
import requests
import json
import logging
from typing import List, Dict, Optional, Union, Iterator, Any
from dotenv import load_dotenv

load_dotenv()
# Configure logging - default to WARNING, override with SEEKGPT_LOGLEVEL env var
log_level = os.environ.get("SEEKGPT_LOGLEVEL", "WARNING").upper()
logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Custom Exceptions ---
class SeekGPTError(Exception):
    """Base exception class for the seekgpt library."""
    def __init__(self, message: str, http_status: Optional[int] = None, response_body: Optional[Union[str, bytes]] = None):
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.response_body = response_body

    def __str__(self) -> str:
        msg = self.message
        if self.http_status:
            msg += f" (HTTP Status: {self.http_status})"
        # Avoid printing potentially huge response bodies in the default __str__
        # if self.response_body:
        #     try:
        #         body_str = self.response_body.decode('utf-8') if isinstance(self.response_body, bytes) else str(self.response_body)
        #         msg += f"\nResponse Body: {body_str[:500]}..." # Truncate long bodies
        #     except Exception:
        #         msg += "\nResponse Body: <Could not decode or display>"
        return msg

class APIConnectionError(SeekGPTError):
    """Exception for network-related issues (DNS failure, refused connection, timeout, etc)."""
    pass

class AuthenticationError(SeekGPTError):
    """Exception for authentication issues (401 or 403 errors)."""
    pass

class InvalidRequestError(SeekGPTError):
    """Exception for invalid request parameters or structure (400, 422 errors), or rate limits (429)."""
    pass

class APIError(SeekGPTError):
    """Exception for other API errors (non-2xx responses not covered above, e.g., 5xx)."""
    pass


# --- Base Client ---
class SeekGPT:
    """
    A base client for interacting with OpenAI-compatible LLM APIs.

    Allows connection to various endpoints by specifying the api_base URL
    and api_key. Handles common request patterns, authentication, and errors.
    """
    DEFAULT_API_BASE = "https://api.seekgpt.org/v1"
    REQUEST_TIMEOUT = 60 # seconds

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[int] = None,
        # Allow passing a custom requests session
        session: Optional[requests.Session] = None,
    ):
        """
        Initializes the SeekGPT.

        Args:
            api_key: The API key for authentication. Defaults to SEEKGPT_API_KEY
                     environment variable, with fallbacks to common keys like
                     OPENAI_API_KEY if SEEKGPT_API_KEY is not set.
            api_base: The base URL for the API endpoint (e.g., "https://api.openai.com/v1").
                      Defaults to SEEKGPT_API_BASE env var or "https://api.seekgpt.org/v1".
            default_model: The default model name to use if not specified in method calls.
                           Defaults to SEEKGPT_DEFAULT_MODEL env var.
            timeout: Request timeout in seconds. Defaults to 60.
            session: An optional requests.Session object to use for making requests.
                     If None, a new session is created.
        """
        self.api_base = (api_base or os.getenv("SEEKGPT_API_BASE") or self.DEFAULT_API_BASE).rstrip('/')
        self.api_key = api_key or os.getenv("SEEKGPT_API_KEY")

        # Fallback to common API key env vars if SEEKGPT_API_KEY is missing
        if not self.api_key:
            fallback_keys = [
                "OPENAI_API_KEY",
                "ANYSCALE_API_KEY",
                "TOGETHER_API_KEY",
                # Add other relevant keys here
                # Note: Anthropic/Cohere use different auth/SDKs, less likely to be set here for this client
            ]
            for key_name in fallback_keys:
                key_value = os.getenv(key_name)
                if key_value:
                    self.api_key = key_value
                    logger.warning(f"SEEKGPT_API_KEY not set, falling back to use {key_name}.")
                    break

        self.default_model = default_model or os.getenv("SEEKGPT_DEFAULT_MODEL")
        self.timeout = timeout if timeout is not None else self.REQUEST_TIMEOUT

        # Use provided session or create a new one
        self._session = session or requests.Session()

        logger.info(f"Initialized SeekGPT with API base: {self.api_base}")
        if not self.api_key and not self._is_local_host():
             logger.warning("API key not provided or found in environment variables. Requests to non-local APIs might fail authentication.")

    def _is_local_host(self) -> bool:
        """Checks if the api_base points to a local address."""
        # Check common local hostnames and IPs
        return any(host in self.api_base for host in ["localhost", "127.0.0.1", "0.0.0.0"])

    def _get_headers(self) -> Dict[str, str]:
        """Constructs standard request headers, primarily for authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json", # Default, can be overridden for streaming if needed
            # Consider adding a User-Agent header
            # "User-Agent": f"seekgpt-python/{__version__}" # Requires importing __version__
        }
        # Most OpenAI-compatible APIs use Bearer token
        if self.api_key:
            # Note: For APIs like Anthropic that use different schemes (e.g., x-api-key),
            # using their dedicated SDK is strongly recommended. This client assumes
            # Bearer token auth typical for OpenAI-compatible endpoints.
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif not self._is_local_host():
            # Log a warning if no key is provided for a non-local host,
            # even if we don't raise an error immediately.
            logger.warning(f"Making request to non-local host {self.api_base} without an API key.")

        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], Iterator[str]]:
        """
        Makes an HTTP request to the specified API endpoint.

        Args:
            method: HTTP method (e.g., 'post', 'get').
            endpoint: API endpoint path relative to api_base (e.g., 'chat/completions').
            data: JSON payload for the request body (for POST/PUT requests).
            stream: Whether to stream the response (typically for SSE).

        Returns:
            If stream=False, returns the parsed JSON response as a dictionary.
            If stream=True, returns an iterator yielding raw response lines (str).

        Raises:
            AuthenticationError: If API key is missing for non-local endpoints or auth fails (401/403).
            APIConnectionError: If connection fails (network error, timeout).
            InvalidRequestError: For bad request parameters (400/422) or rate limits (429).
            APIError: For other non-2xx API errors (e.g., 5xx server errors).
            SeekGPTError: For unexpected errors during the request or response processing.
        """
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        # Adjust Accept header for streaming if necessary (though usually not required for SSE)
        if stream:
            headers["Accept"] = "text/event-stream"

        # Log request details (be careful with sensitive data if logging request body)
        logger.debug(f"Request: {method.upper()} {url}")
        logger.debug(f"Headers: { {k: v for k, v in headers.items() if k.lower() != 'authorization'} }") # Hide Auth header
        if data and not stream and logger.isEnabledFor(logging.DEBUG):
             try:
                 log_data = json.dumps(data, indent=2)
                 logger.debug(f"Request Data:\n{log_data}")
             except TypeError:
                 logger.debug("Request Data: <Non-serializable data>")
        elif data and stream:
             logger.debug("Request Data: <Streaming request, data not logged>")


        try:
            response = self._session.request(
                method,
                url,
                headers=headers,
                json=data if method.lower() in ['post', 'put', 'patch'] else None,
                params=data if method.lower() == 'get' else None, # Pass data as params for GET
                stream=stream,
                timeout=self.timeout
            )

            logger.debug(f"Response Status Code: {response.status_code}")
            # Log response headers only if debugging is enabled
            if logger.isEnabledFor(logging.DEBUG):
                 logger.debug(f"Response Headers: {response.headers}")

            # Check for HTTP errors first
            response.raise_for_status() # Raises requests.exceptions.HTTPError for 4xx/5xx

            # Process successful response
            if stream:
                # Return an iterator for streaming responses (Server-Sent Events)
                def sse_iterator():
                    try:
                        for line in response.iter_lines():
                            if line:
                                decoded_line = line.decode('utf-8')
                                logger.debug(f"Stream line received: {decoded_line}")
                                yield decoded_line # Yield the raw SSE line
                    except requests.exceptions.ChunkedEncodingError as e:
                        logger.error(f"Chunked encoding error during streaming from {url}: {e}")
                        raise APIConnectionError(f"Stream connection error: {e}", http_status=response.status_code, response_body=response.content) from e
                    except Exception as e:
                        logger.error(f"Unexpected error during streaming from {url}: {e}")
                        raise SeekGPTError(f"Error reading stream: {e}") from e
                    finally:
                        response.close()
                        logger.debug(f"Stream closed for {url}")
                return sse_iterator()
            else:
                # Return parsed JSON for non-streaming responses
                try:
                    json_response = response.json()
                    if logger.isEnabledFor(logging.DEBUG):
                         logger.debug(f"Response JSON:\n{json.dumps(json_response, indent=2)}")
                    return json_response
                except json.JSONDecodeError as e:
                     logger.error(f"Failed to decode JSON response from {url}. Status: {response.status_code}. Body: {response.text[:500]}...")
                     raise APIError(f"Failed to decode API response body as JSON: {e}", http_status=response.status_code, response_body=response.text) from e

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out after {self.timeout}s to {url}: {e}")
            raise APIConnectionError(f"Request timed out: {e}") from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Could not connect to {url}. Error: {e}")
            raise APIConnectionError(f"Connection error to {self.api_base}: {e}") from e
        except requests.exceptions.HTTPError as e:
            # Handle errors raised by response.raise_for_status()
            http_status = e.response.status_code
            response_body = e.response.text # Or e.response.content for binary
            logger.error(f"HTTP error {http_status} for {method.upper()} {url}. Response: {response_body[:500]}...")

            # Try to parse error details from the response body if it's JSON
            error_message = f"API request failed with status {http_status}"
            try:
                err_data = e.response.json()
                # Look for common error message structures
                if isinstance(err_data.get("error"), dict):
                    error_message = err_data["error"].get("message", error_message)
                elif isinstance(err_data.get("error"), str):
                     error_message = err_data["error"]
                elif isinstance(err_data.get("detail"), str): # FastAPI/Starlette style
                     error_message = err_data["detail"]
                elif isinstance(err_data.get("message"), str): # Other common patterns
                     error_message = err_data["message"]

            except json.JSONDecodeError:
                logger.warning(f"Could not parse error response body as JSON for status {http_status}.")
                # Use the raw response body (truncated) if it's not JSON or parsing fails
                error_message = f"API request failed with status {http_status}. Response: {response_body[:200]}"


            # Raise specific exceptions based on status code
            if http_status in (401, 403):
                raise AuthenticationError(error_message, http_status=http_status, response_body=response_body) from e
            elif http_status in (400, 422):
                raise InvalidRequestError(error_message, http_status=http_status, response_body=response_body) from e
            elif http_status == 429:
                 raise InvalidRequestError(f"Rate limit exceeded: {error_message}", http_status=http_status, response_body=response_body) from e
            else: # Other 4xx or 5xx errors
                raise APIError(error_message, http_status=http_status, response_body=response_body) from e
        except Exception as e:
             # Catch any other unexpected errors during the request process
             logger.exception(f"An unexpected error occurred during the API request to {url}: {e}") # Use logger.exception to include traceback
             raise SeekGPTError(f"An unexpected error occurred: {e}") from e

    # --- Core API Methods ---

    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs: Any # Allow passing arbitrary parameters like temperature, max_tokens, etc.
    ) -> Union[Dict[str, Any], Iterator[str]]:
        """
        Sends a chat request to the LLM using the standard OpenAI chat/completions format.

        Args:
            messages: A list of message dictionaries, following the OpenAI format, e.g.,
                      [{'role': 'system', 'content': 'You are helpful'},
                       {'role': 'user', 'content': 'Hello!'}].
                      Content can be a string or a list for multimodal models
                      (e.g., [{'type': 'text', 'text': '...'}, {'type': 'image_url', ...}]).
            model: The model name to use (e.g., 'gpt-4o', 'llama3', 'claude-3-opus-20240229').
                   Overrides the client's default_model if provided. If neither is set,
                   raises ValueError.
            stream: If True, returns an iterator yielding raw Server-Sent Event lines (str).
                    If False (default), returns the complete JSON response dictionary.
            **kwargs: Additional parameters to pass directly to the API endpoint
                      (e.g., temperature, max_tokens, top_p, tools, tool_choice).

        Returns:
            If stream=False: A dictionary containing the parsed API response.
            If stream=True: An iterator yielding raw string lines from the SSE stream.
                            You'll need to parse these lines (e.g., remove "data: " prefix,
                            handle "[DONE]").

        Raises:
            ValueError: If no model is specified (neither in the method call nor as client default).
            AuthenticationError: If authentication fails.
            APIConnectionError: If the connection to the API fails.
            InvalidRequestError: If the request format is invalid or rate limited.
            APIError: For other server-side errors.
            SeekGPTError: For other unexpected issues.
        """
        target_model = model or self.default_model
        if not target_model:
            raise ValueError("A 'model' must be specified either during client initialization "
                             "or in the chat() method call.")

        endpoint = "chat/completions"
        logger.info(f"Sending chat request to model '{target_model}' via {endpoint} (stream={stream})")

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": stream,
            **kwargs # Include any additional parameters passed
        }

        # Remove keys with None values, as some APIs might reject them
        payload = {k: v for k, v in payload.items() if v is not None}

        return self._request(method="post", endpoint=endpoint, data=payload, stream=stream)

    # --- Potential Future Methods (Examples) ---

    # def embeddings(
    #     self,
    #     input: Union[str, List[str]],
    #     model: Optional[str] = None,
    #     **kwargs: Any
    # ) -> Dict[str, Any]:
    #     """
    #     Generates embeddings for the given input text(s).

    #     Args:
    #         input: A single string or a list of strings to embed.
    #         model: The embedding model name to use. Must be specified if no
    #                default embedding model is configured for the client.
    #         **kwargs: Additional parameters for the embeddings endpoint (e.g., encoding_format).

    #     Returns:
    #         A dictionary containing the embedding results.

    #     Raises:
    #         ValueError: If no embedding model is specified.
    #         # ... other exceptions from _request ...
    #     """
    #     # Note: Need to decide how to handle default embedding model (different from chat model)
    #     target_model = model # or self.default_embedding_model
    #     if not target_model:
    #         raise ValueError("An embedding 'model' must be specified.")

    #     endpoint = "embeddings"
    #     logger.info(f"Requesting embeddings using model '{target_model}' via {endpoint}")

    #     payload = {
    #         "input": input,
    #         "model": target_model,
    #         **kwargs
    #     }
    #     payload = {k: v for k, v in payload.items() if v is not None}

    #     # Embedding requests are typically not streamed
    #     response = self._request(method="post", endpoint=endpoint, data=payload, stream=False)
    #     # Ensure response is a dict before returning (it should be if stream=False)
    #     if not isinstance(response, dict):
    #          raise APIError(f"Unexpected response type for embeddings: {type(response)}", response_body=str(response))
    #     return response


    # def list_models(self) -> Dict[str, Any]:
    #     """
    #     Lists available models from the API endpoint (if supported).

    #     Returns:
    #         A dictionary containing the list of models, typically under a 'data' key.

    #     Raises:
    #         APIError: If the endpoint doesn't support model listing (e.g., 404) or other errors occur.
    #         # ... other exceptions from _request ...
    #     """
    #     endpoint = "models"
    #     logger.info(f"Requesting list of models from {endpoint}")
    #     try:
    #         response = self._request(method="get", endpoint=endpoint, stream=False)
    #         # Ensure response is a dict before returning
    #         if not isinstance(response, dict):
    #              raise APIError(f"Unexpected response type for list_models: {type(response)}", response_body=str(response))
    #         return response
    #     except APIError as e:
    #          # Handle cases where the /models endpoint might not exist gracefully
    #          if e.http_status == 404:
    #              logger.warning(f"The API endpoint {self.api_base}/{endpoint} was not found. Model listing may not be supported.")
    #              # Return an empty structure or re-raise depending on desired behavior
    #              # Re-raising might be better to signal the feature isn't available
    #              raise APIError(f"Model listing endpoint not found (404).", http_status=404) from e
    #          raise # Re-raise other APIErrors


# --- SeekGPT Specific Client ---
class SeekGPTClient(SeekGPT):
    """
    A client specifically configured for the default SeekGPT API.

    Inherits from SeekGPT but defaults `api_base` to SeekGPT's endpoint
    and prioritizes the `SEEKGPT_API_KEY`.
    """
    SEEKGPT_DEFAULT_BASE = "https://api.seekgpt.org/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[int] = None,
        session: Optional[requests.Session] = None,
        ):
        """
        Initializes the SeekGPTClient.

        Args:
            api_key: Your SeekGPT API key. Defaults strictly to the SEEKGPT_API_KEY
                     environment variable if not provided directly. Raises an error
                     if neither is found.
            default_model: Default SeekGPT model to use. Defaults to SEEKGPT_DEFAULT_MODEL env var.
            timeout: Request timeout in seconds. Defaults to 60.
            session: An optional requests.Session object.
        """
        # Prioritize direct argument, then specific env var for SeekGPTClient
        resolved_api_key = api_key or os.getenv("SEEKGPT_API_KEY")

        # SeekGPTClient requires the SeekGPT key specifically.
        if not resolved_api_key:
            raise AuthenticationError(
                "SeekGPT API key is missing. Pass `api_key` argument or set the "
                "SEEKGPT_API_KEY environment variable.", http_status=401
            )

        super().__init__(
            api_key=resolved_api_key,
            # Explicitly use the SeekGPT default base URL, ignoring SEEKGPT_API_BASE env var for this specific client
            api_base=self.SEEKGPT_DEFAULT_BASE,
            default_model=default_model or os.getenv("SEEKGPT_DEFAULT_MODEL"),
            timeout=timeout,
            session=session,
        )
        logger.info(f"Initialized SeekGPTClient for endpoint: {self.api_base}")

