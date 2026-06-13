"""
Assessment generator for the Placement Preparation Assistant.

Creates customized quizzes, coding challenges, and aptitude questions
based on JD analysis and target skill areas.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from ai_module.groq_client import (
    GroqClient,
    GroqClientError,
    generate_response,
)

logger = logging.getLogger(__name__)


class AssessmentGeneratorError(GroqClientError):
    """Raised when assessment generation fails."""


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    return cleaned.strip()


def _parse_json_response(raw: str) -> dict[str, Any]:
    if not raw or not raw.strip():
        raise AssessmentGeneratorError("Groq returned an empty response.")

    try:
        return json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        raise AssessmentGeneratorError(
            "Groq returned invalid JSON."
        ) from exc


class AssessmentGenerator:
    """
    Generates placement-focused assessments tailored to a role or skill set.
    """

    def __init__(self, groq_client: Optional[GroqClient] = None) -> None:
        self.groq_client = groq_client or GroqClient()

    def generate(
        self,
        topics: list[str],
        difficulty: str = "medium",
        num_questions: int = 10,
    ) -> dict[str, Any]:
        """
        Generate full assessment.

        Returns:
        {
            "mcqs": [...],
            "coding_questions": [...]
        }
        """

        if not topics:
            raise ValueError("topics cannot be empty")

        prompt = f"""
Generate a placement assessment.

Topics:
{", ".join(topics)}

Difficulty:
{difficulty}

Number of MCQs:
{num_questions}

Generate exactly:

1. MCQs
   Each MCQ must contain:

* question
* options (4 choices)
* correct_answer
* explanation

2. Two coding questions.

Each coding question must contain:

* title
* problem_statement
* difficulty
* constraints
* sample_input
* sample_output

Return ONLY valid JSON.

Example:

{{
"mcqs": [],
"coding_questions": []
}}
"""

        raw = generate_response(
            prompt,
            model=self.groq_client.model,
            api_key=self.groq_client.api_key,
            temperature=0.4,
            max_tokens=3000,
        )

        return _parse_json_response(raw)

    def generate_mcq(
        self,
        topic: str,
        count: int = 5,
        difficulty: str = "medium",
    ) -> list[dict[str, Any]]:
        """
        Generate MCQs for a single topic.
        """

        prompt = f"""
Generate {count} multiple-choice questions.

Topic:
{topic}

Difficulty:
{difficulty}

Each question must contain:

* question
* options
* correct_answer
* explanation

Return ONLY JSON:

{{
"mcqs": [...]
}}
"""

        raw = generate_response(
            prompt,
            model=self.groq_client.model,
            api_key=self.groq_client.api_key,
            temperature=0.4,
            max_tokens=2000,
        )

        parsed = _parse_json_response(raw)

        return parsed.get("mcqs", [])

    def generate_coding_question(
        self,
        topic: str,
        difficulty: str = "medium",
    ) -> dict[str, Any]:
        """
        Generate one coding challenge.
        """

        prompt = f"""
Generate one coding interview question.

Topic:
{topic}

Difficulty:
{difficulty}

Return ONLY JSON:

{{
"title": "",
"problem_statement": "",
"difficulty": "",
"constraints": [],
"sample_input": "",
"sample_output": ""
}}
"""

        raw = generate_response(
            prompt,
            model=self.groq_client.model,
            api_key=self.groq_client.api_key,
            temperature=0.4,
            max_tokens=1500,
        )

        return _parse_json_response(raw)


def generate_assessment(
    topics: list[str],
    difficulty: str = "medium",
    num_questions: int = 10,
) -> dict[str, Any]:
    """
    Convenience wrapper.

    Example:
        generate_assessment(
            ["Arrays", "Trees", "OOPs"]
        )
    """

    generator = AssessmentGenerator()

    return generator.generate(
        topics=topics,
        difficulty=difficulty,
        num_questions=num_questions,
    )
