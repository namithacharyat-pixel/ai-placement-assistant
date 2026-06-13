"""Roadmap generation routes."""

import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Blueprint, jsonify, request

from ai_module.groq_client import GroqClientError, GroqConfigurationError
from ai_module.roadmap_generator import RoadmapGeneratorError, generate_roadmap

logger = logging.getLogger(__name__)

roadmap_bp = Blueprint("roadmap", __name__)


def _normalize_topic_list(value: object, field_name: str) -> list[str]:
    """Validate and normalize a list of topic strings."""
    if value is None:
        return []

    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list.")

    topics: list[str] = []
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
        topics.append(cleaned)

    return topics


def _combine_topics(weak_topics: list[str], missing_skills: list[str]) -> list[str]:
    """Merge missing skills and weak topics, preserving priority order."""
    combined: list[str] = []
    seen: set[str] = set()

    for topic in missing_skills + weak_topics:
        key = topic.casefold()
        if key in seen:
            continue
        seen.add(key)
        combined.append(topic)

    return combined


@roadmap_bp.post("/generate")
def generate():
    """Generate a personalized study roadmap."""
    try:
        payload = request.get_json(silent=True)
        if payload is None or not isinstance(payload, dict):
            return jsonify({"error": "Request body must be valid JSON."}), 400

        target_company = payload.get("target_company")
        if target_company is None:
            return jsonify({"error": "Missing required field: target_company."}), 400
        if not isinstance(target_company, str) or not target_company.strip():
            return jsonify({"error": "target_company must be a non-empty string."}), 400

        weak_topics = _normalize_topic_list(payload.get("weak_topics"), "weak_topics")
        missing_skills = _normalize_topic_list(
            payload.get("missing_skills"),
            "missing_skills",
        )
        topics = _combine_topics(weak_topics, missing_skills)

        if not topics:
            return jsonify(
                {"error": "At least one topic is required in weak_topics or missing_skills."}
            ), 400

        interview_date = payload.get("interview_date")
        if interview_date is not None and (
            not isinstance(interview_date, str) or not interview_date.strip()
        ):
            return jsonify({"error": "interview_date must be a non-empty string."}), 400

        hours_per_day = payload.get("hours_per_day", 2)
        if not isinstance(hours_per_day, (int, float)) or isinstance(hours_per_day, bool):
            return jsonify({"error": "hours_per_day must be a positive number."}), 400

        roadmap = generate_roadmap(
            weak_topics=topics,
            target_company=target_company.strip(),
            interview_date=interview_date.strip() if isinstance(interview_date, str) else None,
            hours_per_day=float(hours_per_day),
        )

        return jsonify(roadmap), 200

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except GroqConfigurationError as exc:
        return jsonify({"error": str(exc)}), 500
    except (RoadmapGeneratorError, GroqClientError) as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        logger.exception("Unexpected error during roadmap generation.")
        return jsonify({"error": "An unexpected error occurred during roadmap generation."}), 500
