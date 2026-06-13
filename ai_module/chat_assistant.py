"""
Chat assistant for the Placement Preparation Assistant.

Provides conversational support for interview preparation questions including
DSA, CS fundamentals, behavioral interviews, and placement strategy.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from groq import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    Groq,
    RateLimitError,
)

from ai_module.groq_client import (
    DEFAULT_MODEL,
    GroqAPIError,
    GroqClient,
    GroqClientError,
    GroqConfigurationError,
    _extract_response_text,
    _resolve_api_key,
)

logger = logging.getLogger(__name__)

BASE_SYSTEM_PROMPT = """You are an expert AI placement and interview preparation assistant.

Help students prepare for technical and non-technical interviews by answering questions on:
- Data structures and algorithms
- Core CS topics (OS, DBMS, OOP, Computer Networks)
- Coding problem-solving approaches
- System design basics
- Behavioral and HR interview questions
- Resume, projects, and placement strategy

Guidelines:
- Give clear, accurate, and interview-focused answers.
- Use concise explanations with examples when helpful.
- For coding questions, explain approach, complexity, and key edge cases.
- Encourage understanding; provide hints before full solutions when appropriate.
- Keep responses structured and practical for placement preparation.
"""


class ChatAssistantError(GroqClientError):
    """Raised when chat assistant processing fails."""


def build_system_prompt(context: Optional[dict[str, Any]] = None) -> str:
    """
    Build a system prompt enriched with optional student-specific context.

    Args:
        context: Optional session context such as target company, weak topics,
            JD analysis, roadmap, or recent performance.

    Returns:
        System prompt string for the LLM.
    """
    if not context:
        return BASE_SYSTEM_PROMPT

    context_sections: list[str] = []

    target_company = str(context.get("target_company", "")).strip()
    if target_company:
        context_sections.append(f"Target company: {target_company}")

    weak_topics = context.get("weak_topics")
    if isinstance(weak_topics, list):
        topics = [str(topic).strip() for topic in weak_topics if str(topic).strip()]
        if topics:
            context_sections.append(f"Weak topics: {', '.join(topics)}")

    for key, label in (
        ("jd_analysis", "Job description analysis"),
        ("roadmap", "Study roadmap"),
        ("performance", "Recent performance"),
    ):
        value = context.get(key)
        if isinstance(value, dict) and value:
            context_sections.append(f"{label}:\n{json.dumps(value, indent=2)}")

    if not context_sections:
        return BASE_SYSTEM_PROMPT

    return (
        BASE_SYSTEM_PROMPT
        + "\n\nUse the following student context to personalize your guidance:\n"
        + "\n\n".join(context_sections)
    )


def _validate_question(question: str) -> str:
    """Validate and normalize a student question."""
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("question must be a non-empty string.")
    return cleaned


def _validate_messages(messages: list[dict[str, str]]) -> None:
    """Ensure chat messages use supported roles and non-empty content."""
    if not messages:
        raise ChatAssistantError("Chat request must include at least one message.")

    for index, message in enumerate(messages):
        role = message.get("role")
        content = message.get("content", "")

        if role not in {"system", "user", "assistant"}:
            raise ChatAssistantError(f"messages[{index}] has an invalid role: {role!r}.")
        if not isinstance(content, str) or not content.strip():
            raise ChatAssistantError(f"messages[{index}] must include non-empty content.")


def _generate_chat_response(
    messages: list[dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: float = 0.6,
    max_tokens: Optional[int] = 1024,
    api_key: Optional[str] = None,
) -> str:
    """Send a multi-turn chat request to the Groq API."""
    _validate_messages(messages)

    resolved_model = (model or DEFAULT_MODEL).strip()
    if not resolved_model:
        raise GroqConfigurationError("Groq model is not configured.")

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
        logger.exception("Unexpected error while calling Groq chat API.")
        raise GroqAPIError("An unexpected error occurred while generating a chat response.") from exc


def ask_question(
    question: str,
    *,
    context: Optional[dict[str, Any]] = None,
    groq_client: Optional[GroqClient] = None,
) -> str:
    """
    Answer a single student interview-preparation question.

    Args:
        question: Student question text.
        context: Optional session context for personalized answers.
        groq_client: Optional Groq client for model and API key defaults.

    Returns:
        AI-generated answer text.

    Raises:
        ValueError: If the question is empty.
        GroqClientError: If the Groq API request fails.
    """
    cleaned_question = _validate_question(question)
    client = groq_client or GroqClient()

    messages = [
        {"role": "system", "content": build_system_prompt(context)},
        {"role": "user", "content": cleaned_question},
    ]

    logger.info("Answering student question (%d characters).", len(cleaned_question))

    answer = _generate_chat_response(
        messages,
        model=client.model,
        api_key=client.api_key,
    )

    logger.info("Generated chat answer (%d characters).", len(answer))
    return answer


class ChatAssistant:
    """
    Conversational AI assistant for placement preparation support.
    """

    def __init__(self, groq_client: Optional[GroqClient] = None) -> None:
        """
        Initialize the chat assistant.

        Args:
            groq_client: Shared Groq client instance. Creates one if not provided.
        """
        self.groq_client = groq_client or GroqClient()
        self.conversation_history: list[dict[str, str]] = []
        self._context: Optional[dict[str, Any]] = None

    def set_context(self, context: Optional[dict[str, Any]]) -> None:
        """Set session context applied to future chat responses."""
        self._context = context

    def chat(
        self,
        user_message: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Process a student question and return an assistant reply.

        Args:
            user_message: Latest message from the student.
            context: Optional session context (JD, roadmap, performance, etc.).

        Returns:
            AI-generated answer text.
        """
        cleaned_message = _validate_question(user_message)
        active_context = context if context is not None else self._context

        self.conversation_history.append({"role": "user", "content": cleaned_message})

        messages = [
            {"role": "system", "content": self.build_system_prompt(active_context)},
            *self.conversation_history,
        ]

        answer = _generate_chat_response(
            messages,
            model=self.groq_client.model,
            api_key=self.groq_client.api_key,
        )

        self.conversation_history.append({"role": "assistant", "content": answer})
        return answer

    def clear_history(self) -> None:
        """Reset the in-memory conversation history."""
        self.conversation_history = []

    def get_history(self) -> list[dict[str, str]]:
        """
        Return the current conversation history.

        Returns:
            List of message dicts with role and content keys.
        """
        return self.conversation_history.copy()

    def build_system_prompt(self, context: Optional[dict[str, Any]] = None) -> str:
        """
        Build a system prompt enriched with user-specific context.

        Args:
            context: Optional session context for personalized guidance.
                Falls back to session context set via `set_context`.

        Returns:
            System prompt string for the LLM.
        """
        active_context = context if context is not None else self._context
        return build_system_prompt(active_context)
