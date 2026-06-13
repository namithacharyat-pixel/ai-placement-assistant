"""Assessment generation routes."""

import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Blueprint, jsonify, request

from ai_module.assessment_generator import (
    AssessmentGenerator,
    AssessmentGeneratorError,
)
from ai_module.groq_client import GroqClientError, GroqConfigurationError

logger = logging.getLogger(__name__)

assessment_bp = Blueprint("assessment", __name__)
_generator = AssessmentGenerator()


@assessment_bp.post("/mcq")
def generate_mcq():
    """Generate multiple-choice questions for a given topic."""
    try:
        payload = request.get_json(silent=True)
        if payload is None or not isinstance(payload, dict):
            return jsonify({"error": "Request body must be valid JSON."}), 400

        topic = payload.get("topic")
        if topic is None:
            return jsonify({"error": "Missing required field: topic."}), 400
        if not isinstance(topic, str) or not topic.strip():
            return jsonify({"error": "topic must be a non-empty string."}), 400

        difficulty = payload.get("difficulty", "medium")
        if not isinstance(difficulty, str) or not difficulty.strip():
            return jsonify({"error": "difficulty must be a non-empty string."}), 400

        count = payload.get("count")
        if count is None:
            return jsonify({"error": "Missing required field: count."}), 400
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            return jsonify({"error": "count must be a positive integer."}), 400

        mcqs = _generator.generate_mcq(
            topic=topic.strip(),
            count=count,
            difficulty=difficulty.strip(),
        )

        return jsonify({"mcqs": mcqs}), 200

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except GroqConfigurationError as exc:
        return jsonify({"error": str(exc)}), 500
    except (AssessmentGeneratorError, GroqClientError) as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        logger.exception("Unexpected error during MCQ generation.")
        return jsonify({"error": "An unexpected error occurred during MCQ generation."}), 500


@assessment_bp.post("/coding")
def generate_coding():
    """Generate a coding interview question for a given topic."""
    try:
        payload = request.get_json(silent=True)
        if payload is None or not isinstance(payload, dict):
            return jsonify({"error": "Request body must be valid JSON."}), 400

        topic = payload.get("topic")
        if topic is None:
            return jsonify({"error": "Missing required field: topic."}), 400
        if not isinstance(topic, str) or not topic.strip():
            return jsonify({"error": "topic must be a non-empty string."}), 400

        difficulty = payload.get("difficulty", "medium")
        if not isinstance(difficulty, str) or not difficulty.strip():
            return jsonify({"error": "difficulty must be a non-empty string."}), 400

        category = payload.get("category", "DSA")
        company_name = payload.get("company_name")
        language = payload.get("language", "java")

        question = _generator.generate_coding_question(
            topic=topic,
            difficulty=difficulty,
            category=category,
            company_name=company_name,
            language=language
            )

        return jsonify(question), 200
    


    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except GroqConfigurationError as exc:
        return jsonify({"error": str(exc)}), 500
    except (AssessmentGeneratorError, GroqClientError) as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        logger.exception("Unexpected error during coding question generation.")
        return jsonify({"error": "An unexpected error occurred during coding question generation."}), 500
    

@assessment_bp.post("/review")
def review_solution():
    """AI review of a coding solution."""
    try:
        payload = request.get_json(silent=True)

        if payload is None or not isinstance(payload, dict):
            return jsonify({"error": "Request body must be valid JSON."}), 400

        question = payload.get("question")
        solution = payload.get("solution")
        language = payload.get("language")

        if not question:
            return jsonify({"error": "Missing question"}), 400

        if not solution:
            return jsonify({"error": "Missing solution"}), 400

        if not language:
            return jsonify({"error": "Missing language"}), 400

        result = _generator.review_solution(
            question=question,
            user_solution=solution,
            language=language,
        )

        return jsonify(result), 200

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    except GroqConfigurationError as exc:
        return jsonify({"error": str(exc)}), 500

    except (AssessmentGeneratorError, GroqClientError) as exc:
        return jsonify({"error": str(exc)}), 502

    except Exception:
        logger.exception("Unexpected error during solution review.")
        return jsonify(
            {"error": "An unexpected error occurred during review."}
        ), 500
    

@assessment_bp.get("/recommendation/<company>")
def recommendation(company: str):
    """Get next recommended topic for a company."""
    try:
        result = _generator.generate_next_recommendation(company)

        return jsonify(result), 200

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    except GroqConfigurationError as exc:
        return jsonify({"error": str(exc)}), 500

    except (AssessmentGeneratorError, GroqClientError) as exc:
        return jsonify({"error": str(exc)}), 502

    except Exception:
        logger.exception("Unexpected error during recommendation generation.")
        return jsonify(
            {"error": "An unexpected error occurred."}
        ), 500
