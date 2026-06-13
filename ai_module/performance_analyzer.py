"""
Performance analyzer for the Placement Preparation Assistant.

Evaluates student answers against correct answers, computes scores and
topic strengths, and returns structured JSON with personalized recommendations.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional, TypedDict

from ai_module.groq_client import GroqClient, GroqClientError, generate_response

logger = logging.getLogger(__name__)

REQUIRED_REPORT_KEYS = ("score", "strong_topics", "weak_topics", "recommendations")
STRONG_TOPIC_THRESHOLD = 0.8
WEAK_TOPIC_THRESHOLD = 0.6

RECOMMENDATIONS_SYSTEM_PROMPT = """You are an expert placement preparation coach.
Given a student's assessment performance summary, provide actionable study recommendations.

Return ONLY valid JSON with exactly this shape:
{
  "recommendations": [
    "Specific, concise recommendation tied to weak topics or overall score"
  ]
}

Rules:
- Provide 3 to 5 recommendations.
- Focus on weak topics first, then general improvement strategies if needed.
- Keep each recommendation practical and interview-focused.
- Do not include markdown, explanations, or extra keys.
"""


class PerformanceReport(TypedDict):
    """Structured performance analysis output."""

    score: float
    strong_topics: list[str]
    weak_topics: list[str]
    recommendations: list[str]


class NormalizedAnswer(TypedDict):
    """Internal normalized answer record."""

    question_id: str
    topic: str
    answer: str


class PerformanceAnalyzerError(GroqClientError):
    """Raised when performance analysis or response parsing fails."""


def _strip_code_fence(text: str) -> str:
    """Remove optional Markdown JSON code fences from model output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _parse_json_response(raw: str) -> dict[str, Any]:
    """Parse model output into a JSON object."""
    try:
        return json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse performance analysis JSON: %s", raw[:500])
        raise PerformanceAnalyzerError(
            "Groq returned invalid JSON for performance recommendations."
        ) from exc


def _normalize_string_list(value: Any, field_name: str) -> list[str]:
    """Normalize a field into a deduplicated list of non-empty strings."""
    if not isinstance(value, list):
        raise PerformanceAnalyzerError(
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


def _normalize_answer_value(value: Any) -> str:
    """Convert an answer value to a comparable string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value).strip()
    return str(value).strip()


def _normalize_answers(answers: Any, label: str) -> dict[str, NormalizedAnswer]:
    """
    Normalize answer input into a question_id-keyed mapping.

    Supported formats:
    - List of dicts with `question_id`, `topic`, and `answer`
    - Dict keyed by question_id with values as answer strings or dicts
    """
    if answers is None:
        raise ValueError(f"{label} must not be None.")

    normalized: dict[str, NormalizedAnswer] = {}

    if isinstance(answers, list):
        for index, item in enumerate(answers):
            if not isinstance(item, dict):
                raise ValueError(f"{label}[{index}] must be a dictionary.")

            question_id = str(item.get("question_id", "")).strip()
            topic = str(item.get("topic", "General")).strip() or "General"
            answer = _normalize_answer_value(item.get("answer"))

            if not question_id:
                raise ValueError(f"{label}[{index}] is missing `question_id`.")

            normalized[question_id] = NormalizedAnswer(
                question_id=question_id,
                topic=topic,
                answer=answer,
            )
        return normalized

    if isinstance(answers, dict):
        for question_id, item in answers.items():
            qid = str(question_id).strip()
            if not qid:
                raise ValueError(f"{label} contains an empty question ID.")

            if isinstance(item, dict):
                topic = str(item.get("topic", "General")).strip() or "General"
                answer = _normalize_answer_value(item.get("answer"))
            else:
                topic = "General"
                answer = _normalize_answer_value(item)

            normalized[qid] = NormalizedAnswer(
                question_id=qid,
                topic=topic,
                answer=answer,
            )
        return normalized

    raise ValueError(f"{label} must be a list or dictionary.")


def _compare_answers(
    student_answers: dict[str, NormalizedAnswer],
    correct_answers: dict[str, NormalizedAnswer],
) -> tuple[float, dict[str, dict[str, int]]]:
    """
    Compare student and correct answers.

    Returns:
        Overall score percentage and per-topic stats with correct/total counts.
    """
    if not correct_answers:
        raise ValueError("correct_answers must not be empty.")

    missing_ids = sorted(set(correct_answers) - set(student_answers))
    if missing_ids:
        raise ValueError(
            "student_answers is missing responses for question IDs: "
            + ", ".join(missing_ids)
        )

    topic_stats: dict[str, dict[str, int]] = {}
    correct_count = 0
    total_count = len(correct_answers)

    for question_id, correct in correct_answers.items():
        student = student_answers[question_id]
        topic = correct.get("topic") or student.get("topic") or "General"

        if topic not in topic_stats:
            topic_stats[topic] = {"correct": 0, "total": 0}

        topic_stats[topic]["total"] += 1

        is_correct = student["answer"].casefold() == correct["answer"].casefold()
        if is_correct:
            correct_count += 1
            topic_stats[topic]["correct"] += 1

    score = round((correct_count / total_count) * 100, 2)
    return score, topic_stats


def _classify_topics(topic_stats: dict[str, dict[str, int]]) -> tuple[list[str], list[str]]:
    """Split topics into strong and weak areas based on accuracy thresholds."""
    strong_topics: list[str] = []
    weak_topics: list[str] = []

    for topic, stats in sorted(topic_stats.items()):
        total = stats["total"]
        if total == 0:
            continue

        accuracy = stats["correct"] / total
        if accuracy >= STRONG_TOPIC_THRESHOLD:
            strong_topics.append(topic)
        elif accuracy < WEAK_TOPIC_THRESHOLD:
            weak_topics.append(topic)

    return strong_topics, weak_topics


def _fallback_recommendations(
    score: float,
    weak_topics: list[str],
    strong_topics: list[str],
) -> list[str]:
    """Generate deterministic recommendations when Groq is unavailable."""
    recommendations: list[str] = []

    for topic in weak_topics:
        recommendations.append(
            f"Revise core concepts and practice timed questions on {topic}."
        )

    if score < 60:
        recommendations.append(
            "Build a daily revision plan focusing on fundamentals before advanced problems."
        )
    elif score < 80:
        recommendations.append(
            "Review incorrect answers and drill weak topics with mixed mock assessments."
        )
    elif not weak_topics:
        recommendations.append(
            "Maintain momentum with mixed mock tests and interview-style problem sets."
        )

    if strong_topics:
        recommendations.append(
            "Keep reinforcing strong areas: "
            + ", ".join(strong_topics[:3])
            + "."
        )

    return recommendations[:5]


def _generate_recommendations(
    score: float,
    strong_topics: list[str],
    weak_topics: list[str],
    topic_stats: dict[str, dict[str, int]],
    *,
    groq_client: Optional[GroqClient] = None,
) -> list[str]:
    """Generate personalized recommendations using Groq."""
    client = groq_client or GroqClient()

    topic_breakdown = {
        topic: {
            "correct": stats["correct"],
            "total": stats["total"],
            "accuracy_percent": round((stats["correct"] / stats["total"]) * 100, 2),
        }
        for topic, stats in topic_stats.items()
        if stats["total"] > 0
    }

    prompt = (
        "Generate study recommendations for this assessment performance:\n\n"
        + json.dumps(
            {
                "score": score,
                "strong_topics": strong_topics,
                "weak_topics": weak_topics,
                "topic_breakdown": topic_breakdown,
            },
            indent=2,
        )
    )

    try:
        raw_response = generate_response(
            prompt,
            system_prompt=RECOMMENDATIONS_SYSTEM_PROMPT,
            model=client.model,
            temperature=0.4,
            max_tokens=1024,
            api_key=client.api_key,
        )
        parsed = _parse_json_response(raw_response)
        recommendations = _normalize_string_list(parsed.get("recommendations"), "recommendations")

        if not recommendations:
            raise PerformanceAnalyzerError("Groq returned an empty recommendations list.")

        return recommendations

    except GroqClientError:
        logger.warning("Groq recommendation generation failed; using fallback recommendations.")
        return _fallback_recommendations(score, weak_topics, strong_topics)


def _validate_report(data: dict[str, Any]) -> PerformanceReport:
    """Ensure the performance report matches the expected schema."""
    missing_keys = [key for key in REQUIRED_REPORT_KEYS if key not in data]
    if missing_keys:
        raise PerformanceAnalyzerError(
            f"Performance report missing keys: {', '.join(missing_keys)}"
        )

    score = data["score"]
    if not isinstance(score, (int, float)):
        raise PerformanceAnalyzerError("Expected `score` to be a number.")
    if score < 0 or score > 100:
        raise PerformanceAnalyzerError("`score` must be between 0 and 100.")

    return PerformanceReport(
        score=round(float(score), 2),
        strong_topics=_normalize_string_list(data["strong_topics"], "strong_topics"),
        weak_topics=_normalize_string_list(data["weak_topics"], "weak_topics"),
        recommendations=_normalize_string_list(data["recommendations"], "recommendations"),
    )


def analyze_performance(
    student_answers: Any,
    correct_answers: Any,
    *,
    groq_client: Optional[GroqClient] = None,
) -> PerformanceReport:
    """
    Analyze student performance against correct answers.

    Args:
        student_answers: Student responses as a list or dict of answer records.
        correct_answers: Correct answers in the same format as student answers.
        groq_client: Optional Groq client for generating recommendations.

    Returns:
        Structured report with score, strong_topics, weak_topics, and recommendations.

    Raises:
        ValueError: If inputs are invalid or incomplete.
        PerformanceAnalyzerError: If response validation fails.
        GroqClientError: If the Groq API request fails before fallback is applied.
    """
    normalized_student = _normalize_answers(student_answers, "student_answers")
    normalized_correct = _normalize_answers(correct_answers, "correct_answers")

    score, topic_stats = _compare_answers(normalized_student, normalized_correct)
    strong_topics, weak_topics = _classify_topics(topic_stats)
    recommendations = _generate_recommendations(
        score,
        strong_topics,
        weak_topics,
        topic_stats,
        groq_client=groq_client,
    )

    report = PerformanceReport(
        score=score,
        strong_topics=strong_topics,
        weak_topics=weak_topics,
        recommendations=recommendations,
    )

    logger.info(
        "Performance analysis complete: score=%.2f, strong=%d, weak=%d, recommendations=%d.",
        report["score"],
        len(report["strong_topics"]),
        len(report["weak_topics"]),
        len(report["recommendations"]),
    )

    return _validate_report(report)


class PerformanceAnalyzer:
    """
    Analyzes assessment results and user submissions to measure readiness.
    """

    def __init__(self, groq_client: Optional[GroqClient] = None) -> None:
        """
        Initialize the performance analyzer.

        Args:
            groq_client: Shared Groq client instance. Creates one if not provided.
        """
        self.groq_client = groq_client or GroqClient()

    def analyze_submission(
        self,
        assessment: dict[str, Any],
        user_answers: dict[str, Any],
    ) -> PerformanceReport:
        """
        Score a completed assessment and produce a performance summary.

        Args:
            assessment: Assessment payload containing a `questions` list with
                `question_id`, `topic`, and `correct_answer` fields.
            user_answers: User's submitted answers keyed by question ID.

        Returns:
            Performance report with score, topic breakdown, and recommendations.
        """
        questions = assessment.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError("assessment must contain a non-empty `questions` list.")

        correct_answers: list[dict[str, Any]] = []
        student_answers: list[dict[str, Any]] = []

        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                raise ValueError(f"assessment.questions[{index}] must be a dictionary.")

            question_id = str(
                question.get("question_id") or question.get("id") or ""
            ).strip()
            if not question_id:
                raise ValueError(f"assessment.questions[{index}] is missing `question_id`.")

            topic = str(question.get("topic", "General")).strip() or "General"
            correct_answer = question.get("correct_answer", question.get("answer"))
            if correct_answer is None:
                raise ValueError(
                    f"assessment.questions[{index}] is missing `correct_answer`."
                )

            if question_id not in user_answers:
                raise ValueError(
                    f"user_answers is missing a response for question ID `{question_id}`."
                )

            correct_answers.append(
                {
                    "question_id": question_id,
                    "topic": topic,
                    "answer": correct_answer,
                }
            )
            student_answers.append(
                {
                    "question_id": question_id,
                    "topic": topic,
                    "answer": user_answers[question_id],
                }
            )

        return analyze_performance(
            student_answers,
            correct_answers,
            groq_client=self.groq_client,
        )

    def identify_weak_areas(
        self,
        performance_history: list[dict[str, Any]],
    ) -> list[str]:
        """
        Identify recurring weak topics from historical performance data.

        Args:
            performance_history: List of past performance report objects.

        Returns:
            Ordered list of topics requiring additional preparation.
        """
        if not performance_history:
            return []

        topic_misses: dict[str, int] = {}

        for report in performance_history:
            if not isinstance(report, dict):
                continue
            for topic in report.get("weak_topics", []):
                if isinstance(topic, str) and topic.strip():
                    key = topic.strip()
                    topic_misses[key] = topic_misses.get(key, 0) + 1

        return [
            topic
            for topic, _ in sorted(topic_misses.items(), key=lambda item: (-item[1], item[0]))
        ]

    def generate_feedback(
        self,
        question: dict[str, Any],
        user_answer: Any,
        is_correct: bool,
    ) -> str:
        """
        Generate personalized feedback for a single question response.

        Args:
            question: Question object from the assessment.
            user_answer: User's submitted answer.
            is_correct: Whether the answer was marked correct.

        Returns:
            Human-readable feedback explaining the result and next steps.
        """
        topic = str(question.get("topic", "this topic")).strip() or "this topic"
        correct_answer = question.get("correct_answer", question.get("answer", "N/A"))
        prompt = (
            "Provide concise interview-prep feedback for one assessment question.\n\n"
            f"Topic: {topic}\n"
            f"Question: {question.get('question', question.get('prompt', 'N/A'))}\n"
            f"Student answer: {_normalize_answer_value(user_answer)}\n"
            f"Correct answer: {_normalize_answer_value(correct_answer)}\n"
            f"Result: {'Correct' if is_correct else 'Incorrect'}\n\n"
            "Reply in 2-3 sentences with encouragement and one concrete next step."
        )

        return generate_response(
            prompt,
            system_prompt="You are a supportive placement preparation mentor.",
            model=self.groq_client.model,
            temperature=0.5,
            max_tokens=256,
            api_key=self.groq_client.api_key,
        )
