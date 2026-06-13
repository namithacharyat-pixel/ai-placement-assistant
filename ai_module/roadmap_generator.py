"""
Roadmap generator for the Placement Preparation Assistant.

Builds a personalized 3-week study roadmap from weak topics and a target
company using the Groq API.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any, Optional, TypedDict

from ai_module.groq_client import GroqClient, GroqClientError, generate_response

logger = logging.getLogger(__name__)

ROADMAP_WEEKS = 3
DAYS_PER_WEEK = 7

SYSTEM_PROMPT = """You are an expert placement preparation coach.
Create a focused 3-week study roadmap for a student targeting a specific company.

Return ONLY valid JSON with exactly this shape:
{
  "target_company": "Company name",
  "weak_topics": ["topic1", "topic2"],
  "duration_weeks": 3,
  "weeks": [
    {
      "week": 1,
      "title": "Week theme title",
      "focus_topics": ["topics emphasized this week"],
      "goals": ["measurable weekly goals"],
      "daily_plan": [
        {
          "day": 1,
          "topics": ["topics for the day"],
          "tasks": ["specific study tasks"],
          "hours": 2
        }
      ]
    }
  ]
}

Rules:
- Always return exactly 3 week objects with week numbers 1, 2, and 3.
- Each week must contain exactly 7 daily_plan entries with day values 1 through 7.
- Prioritize weak topics in week 1 and week 2; week 3 should focus on revision and mocks.
- Tailor tasks to the target company's typical interview style when possible.
- Keep tasks actionable, concise, and interview-focused.
- Do not include markdown, explanations, or extra keys.
"""


class DailyPlan(TypedDict):
    """Single day within a weekly study plan."""

    day: int
    topics: list[str]
    tasks: list[str]
    hours: float


class WeekPlan(TypedDict):
    """Study plan for one week."""

    week: int
    title: str
    focus_topics: list[str]
    goals: list[str]
    daily_plan: list[DailyPlan]


class StudyRoadmap(TypedDict):
    """Structured preparation roadmap (3-week full plan or adaptive short/emergency plan)."""

    target_company: str
    weak_topics: list[str]
    duration_weeks: int
    weeks: list[WeekPlan]
    # New fields — present whenever interview_date is supplied
    interview_date: str        # "YYYY-MM-DD" or "" when not provided
    days_remaining: int        # -1 when not provided
    hours_per_day: float       # default 2.0
    roadmap_type: str          # "Full Preparation Plan" | "Short-Term Plan" | "Emergency Plan"


class RoadmapGeneratorError(GroqClientError):
    """Raised when roadmap generation or response parsing fails."""


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
        logger.error("Failed to parse roadmap JSON: %s", raw[:500])
        raise RoadmapGeneratorError("Groq returned invalid JSON for roadmap generation.") from exc


def _normalize_string_list(value: Any, field_name: str) -> list[str]:
    """Normalize a field into a deduplicated list of non-empty strings."""
    if not isinstance(value, list):
        raise RoadmapGeneratorError(
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


def _normalize_topics(weak_topics: Any) -> list[str]:
    """Validate and normalize weak topic input."""
    topics = _normalize_string_list(weak_topics, "weak_topics")
    if not topics:
        raise ValueError("weak_topics must contain at least one topic.")
    return topics


def _normalize_company(target_company: str) -> str:
    """Validate and normalize the target company name."""
    company = target_company.strip()
    if not company:
        raise ValueError("target_company must be a non-empty string.")
    return company


def _parse_interview_date(interview_date: Optional[str]) -> Optional[date]:
    """
    Parse and validate an interview date string.

    Args:
        interview_date: Date string in ``YYYY-MM-DD`` format, or ``None``.

    Returns:
        A :class:`datetime.date` object, or ``None`` when not supplied.

    Raises:
        ValueError: If the string is present but not in ``YYYY-MM-DD`` format,
                    or if the date is in the past.
    """
    if interview_date is None:
        return None

    interview_date = interview_date.strip()
    try:
        parsed = date.fromisoformat(interview_date)
    except ValueError:
        raise ValueError(
            f"interview_date '{interview_date}' is not a valid YYYY-MM-DD date."
        )

    if parsed < date.today():
        raise ValueError(
            f"interview_date '{interview_date}' is in the past. "
            "Please provide a future date."
        )

    return parsed


def _validate_hours_per_day(hours_per_day: Any) -> float:
    """
    Validate and return hours_per_day as a positive float.

    Raises:
        ValueError: If the value is not a positive number.
    """
    try:
        hours = float(hours_per_day)
    except (TypeError, ValueError):
        raise ValueError(
            f"hours_per_day must be a positive number, got '{hours_per_day}'."
        )

    if hours <= 0:
        raise ValueError(
            f"hours_per_day must be greater than 0, got {hours}."
        )

    return hours


def _resolve_roadmap_type(days_remaining: Optional[int]) -> str:
    """
    Determine the roadmap type from the number of days until the interview.

    Args:
        days_remaining: Days until the interview, or ``None`` when no date supplied.

    Returns:
        One of ``"Emergency Plan"``, ``"Short-Term Plan"``, or ``"Full Preparation Plan"``.
    """
    if days_remaining is None:
        return "Full Preparation Plan"
    if days_remaining <= 3:
        return "Emergency Plan"
    if days_remaining <= 14:
        return "Short-Term Plan"
    return "Full Preparation Plan"


def _workload_description(hours_per_day: float) -> str:
    """Return a short workload descriptor for use in Groq prompts."""
    if hours_per_day <= 2:
        return "light workload (2-3 tasks per day)"
    if hours_per_day <= 5:
        return "moderate workload (4-5 tasks per day)"
    return "intensive workload (6+ tasks per day)"


def _normalize_daily_plan(value: Any, week_number: int) -> list[DailyPlan]:
    """Validate daily plan entries for a week."""
    if not isinstance(value, list):
        raise RoadmapGeneratorError(
            f"Week {week_number} `daily_plan` must be a list, got {type(value).__name__}."
        )

    daily_plan: list[DailyPlan] = []
    seen_days: set[int] = set()

    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RoadmapGeneratorError(
                f"Week {week_number} daily_plan[{index}] must be a dictionary."
            )

        day = item.get("day")
        if not isinstance(day, int) or day < 1 or day > DAYS_PER_WEEK:
            raise RoadmapGeneratorError(
                f"Week {week_number} daily_plan[{index}] must have `day` between 1 and 7."
            )
        if day in seen_days:
            raise RoadmapGeneratorError(f"Week {week_number} has duplicate day {day}.")
        seen_days.add(day)

        hours = item.get("hours", 2)
        if not isinstance(hours, (int, float)) or hours <= 0:
            raise RoadmapGeneratorError(
                f"Week {week_number} day {day} must have a positive numeric `hours` value."
            )

        daily_plan.append(
            DailyPlan(
                day=day,
                topics=_normalize_string_list(item.get("topics"), f"week {week_number} day {day} topics"),
                tasks=_normalize_string_list(item.get("tasks"), f"week {week_number} day {day} tasks"),
                hours=round(float(hours), 1),
            )
        )

    if len(daily_plan) != DAYS_PER_WEEK:
        raise RoadmapGeneratorError(
            f"Week {week_number} must contain exactly {DAYS_PER_WEEK} daily_plan entries."
        )

    daily_plan.sort(key=lambda entry: entry["day"])
    return daily_plan


def _validate_roadmap(
    data: dict[str, Any],
    expected_company: str,
    expected_topics: list[str],
    *,
    interview_date: str = "",
    days_remaining: int = -1,
    hours_per_day: float = 2.0,
    roadmap_type: str = "Full Preparation Plan",
) -> StudyRoadmap:
    """Ensure the parsed response matches the expected 3-week roadmap schema."""
    if not isinstance(data, dict):
        raise RoadmapGeneratorError("Roadmap response must be a JSON object.")

    target_company = str(data.get("target_company", "")).strip()
    if not target_company:
        raise RoadmapGeneratorError("Roadmap response is missing `target_company`.")

    weak_topics = _normalize_string_list(data.get("weak_topics"), "weak_topics")
    duration_weeks = data.get("duration_weeks")
    if duration_weeks != ROADMAP_WEEKS:
        raise RoadmapGeneratorError(f"`duration_weeks` must be {ROADMAP_WEEKS}.")

    weeks_value = data.get("weeks")
    if not isinstance(weeks_value, list) or len(weeks_value) != ROADMAP_WEEKS:
        raise RoadmapGeneratorError(f"Roadmap must contain exactly {ROADMAP_WEEKS} weeks.")

    weeks: list[WeekPlan] = []
    seen_weeks: set[int] = set()

    for index, week in enumerate(weeks_value):
        if not isinstance(week, dict):
            raise RoadmapGeneratorError(f"weeks[{index}] must be a dictionary.")

        week_number = week.get("week")
        if not isinstance(week_number, int) or week_number < 1 or week_number > ROADMAP_WEEKS:
            raise RoadmapGeneratorError(f"weeks[{index}] must have `week` between 1 and 3.")
        if week_number in seen_weeks:
            raise RoadmapGeneratorError(f"Duplicate week number found: {week_number}.")
        seen_weeks.add(week_number)

        title = str(week.get("title", "")).strip()
        if not title:
            raise RoadmapGeneratorError(f"Week {week_number} is missing `title`.")

        weeks.append(
            WeekPlan(
                week=week_number,
                title=title,
                focus_topics=_normalize_string_list(week.get("focus_topics"), f"week {week_number} focus_topics"),
                goals=_normalize_string_list(week.get("goals"), f"week {week_number} goals"),
                daily_plan=_normalize_daily_plan(week.get("daily_plan"), week_number),
            )
        )

    weeks.sort(key=lambda entry: entry["week"])

    return StudyRoadmap(
        target_company=target_company or expected_company,
        weak_topics=weak_topics or expected_topics,
        duration_weeks=ROADMAP_WEEKS,
        weeks=weeks,
        interview_date=interview_date,
        days_remaining=days_remaining,
        hours_per_day=hours_per_day,
        roadmap_type=roadmap_type,
    )


def _build_fallback_roadmap(
    weak_topics: list[str],
    target_company: str,
    *,
    interview_date: str = "",
    days_remaining: int = -1,
    hours_per_day: float = 2.0,
    roadmap_type: str = "Full Preparation Plan",
) -> StudyRoadmap:
    """Build a deterministic roadmap when Groq is unavailable.

    Adapts titles, goals, and daily task counts to the roadmap_type and
    hours_per_day so the fallback remains consistent with the enhanced schema.
    """
    # Task count driven by hours_per_day
    if hours_per_day <= 2:
        tasks_per_day = 2
    elif hours_per_day <= 5:
        tasks_per_day = 4
    else:
        tasks_per_day = 6

    # Titles and goals vary by plan type
    if roadmap_type == "Emergency Plan":
        week_titles = [
            "Emergency Weak-Topic Blitz",
            "Key JD Skills Rapid Review",
            "Mock Interviews and Final Revision",
        ]
        week_goals = [
            [
                f"Cover the most critical parts of {', '.join(weak_topics[:2])}.",
                "Focus exclusively on high-probability interview questions.",
            ],
            [
                "Drill the most important JD skills at speed.",
                "Eliminate the biggest knowledge gaps before the interview.",
            ],
            [
                f"Run at least 2 timed {target_company}-style mock sessions.",
                "Revise notes and consolidate key formulas/patterns.",
            ],
        ]
    elif roadmap_type == "Short-Term Plan":
        week_titles = [
            "Weak Topic Focus and JD Alignment",
            "Practice and Problem Solving",
            "Mock Interviews and Revision",
        ]
        week_goals = [
            [
                f"Rebuild fundamentals for {', '.join(weak_topics[:2])}.",
                f"Align study with {target_company} JD technologies.",
            ],
            [
                "Solve medium-level problems on weak topics.",
                "Track mistakes and maintain an error log.",
            ],
            [
                "Run timed mock assessments.",
                f"Simulate {target_company}-style interview questions.",
            ],
        ]
    else:  # Full Preparation Plan
        week_titles = [
            "Foundation and Concept Review",
            "Practice and Problem Solving",
            "Revision and Mock Interviews",
        ]
        week_goals = [
            [
                f"Rebuild fundamentals for {', '.join(weak_topics[:2])}.",
                f"Review core theory commonly asked at {target_company}.",
            ],
            [
                "Solve medium-level problems on weak topics.",
                "Track mistakes and maintain an error log.",
            ],
            [
                "Run timed mock assessments.",
                f"Simulate {target_company}-style interview questions.",
            ],
        ]

    weeks: list[WeekPlan] = []

    for week_index in range(ROADMAP_WEEKS):
        daily_plan: list[DailyPlan] = []
        for day in range(1, DAYS_PER_WEEK + 1):
            topic_index = (day - 1) % len(weak_topics)
            topic = weak_topics[topic_index]

            base_tasks = [
                f"Study {topic} concepts for {target_company} interviews.",
                f"Solve 2-3 practice problems on {topic}.",
            ]
            extra_tasks = [
                f"Review common {topic} patterns and edge cases.",
                f"Watch a short tutorial or read documentation on {topic}.",
                "Update your error log with today's mistakes.",
                f"Attempt one timed {target_company}-style question on {topic}.",
            ]
            tasks = (base_tasks + extra_tasks)[: max(tasks_per_day, 2)]

            daily_plan.append(
                DailyPlan(
                    day=day,
                    topics=[topic],
                    tasks=tasks,
                    hours=hours_per_day,
                )
            )

        weeks.append(
            WeekPlan(
                week=week_index + 1,
                title=week_titles[week_index],
                focus_topics=weak_topics,
                goals=week_goals[week_index],
                daily_plan=daily_plan,
            )
        )

    return StudyRoadmap(
        target_company=target_company,
        weak_topics=weak_topics,
        duration_weeks=ROADMAP_WEEKS,
        weeks=weeks,
        interview_date=interview_date,
        days_remaining=days_remaining,
        hours_per_day=hours_per_day,
        roadmap_type=roadmap_type,
    )


def generate_roadmap(
    weak_topics: list[str],
    target_company: str,
    *,
    interview_date: Optional[str] = None,
    hours_per_day: Optional[float] = None,
    groq_client: Optional[GroqClient] = None,
) -> StudyRoadmap:
    """
    Generate a placement preparation roadmap for weak topics and a target company.

    The plan type and daily workload adapt automatically:

    * **Emergency Plan** — ≤ 3 days to interview (weak topics + revision only).
    * **Short-Term Plan** — 4-14 days (weak topics + JD technologies + mocks).
    * **Full Preparation Plan** — > 14 days, or no interview date supplied (3-week deep plan).

    Daily task count scales with ``hours_per_day``:

    * ≤ 2 h → 2-3 tasks  |  3-5 h → 4-5 tasks  |  ≥ 6 h → 6+ tasks

    Args:
        weak_topics:    Topics requiring additional preparation.
        target_company: Company the student is preparing for.
        interview_date: Target interview date in ``YYYY-MM-DD`` format (optional).
                        Defaults to ``None`` → Full Preparation Plan.
        hours_per_day:  Daily available study hours (optional).
                        Defaults to ``2.0``.
        groq_client:    Optional shared Groq client.

    Returns:
        :class:`StudyRoadmap` with weekly goals, daily tasks, and the new
        ``interview_date``, ``days_remaining``, ``hours_per_day``, and
        ``roadmap_type`` fields populated.

    Raises:
        ValueError: If inputs are empty, ``interview_date`` is malformed/past,
                    or ``hours_per_day`` is not positive.
        RoadmapGeneratorError: If Groq returns an invalid roadmap payload.
        GroqClientError: If the Groq API request fails before fallback is applied.
    """
    # --- Validate and normalise inputs ---
    normalized_topics = _normalize_topics(weak_topics)
    normalized_company = _normalize_company(target_company)
    client = groq_client or GroqClient()

    parsed_date = _parse_interview_date(interview_date)
    validated_hours = _validate_hours_per_day(hours_per_day if hours_per_day is not None else 2.0)

    days_remaining: int = (parsed_date - date.today()).days if parsed_date else -1
    roadmap_type: str = _resolve_roadmap_type(days_remaining if parsed_date else None)
    interview_date_str: str = parsed_date.isoformat() if parsed_date else ""
    workload: str = _workload_description(validated_hours)

    # --- Build Groq prompt with new context ---
    date_context = (
        f"Interview date: {interview_date_str} ({days_remaining} days remaining)\n"
        if parsed_date
        else "Interview date: not specified\n"
    )

    if roadmap_type == "Emergency Plan":
        focus_instruction = (
            "EMERGENCY MODE: Only {days_remaining} days remain. "
            "Focus exclusively on weak topics, the most critical JD skills, "
            "interview revision, and at least one mock interview session per day."
        ).format(days_remaining=days_remaining)
    elif roadmap_type == "Short-Term Plan":
        focus_instruction = (
            "SHORT-TERM MODE: {days_remaining} days remain. "
            "Cover weak topics and key JD technologies as a priority, "
            "include daily practice questions, and schedule mock interviews in week 3."
        ).format(days_remaining=days_remaining)
    else:
        focus_instruction = (
            "Spread weak-topic coverage across weeks 1 and 2, then prioritize "
            f"revision, timed practice, and {normalized_company}-specific mock interviews in week 3."
        )

    prompt = (
        f"Create a 3-week placement preparation roadmap.\n\n"
        f"Target company: {normalized_company}\n"
        f"Weak topics: {json.dumps(normalized_topics)}\n"
        f"{date_context}"
        f"Roadmap type: {roadmap_type}\n"
        f"Study hours per day: {validated_hours} ({workload})\n\n"
        f"{focus_instruction}\n\n"
        f"Each day's task list must reflect a {workload}."
    )

    logger.info(
        "Generating %s for %s — %d weak topics, %s days remaining, %.1f h/day.",
        roadmap_type,
        normalized_company,
        len(normalized_topics),
        days_remaining if parsed_date else "N/A",
        validated_hours,
    )

    # Shared kwargs for both _validate_roadmap and _build_fallback_roadmap
    plan_kwargs = dict(
        interview_date=interview_date_str,
        days_remaining=days_remaining,
        hours_per_day=validated_hours,
        roadmap_type=roadmap_type,
    )

    try:
        raw_response = generate_response(
            prompt,
            system_prompt=SYSTEM_PROMPT,
            model=client.model,
            temperature=0.4,
            max_tokens=4096,
            api_key=client.api_key,
        )
        parsed = _parse_json_response(raw_response)
        roadmap = _validate_roadmap(parsed, normalized_company, normalized_topics, **plan_kwargs)
    except (GroqClientError, RoadmapGeneratorError) as exc:
        logger.warning("Groq roadmap generation failed (%s); using fallback roadmap.", exc)
        roadmap = _build_fallback_roadmap(normalized_topics, normalized_company, **plan_kwargs)

    logger.info(
        "Roadmap ready — type: %s, company: %s, weeks: %d, daily entries: %d.",
        roadmap["roadmap_type"],
        roadmap["target_company"],
        len(roadmap["weeks"]),
        sum(len(week["daily_plan"]) for week in roadmap["weeks"]),
    )

    return roadmap


class RoadmapGenerator:
    """
    Generates adaptive preparation roadmaps for placement candidates.
    """

    def __init__(self, groq_client: Optional[GroqClient] = None) -> None:
        """
        Initialize the roadmap generator.

        Args:
            groq_client: Shared Groq client instance. Creates one if not provided.
        """
        self.groq_client = groq_client or GroqClient()

    def generate(
        self,
        weak_topics: list[str],
        target_company: str,
        *,
        interview_date: Optional[str] = None,
        hours_per_day: Optional[float] = None,
    ) -> StudyRoadmap:
        """
        Create a preparation roadmap for weak topics and a target company.

        Args:
            weak_topics:    Topics needing extra focus from performance analysis.
            target_company: Company the student is targeting.
            interview_date: Target interview date in ``YYYY-MM-DD`` format (optional).
            hours_per_day:  Daily available study hours (optional, default 2.0).

        Returns:
            Structured roadmap with weekly goals, daily tasks, and plan metadata.
        """
        return generate_roadmap(
            weak_topics,
            target_company,
            interview_date=interview_date,
            hours_per_day=hours_per_day,
            groq_client=self.groq_client,
        )

    def prioritize_topics(
        self,
        topics: list[str],
        weak_areas: list[str],
        jd_analysis: Optional[dict[str, Any]] = None,
    ) -> list[str]:
        """
        Rank topics by preparation priority.

        Args:
            topics: Full list of topics to prepare.
            weak_areas: Topics where the user underperformed.
            jd_analysis: Optional JD analysis for role-specific weighting.

        Returns:
            Topics ordered from highest to lowest priority.
        """
        normalized_topics = _normalize_string_list(topics, "topics")
        normalized_weak = _normalize_string_list(weak_areas, "weak_areas")

        jd_priority: list[str] = []
        if isinstance(jd_analysis, dict):
            for key in ("dsa_topics", "cs_topics", "technologies", "skills"):
                jd_priority.extend(_normalize_string_list(jd_analysis.get(key, []), key))

        prioritized: list[str] = []
        seen: set[str] = set()

        for topic in normalized_weak + jd_priority + normalized_topics:
            key = topic.casefold()
            if key in seen:
                continue
            seen.add(key)
            prioritized.append(topic)

        return prioritized

    def update_roadmap(
        self,
        current_roadmap: StudyRoadmap,
        latest_performance: dict[str, Any],
    ) -> StudyRoadmap:
        """
        Adjust an existing roadmap based on new performance data.

        Args:
            current_roadmap: Active roadmap to revise.
            latest_performance: Most recent performance report.

        Returns:
            Updated 3-week roadmap reflecting revised weak-topic priorities.
        """
        if not isinstance(latest_performance, dict):
            raise ValueError("latest_performance must be a dictionary.")

        updated_weak_topics = _normalize_string_list(
            latest_performance.get("weak_topics"),
            "weak_topics",
        )
        if not updated_weak_topics:
            updated_weak_topics = current_roadmap["weak_topics"]

        merged_topics = self.prioritize_topics(
            topics=current_roadmap["weak_topics"] + updated_weak_topics,
            weak_areas=updated_weak_topics,
        )

        return generate_roadmap(
            merged_topics,
            current_roadmap["target_company"],
            groq_client=self.groq_client,
        )
