"""
Assessment generator for the Placement Preparation Assistant.

Creates customized quizzes, coding challenges, and aptitude questions
based on JD analysis and target skill areas. Also maintains a
persistent per-company learning memory used to adapt future
assessments to the student's demonstrated strengths and weaknesses.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import date
from typing import Any, Optional

from ai_module.groq_client import (
    GroqClient,
    GroqClientError,
    generate_response,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ASSESSMENT_HISTORY_PATH = os.path.join(DATA_DIR, "assessment_history.json")

DIFFICULTY_ORDER = ["easy", "medium", "hard"]


class AssessmentGeneratorError(GroqClientError):
    """Raised when assessment generation fails."""


# ---------------------------------------------------------------------------
# JSON / response helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Assessment History Manager
# ---------------------------------------------------------------------------
#
# History is stored in a single JSON file, keyed by a normalized company
# name. Each company entry has the shape:
#
# {
#   "solved_questions": [
#       {
#           "topic": "Arrays",
#           "difficulty": "easy",
#           "title": "Two Sum",
#           "score": 90,
#           "date": "2026-06-13"
#       },
#       ...
#   ],
#   "weak_topics": ["Trees", "Graphs"],
#   "strong_topics": ["Arrays"]
# }
# ---------------------------------------------------------------------------


def _normalize_company_name(company_name: str) -> str:
    """Normalize a company name into a stable lookup key."""

    if not company_name or not company_name.strip():
        raise ValueError("company_name cannot be empty")

    return company_name.strip().lower()


def _empty_company_record() -> dict[str, Any]:
    return {
        "solved_questions": [],
        "weak_topics": [],
        "strong_topics": [],
    }


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_full_history() -> dict[str, Any]:
    """Load the full assessment history file, creating it if missing."""

    _ensure_data_dir()

    if not os.path.exists(ASSESSMENT_HISTORY_PATH):
        return {}

    try:
        with open(ASSESSMENT_HISTORY_PATH, "r", encoding="utf-8") as fh:
            content = fh.read().strip()
    except OSError as exc:
        logger.warning("Could not read assessment history file: %s", exc)
        return {}

    if not content:
        return {}

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Assessment history file is corrupted (%s); starting fresh.", exc
        )
        return {}

    if not isinstance(data, dict):
        logger.warning("Assessment history file has unexpected shape; starting fresh.")
        return {}

    return data


def _save_full_history(data: dict[str, Any]) -> None:
    """Persist the full assessment history file."""

    _ensure_data_dir()

    try:
        with open(ASSESSMENT_HISTORY_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
    except OSError as exc:
        raise AssessmentGeneratorError(
            f"Failed to save assessment history: {exc}"
        ) from exc


def load_assessment_history(company_name: str) -> dict[str, Any]:
    """
    Load the assessment history for a given company.

    Args:
        company_name: Name of the target company (e.g. "Google").

    Returns:
        A dict with "solved_questions", "weak_topics", and
        "strong_topics" keys. Returns an empty/default record if the
        company has no history yet.
    """

    key = _normalize_company_name(company_name)
    full_history = _load_full_history()

    record = full_history.get(key)
    if record is None:
        return _empty_company_record()

    # Defensive merge in case of partially-written records.
    merged = _empty_company_record()
    merged.update(record)
    return merged


def save_assessment_history(company_name: str, data: dict[str, Any]) -> None:
    """
    Save (overwrite) the assessment history for a given company.

    Args:
        company_name: Name of the target company.
        data: The company's history record (solved_questions,
            weak_topics, strong_topics).
    """

    key = _normalize_company_name(company_name)
    full_history = _load_full_history()

    record = _empty_company_record()
    record.update(data)

    full_history[key] = record
    _save_full_history(full_history)


def _recompute_topic_strengths(record: dict[str, Any]) -> None:
    """
    Recompute weak_topics / strong_topics in-place based on the
    average score per topic across solved_questions.

    A topic is "strong" if its average score >= 80 and "weak" if its
    average score <= 50. Topics in between are left out of both lists.
    """

    topic_scores: dict[str, list[float]] = {}

    for entry in record.get("solved_questions", []):
        topic = entry.get("topic")
        score = entry.get("score")

        if topic is None or score is None:
            continue

        topic_scores.setdefault(topic, []).append(float(score))

    weak_topics: list[str] = []
    strong_topics: list[str] = []

    for topic, scores in topic_scores.items():
        avg = sum(scores) / len(scores)

        if avg >= 80:
            strong_topics.append(topic)
        elif avg <= 50:
            weak_topics.append(topic)

    record["weak_topics"] = weak_topics
    record["strong_topics"] = strong_topics


def record_question_attempt(
    company_name: str,
    topic: str,
    difficulty: str,
    title: str,
    score: float,
) -> dict[str, Any]:
    """
    Record a single solved-question attempt for a company and update
    the derived weak/strong topic lists.

    Args:
        company_name: Name of the target company.
        topic: The topic of the question (e.g. "Arrays").
        difficulty: Difficulty of the question ("easy"/"medium"/"hard").
        title: Title of the question (e.g. "Two Sum").
        score: Score achieved (0-100).

    Returns:
        The updated company history record.
    """

    if not topic or not topic.strip():
        raise ValueError("topic cannot be empty")

    if not title or not title.strip():
        raise ValueError("title cannot be empty")

    try:
        score_value = float(score)
    except (TypeError, ValueError) as exc:
        raise ValueError("score must be numeric") from exc

    if not 0 <= score_value <= 100:
        raise ValueError("score must be between 0 and 100")

    record = load_assessment_history(company_name)

    record["solved_questions"].append(
        {
            "topic": topic,
            "difficulty": difficulty.lower(),
            "title": title,
            "score": score_value,
            "date": date.today().isoformat(),
        }
    )

    _recompute_topic_strengths(record)
    save_assessment_history(company_name, record)

    return record


def get_learning_context(company_name: str, recent_n: int = 5) -> dict[str, Any]:
    """
    Build a learning-context summary for a company, suitable for
    embedding into Groq prompts (a lightweight RAG-style context).

    Args:
        company_name: Name of the target company.
        recent_n: How many of the most recent solved questions to
            include in the "recent_questions" list.

    Returns:
        A dict with keys:
            - solved_topics: sorted list of unique topics solved
            - solved_titles: list of all solved question titles
            - weak_topics: list of weak topics
            - strong_topics: list of strong topics
            - recent_questions: the most recent `recent_n` attempts
            - total_attempts: total number of recorded attempts
    """

    record = load_assessment_history(company_name)
    solved = record.get("solved_questions", [])

    solved_topics = sorted({entry.get("topic") for entry in solved if entry.get("topic")})
    solved_titles = [entry.get("title") for entry in solved if entry.get("title")]
    recent_questions = solved[-recent_n:] if recent_n > 0 else []

    return {
        "solved_topics": solved_topics,
        "solved_titles": solved_titles,
        "weak_topics": record.get("weak_topics", []),
        "strong_topics": record.get("strong_topics", []),
        "recent_questions": recent_questions,
        "total_attempts": len(solved),
    }


# ---------------------------------------------------------------------------
# Difficulty progression
# ---------------------------------------------------------------------------

def _next_difficulty(current_difficulty: str, score: float) -> str:
    """
    Determine the next difficulty level based on the score on the
    current question.

    Rules:
        - score >= 80: move up one difficulty level (capped at "hard")
        - 50 < score < 80: stay on the same difficulty
        - score <= 50 (and > 30): stay on the same difficulty
        - score <= 30: flagged for revision (caller should treat the
          returned difficulty as a "revision" of the same level)

    Args:
        current_difficulty: The difficulty just attempted.
        score: Score achieved (0-100).

    Returns:
        The recommended next difficulty level ("easy"/"medium"/"hard").
    """

    current = current_difficulty.lower().strip()
    if current not in DIFFICULTY_ORDER:
        current = "medium"

    if score >= 80:
        idx = DIFFICULTY_ORDER.index(current)
        next_idx = min(idx + 1, len(DIFFICULTY_ORDER) - 1)
        return DIFFICULTY_ORDER[next_idx]

    # score <= 80 (including the <= 50 and <= 30 revision cases) stays
    # on the same difficulty level; revision-vs-progression is handled
    # by generate_next_recommendation via the "reason" field.
    return current


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------

class AssessmentGenerator:
    """
    Generates placement-focused assessments tailored to a role or skill
    set, and adapts future assessments using a persistent per-company
    learning history.

    Internally, responsibilities are split into:
        - History management   (_load_history / _record_attempt / etc.)
        - Question generation   (generate / generate_mcq / generate_coding_question)
        - AI review             (review_solution)
        - Recommendation engine (generate_next_recommendation)
    """

    def __init__(self, groq_client: Optional[GroqClient] = None) -> None:
        self.groq_client = groq_client or GroqClient()

    # ------------------------------------------------------------------
    # History management (thin wrappers around module-level helpers,
    # kept as methods so subclasses/tests can override storage easily)
    # ------------------------------------------------------------------

    def _load_history(self, company_name: str) -> dict[str, Any]:
        """Load the stored learning history for a company."""

        return load_assessment_history(company_name)

    def _save_history(self, company_name: str, data: dict[str, Any]) -> None:
        """Persist the learning history for a company."""

        save_assessment_history(company_name, data)

    def _record_attempt(
        self,
        company_name: str,
        topic: str,
        difficulty: str,
        title: str,
        score: float,
    ) -> dict[str, Any]:
        """Record a solved-question attempt for a company."""

        return record_question_attempt(
            company_name=company_name,
            topic=topic,
            difficulty=difficulty,
            title=title,
            score=score,
        )

    def _build_learning_context(
        self, company_name: Optional[str]
    ) -> Optional[dict[str, Any]]:
        """
        Build a learning context for the given company, or None if no
        company name was provided (keeps behaviour backward compatible
        for callers that don't pass a company).
        """

        if not company_name:
            return None

        try:
            return get_learning_context(company_name)
        except ValueError:
            logger.warning("Invalid company_name '%s'; skipping learning context.", company_name)
            return None

    @staticmethod
    def _format_learning_context_block(
        company_name: Optional[str],
        context: Optional[dict[str, Any]],
    ) -> str:
        """
        Render a learning-context dict into a human-readable prompt
        block. Returns an empty string if there is no context to add.
        """

        if not context or context.get("total_attempts", 0) == 0:
            return ""

        lines: list[str] = []

        if company_name:
            lines.append(f"Student preparing for {company_name}.")

        solved_titles = context.get("solved_titles") or []
        if solved_titles:
            lines.append("Already solved questions (do not repeat or generate near-duplicates of):")
            for title in solved_titles[-10:]:
                lines.append(f"- {title}")

        recent_questions = context.get("recent_questions") or []
        if recent_questions:
            lines.append("Recent performance:")
            for entry in recent_questions:
                lines.append(
                    "- {topic} ({difficulty}): \"{title}\" scored {score}".format(
                        topic=entry.get("topic", "Unknown"),
                        difficulty=entry.get("difficulty", "unknown"),
                        title=entry.get("title", "Untitled"),
                        score=entry.get("score", "N/A"),
                    )
                )

        weak_topics = context.get("weak_topics") or []
        if weak_topics:
            lines.append("Weak topics (prioritize and go gentle on difficulty):")
            for topic in weak_topics:
                lines.append(f"- {topic}")

        strong_topics = context.get("strong_topics") or []
        if strong_topics:
            lines.append("Strong topics (safe to increase difficulty):")
            for topic in strong_topics:
                lines.append(f"- {topic}")

        if not lines:
            return ""

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Question generation
    # ------------------------------------------------------------------

    def generate(
        self,
        topics: list[str],
        difficulty: str = "medium",
        num_questions: int = 10,
        company_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate a full assessment.

        Args:
            topics: List of topics to cover.
            difficulty: Overall difficulty ("easy"/"medium"/"hard").
            num_questions: Number of MCQs to generate.
            company_name: Optional company name. When provided, the
                student's learning history for that company is used to
                adapt the generated questions (avoiding repeats and
                steering difficulty/topic focus). This parameter is
                optional and the method remains fully backward
                compatible when it is omitted.

        Returns:
            {
                "mcqs": [...],
                "coding_questions": [...]
            }
        """

        if not topics:
            raise ValueError("topics cannot be empty")

        learning_context = self._build_learning_context(company_name)
        context_block = self._format_learning_context_block(company_name, learning_context)

        prompt = f"""
{context_block}Generate a placement assessment.

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
        company_name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Generate MCQs for a single topic.

        Args:
            topic: The topic to generate MCQs for.
            count: Number of MCQs to generate.
            difficulty: Difficulty level.
            company_name: Optional company name used to fetch learning
                history and adapt the generated questions. Optional
                for backward compatibility.

        Returns:
            A list of MCQ dicts, each with "question", "options",
            "correct_answer", and "explanation".
        """

        learning_context = self._build_learning_context(company_name)
        context_block = self._format_learning_context_block(company_name, learning_context)

        prompt = f"""
{context_block}Generate {count} multiple-choice questions.

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
    category: str = "DSA",
    company_name: str | None = None,
    language: str = "java",
) -> dict[str, Any]:
        """
        Generate one coding challenge.

        Args:
            topic: The topic to generate a coding question for.
            difficulty: Difficulty level ("easy"/"medium"/"hard").
            category: Either "DSA" or "SQL" (case-insensitive).
                - "DSA" questions include starter code in Java, Python,
                  C++, and C.
                - "SQL" questions include a database schema, sample
                  data, and expected output instead of starter code.
            company_name: Optional company name used to fetch learning
                history and adapt the generated question (e.g. avoid
                repeating previously solved questions). Optional for
                backward compatibility.

        Returns:
            For category="DSA":
                {
                    "title": "", "problem_statement": "",
                    "difficulty": "", "constraints": [],
                    "sample_input": "", "sample_output": "",
                    "starter_code_java": "", "starter_code_python": "",
                    "starter_code_cpp": "", "starter_code_c": ""
                }

            For category="SQL":
                {
                    "title": "", "database_schema": "",
                    "sample_data": "", "expected_output": "",
                    "difficulty": ""
                }

        Raises:
            ValueError: If `category` is not "DSA" or "SQL".
        """

        normalized_category = category.strip().upper()
        if normalized_category not in ("DSA", "SQL"):
            raise ValueError('category must be "DSA" or "SQL"')

        learning_context = self._build_learning_context(company_name)
        context_block = self._format_learning_context_block(company_name, learning_context)

        if normalized_category == "DSA":
            response_shape = """{
"title": "",
"problem_statement": "",
"difficulty": "",
"constraints": [],
"sample_input": "",
"sample_output": "",
"starter_code_java": "",
"starter_code_python": "",
"starter_code_cpp": "",
"starter_code_c": ""
}"""
            extra_instructions = (
                "Include runnable starter code stubs (function/method "
                "signatures with any necessary boilerplate, but no "
                "solution logic) for Java, Python, C++, and C."
            )
        else:  # SQL
            response_shape = """{
"title": "",
"database_schema": "",
"sample_data": "",
"expected_output": "",
"difficulty": ""
}"""
            extra_instructions = (
                "Provide a realistic database schema (as SQL CREATE "
                "TABLE statements), representative sample data (as SQL "
                "INSERT statements or a small table), and the expected "
                "query result/output."
            )

        prompt = prompt = f"""
Generate a realistic coding interview problem.

Company:
{company_name}

Category:
{category}

Topic:
{topic}

Difficulty:
{difficulty}

Programming Language:
{language}

If language is SQL:
Generate a database schema,
sample records,
and a SQL query challenge.

If language is Java/Python/C++/C:
Generate a LeetCode-style DSA problem.

Return ONLY JSON:

{{
"title":"",
"problem_statement":"",
"difficulty":"",
"constraints":[],
"sample_input":"",
"sample_output":"",
"starter_code_java":"",
"starter_code_python":"",
"starter_code_cpp":"",
"starter_code_c":""
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

    # ------------------------------------------------------------------
    # AI code review
    # ------------------------------------------------------------------

    def review_solution(
        self,
        question: str,
        user_solution: str,
        language: str,
    ) -> dict[str, Any]:
        """
        Use Groq to evaluate a student's solution to a coding question.

        This performs AI-based evaluation ONLY -- the code is never
        executed.

        Args:
            question: The problem statement (or a description of it)
                that the solution is meant to solve.
            user_solution: The student's source code.
            language: The programming language of the solution (e.g.
                "python", "java", "cpp", "c", "sql").

        Returns:
            {
                "correctness": "",
                "time_complexity": "",
                "space_complexity": "",
                "optimization_suggestions": [],
                "interview_feedback": ""
            }

        Raises:
            ValueError: If `question` or `user_solution` is empty.
            AssessmentGeneratorError: If Groq returns an empty or
                invalid JSON response.
        """

        if not question or not question.strip():
            raise ValueError("question cannot be empty")

        if not user_solution or not user_solution.strip():
            raise ValueError("user_solution cannot be empty")

        prompt = f"""
You are an expert technical interviewer reviewing a candidate's code
submission. Do NOT execute the code -- evaluate it purely by reading it.

Problem statement:
{question}

Candidate's solution ({language}):
{user_solution}

Evaluate the solution and return ONLY JSON in this exact shape:

{{
"correctness": "",
"time_complexity": "",
"space_complexity": "",
"optimization_suggestions": [],
"interview_feedback": ""
}}

Guidance:
- "correctness": state whether the solution appears correct, partially
  correct, or incorrect, and briefly why.
- "time_complexity": Big-O time complexity with a short justification.
- "space_complexity": Big-O space complexity with a short justification.
- "optimization_suggestions": a list of concrete, actionable
  improvements (can be empty if the solution is already optimal).
- "interview_feedback": short, constructive feedback as if giving
  verbal feedback to the candidate after an interview.
"""

        raw = generate_response(
            prompt,
            model=self.groq_client.model,
            api_key=self.groq_client.api_key,
            temperature=0.3,
            max_tokens=1200,
        )

        return _parse_json_response(raw)

    # ------------------------------------------------------------------
    # Recommendation engine
    # ------------------------------------------------------------------

    def generate_next_recommendation(self, company_name: str) -> dict[str, Any]:
        """
        Recommend the next topic and difficulty for a student preparing
        for a given company, based on their recorded history.

        Args:
            company_name: Name of the target company.

        Returns:
            {
                "next_topic": "",
                "difficulty": "",
                "reason": ""
            }
        """

        history = self._load_history(company_name)
        solved = history.get("solved_questions", [])
        weak_topics = history.get("weak_topics", [])
        strong_topics = history.get("strong_topics", [])

        # No history at all -> generic starting recommendation.
        if not solved:
            return {
                "next_topic": "Arrays",
                "difficulty": "Easy",
                "reason": "No prior attempts found; starting with a foundational topic.",
            }

        last_entry = solved[-1]
        last_topic = last_entry.get("topic", "Arrays")
        last_difficulty = (last_entry.get("difficulty") or "medium").lower()
        last_score = float(last_entry.get("score", 0))

        # Severe revision case: very low score on the most recent attempt.
        if last_score <= 30:
            return {
                "next_topic": last_topic,
                "difficulty": last_difficulty.capitalize(),
                "reason": (
                    f"Score of {last_score:.0f} on '{last_entry.get('title', 'the last question')}' "
                    f"was very low; recommending revision questions on {last_topic} "
                    f"at {last_difficulty} difficulty before progressing."
                ),
            }

        # Prioritize weak topics if any exist.
        if weak_topics:
            next_topic = weak_topics[0]
            return {
                "next_topic": next_topic,
                "difficulty": "Medium",
                "reason": f"Weak topic detected in previous assessments: {next_topic}.",
            }

        # Otherwise progress difficulty on the most recently attempted topic.
        next_difficulty = _next_difficulty(last_difficulty, last_score)

        if next_difficulty == last_difficulty:
            reason = (
                f"Score of {last_score:.0f} on the last {last_topic} question "
                f"suggests more practice at {next_difficulty} difficulty before moving on."
            )
        else:
            reason = (
                f"Strong score of {last_score:.0f} on the last {last_topic} question; "
                f"ready to progress to {next_difficulty} difficulty."
            )

        # If the student is strong in their last topic and there's a
        # different strong topic, gently nudge toward broadening.
        if strong_topics and last_topic in strong_topics and len(strong_topics) > 0:
            next_topic = last_topic
        else:
            next_topic = last_topic

        return {
            "next_topic": next_topic,
            "difficulty": next_difficulty.capitalize(),
            "reason": reason,
        }


# ---------------------------------------------------------------------------
# Module-level convenience wrappers (backward compatible)
# ---------------------------------------------------------------------------

def generate_assessment(
    topics: list[str],
    difficulty: str = "medium",
    num_questions: int = 10,
    company_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    Convenience wrapper.

    Example:
        generate_assessment(
            ["Arrays", "Trees", "OOPs"]
        )

    Args:
        topics: List of topics to cover.
        difficulty: Overall difficulty.
        num_questions: Number of MCQs to generate.
        company_name: Optional company name for adaptive generation
            based on learning history.
    """

    generator = AssessmentGenerator()

    return generator.generate(
        topics=topics,
        difficulty=difficulty,
        num_questions=num_questions,
        company_name=company_name,
    )
