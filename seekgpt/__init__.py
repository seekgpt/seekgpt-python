# seekgpt/__init__.py
"""
SeekGPT Python Client Library

A library to interact with SeekGPT and other OpenAI-compatible LLM APIs.
"""

# Define the package version
__version__ = "0.1.3" # Update this as the package evolves

# Import key components to make them available at the package level
from .client import (
    # Core Clients
    SeekGPT,
    SeekGPTClient,

    # Exceptions
    SeekGPTError,
    APIConnectionError,
    AuthenticationError,
    InvalidRequestError,
    APIError,
)

# Define what gets imported when using 'from seekgpt import *'
# It's generally better practice to import specific names, but __all__ can be useful.
__all__ = [
    # Clients
    "SeekGPT",
    "SeekGPTClient",

    # Exceptions
    "SeekGPTError",
    "APIConnectionError",
    "AuthenticationError",
    "InvalidRequestError",
    "APIError",

    # Package version
    "__version__",
]

