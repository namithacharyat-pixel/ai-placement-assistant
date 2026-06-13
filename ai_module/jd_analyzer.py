"""
Job Description (JD) analyzer for the Placement Preparation Assistant.

Extracts skills, technologies, and interview topics from raw job descriptions
using the Groq API and returns a validated structured JSON payload.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional, TypedDict

from ai_module.groq_client import GroqClient, GroqClientError, generate_response

logger = logging.getLogger(__name__)

REQUIRED_KEYS = ("skills", "technologies", "dsa_topics", "cs_topics")

SYSTEM_PROMPT = """You are an expert placement preparation analyst.
Analyze the given job description and extract interview-relevant information.

Return ONLY valid JSON with exactly these keys:
{
  "skills": ["list of soft and role-specific skills"],
  "technologies": ["list of tools, languages, frameworks, databases, cloud platforms"],
  "dsa_topics": ["list of data structures and algorithms topics likely tested"],
  "cs_topics": ["list of core CS topics such as OS, DBMS, Networks, OOP"]
}

Rules:
- Each value must be an array of unique, concise strings.
- Infer reasonable DSA and CS topics even if not explicitly stated in the JD.
- Do not include markdown, explanations, or extra keys.
"""

__all__ = [
    "JDAnalysis",
    "JDAnalyzer",
    "JDAnalyzerError",
    "analyze_job_description",
]


class JDAnalysis(TypedDict):
    """Structured output from job description analysis."""

    skills: list[str]
    technologies: list[str]
    dsa_topics: list[str]
    cs_topics: list[str]


class JDAnalyzerError(GroqClientError):
    """Raised when JD analysis or response parsing fails."""


def _validate_job_description(job_description: Any) -> str:
    """
    Validate job description input.

    Raises:
        ValueError: If input is missing, wrong type, or blank.
    """
    if job_description is None:
        raise ValueError("job_description must not be None.")

    if not isinstance(job_description, str):
        raise ValueError(
            f"job_description must be a string, got {type(job_description).__name__}."
        )

    cleaned = job_description.strip()
    if not cleaned:
        raise ValueError("job_description must be a non-empty string.")

    return cleaned


def _strip_code_fence(text: str) -> str:
    """Remove optional Markdown JSON code fences from model output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _parse_json_response(raw: str) -> dict[str, Any]:
    """Parse model output into a JSON object."""
    if not raw or not raw.strip():
        raise JDAnalyzerError("Groq returned an empty response for job description analysis.")

    try:
        parsed = json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse JD analysis JSON: %s", raw[:500])
        raise JDAnalyzerError(
            "Groq returned invalid JSON for job description analysis."
        ) from exc

    if not isinstance(parsed, dict):
        raise JDAnalyzerError("JD analysis response must be a JSON object.")

    return parsed


def _normalize_string_list(value: Any, field_name: str) -> list[str]:
    """Normalize a model field into a deduplicated list of non-empty strings."""
    if not isinstance(value, list):
        raise JDAnalyzerError(
            f"Expected `{field_name}` to be a list, got {type(value).__name__}."
        )

    normalized: list[str] = []
    seen: set[str] = set()

    for item in value:
        if not isinstance(item, str):
            continue

        cleaned = item.strip()
        if not cleaned:
            continue

        key = cleaned.casefold()
        if key in seen:
            continue

        seen.add(key)
        normalized.append(cleaned)

    return normalized


def _merge_topic_lists(*lists: list[str]) -> list[str]:
    """Merge multiple topic lists while preserving order and removing duplicates."""
    merged: list[str] = []
    seen: set[str] = set()

    for items in lists:
        for item in items:
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)

    return merged


def _validate_analysis(data: dict[str, Any]) -> JDAnalysis:
    """Ensure the parsed response matches the expected JD analysis schema."""
    missing_keys = [key for key in REQUIRED_KEYS if key not in data]
    if missing_keys:
        raise JDAnalyzerError(
            f"JD analysis response missing keys: {', '.join(missing_keys)}"
        )

    return JDAnalysis(
        skills=_normalize_string_list(data["skills"], "skills"),
        technologies=_normalize_string_list(data["technologies"], "technologies"),
        dsa_topics=_normalize_string_list(data["dsa_topics"], "dsa_topics"),
        cs_topics=_normalize_string_list(data["cs_topics"], "cs_topics"),
    )


def analyze_job_description(
    job_description: str,
    *,
    groq_client: Optional[GroqClient] = None,
) -> JDAnalysis:
    """
    Analyze a job description and return structured preparation insights.

    Args:
        job_description: Raw text of the job posting.
        groq_client: Optional Groq client for model and API key defaults.

    Returns:
        Dictionary with `skills`, `technologies`, `dsa_topics`, and `cs_topics`.

    Raises:
        ValueError: If `job_description` is invalid.
        JDAnalyzerError: If response parsing or validation fails.
        GroqClientError: If the Groq API request fails.
    """
    cleaned_description = _validate_job_description(job_description)
    client = groq_client or GroqClient()
    prompt = f"Analyze this job description:\n\n{cleaned_description}"

    logger.info(
        "Analyzing job description (%d characters).",
        len(cleaned_description),
    )

    try:
        raw_response = generate_response(
            prompt,
            system_prompt=SYSTEM_PROMPT,
            model=client.model,
            temperature=0.2,
            max_tokens=2048,
            api_key=client.api_key,
        )
    except GroqClientError:
        logger.exception("Groq API request failed during job description analysis.")
        raise

    parsed = _parse_json_response(raw_response)
    analysis = _validate_analysis(parsed)

    logger.info(
        "JD analysis complete: %d skills, %d technologies, %d DSA topics, %d CS topics.",
        len(analysis["skills"]),
        len(analysis["technologies"]),
        len(analysis["dsa_topics"]),
        len(analysis["cs_topics"]),
    )

    return analysis


class JDAnalyzer:
    """
    Analyzes job descriptions to produce structured preparation insights.
    """

    def __init__(self, groq_client: Optional[GroqClient] = None) -> None:
        """
        Initialize the JD analyzer.

        Args:
            groq_client: Shared Groq client instance. Creates one if not provided.
        """
        self.groq_client = groq_client or GroqClient()

    def analyze(self, job_description: str) -> JDAnalysis:
        """
        Parse a job description and return structured analysis.

        Args:
            job_description: Raw text of the job posting.

        Returns:
            Dictionary with `skills`, `technologies`, `dsa_topics`, and `cs_topics`.

        Raises:
            ValueError: If `job_description` is invalid.
            JDAnalyzerError: If response parsing or validation fails.
            GroqClientError: If the Groq API request fails.
        """
        return analyze_job_description(
            job_description,
            groq_client=self.groq_client,
        )

    def extract_skills(self, job_description: str) -> list[str]:
        """
        Extract technical and soft skills mentioned in the JD.

        Args:
            job_description: Raw text of the job posting.

        Returns:
            List of identified skill names.

        Raises:
            ValueError: If `job_description` is invalid.
            JDAnalyzerError: If response parsing or validation fails.
            GroqClientError: If the Groq API request fails.
        """
        return self.analyze(job_description)["skills"]

    def extract_topics(self, job_description: str) -> list[str]:
        """
        Extract interview-relevant DSA and CS topics from the JD.

        Args:
            job_description: Raw text of the job posting.

        Returns:
            Combined deduplicated list of DSA and CS topics.

        Raises:
            ValueError: If `job_description` is invalid.
            JDAnalyzerError: If response parsing or validation fails.
            GroqClientError: If the Groq API request fails.
        """
        analysis = self.analyze(job_description)
        return _merge_topic_lists(analysis["dsa_topics"], analysis["cs_topics"])
