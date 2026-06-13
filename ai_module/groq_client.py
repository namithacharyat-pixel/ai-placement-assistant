"""
Groq API client for the AI-Powered Placement Preparation Assistant.

Provides a reusable `generate_response` helper and a `GroqClient` class
for sending prompts to Groq-hosted LLMs.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from dotenv import load_dotenv
from groq import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    Groq,
    RateLimitError,
)

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_API_KEY_ENV = "GROQ_API_KEY"
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class GroqClientError(Exception):
    """Base exception for Groq client failures."""


class GroqConfigurationError(GroqClientError):
    """Raised when required configuration is missing or invalid."""


class GroqAPIError(GroqClientError):
    """Raised when the Groq API returns an error response."""


def _resolve_api_key(api_key: Optional[str] = None) -> str:
    """Return a non-empty API key from argument or environment."""
    resolved = (api_key or os.getenv(GROQ_API_KEY_ENV) or "").strip()
    if not resolved:
        raise GroqConfigurationError(
            f"Groq API key not configured. Set `{GROQ_API_KEY_ENV}` in your `.env` file."
        )
    return resolved


def _build_messages(prompt: str, system_prompt: Optional[str] = None) -> list[dict[str, str]]:
    """Build chat message payload for the Groq API."""
    if not prompt or not prompt.strip():
        raise ValueError("prompt must be a non-empty string.")

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.append({"role": "user", "content": prompt.strip()})
    return messages


def _extract_response_text(completion: Any) -> str:
    """Extract text content from a Groq chat completion response."""
    try:
        content = completion.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise GroqAPIError("Groq returned an unexpected response format.") from exc

    if content is None or not str(content).strip():
        raise GroqAPIError("Groq returned an empty response.")

    return str(content).strip()


def generate_response(
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    api_key: Optional[str] = None,
) -> str:
    """
    Send a prompt to the Groq API and return the model's text response.

    Args:
        prompt: User message content sent to the model.
        system_prompt: Optional system instruction for the model.
        model: Groq model identifier. Defaults to `GROQ_MODEL` env or
            `llama-3.3-70b-versatile`.
        temperature: Sampling temperature (0.0 to 2.0).
        max_tokens: Optional cap on generated tokens.
        api_key: Optional API key override. Otherwise loaded from `.env`.

    Returns:
        Generated response text from the model.

    Raises:
        ValueError: If `prompt` is empty.
        GroqConfigurationError: If the API key is missing.
        GroqAPIError: If the Groq API request fails or returns invalid data.
    """
    resolved_model = (model or DEFAULT_MODEL).strip()
    if not resolved_model:
        raise GroqConfigurationError("Groq model is not configured.")

    messages = _build_messages(prompt, system_prompt)
    request_kwargs: dict[str, Any] = {
        "model": resolved_model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        request_kwargs["max_tokens"] = max_tokens

    try:
        client = Groq(api_key=_resolve_api_key(api_key))
        completion = client.chat.completions.create(**request_kwargs)
        return _extract_response_text(completion)

    except AuthenticationError as exc:
        logger.error("Groq authentication failed: invalid API key.")
        raise GroqAPIError("Authentication failed. Check your Groq API key.") from exc

    except RateLimitError as exc:
        logger.error("Groq rate limit exceeded.")
        raise GroqAPIError("Rate limit exceeded. Retry after a short delay.") from exc

    except APIConnectionError as exc:
        logger.error("Groq connection error: %s", exc)
        raise GroqAPIError("Unable to connect to Groq. Check your network.") from exc

    except APIStatusError as exc:
        logger.error("Groq API status error [%s]: %s", exc.status_code, exc.message)
        raise GroqAPIError(f"Groq API error ({exc.status_code}): {exc.message}") from exc

    except GroqClientError:
        raise

    except Exception as exc:
        logger.exception("Unexpected error while calling Groq API.")
        raise GroqAPIError("An unexpected error occurred while generating a response.") from exc


class GroqClient:
    """
    Client for interacting with the Groq API.

    Wraps `generate_response` with instance-level defaults for model and API key.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        """
        Initialize the Groq client.

        Args:
            api_key: Groq API key. If None, load from `.env`.
            model: Default model identifier for completions.
        """
        self.api_key = _resolve_api_key(api_key) if api_key else None
        self.model = model

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send a completion request to the Groq API.

        Args:
            prompt: User-facing prompt content.
            system_prompt: Optional system instruction for the model.
            temperature: Sampling temperature for response generation.
            max_tokens: Maximum tokens in the generated response.

        Returns:
            Raw text response from the model.
        """
        return generate_response(
            prompt,
            system_prompt=system_prompt,
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=self.api_key,
        )

    def complete_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """
        Send a completion request and parse the response as JSON.

        Args:
            prompt: User-facing prompt content.
            system_prompt: Optional system instruction for JSON output.
            temperature: Sampling temperature for response generation.

        Returns:
            Parsed JSON object from the model response.
        """
        raise NotImplementedError("GroqClient.complete_json is not implemented yet.")
