"""Performance analysis routes."""

import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Blueprint, jsonify, request

from ai_module.groq_client import GroqClientError, GroqConfigurationError
from ai_module.performance_analyzer import (
    PerformanceAnalyzerError,
    analyze_performance,
)

logger = logging.getLogger(__name__)

performance_bp = Blueprint("performance", __name__)


@performance_bp.post("/analyze")
def analyze():
    """Analyze student answers against correct answers and return a performance report."""
    try:
        payload = request.get_json(silent=True)
        if payload is None or not isinstance(payload, dict):
            return jsonify({"error": "Request body must be valid JSON."}), 400

        student_answers = payload.get("student_answers")
        if student_answers is None:
            return jsonify({"error": "Missing required field: student_answers."}), 400

        correct_answers = payload.get("correct_answers")
        if correct_answers is None:
            return jsonify({"error": "Missing required field: correct_answers."}), 400

        if not isinstance(student_answers, (list, dict)):
            return jsonify({"error": "student_answers must be a list or dictionary."}), 400

        if not isinstance(correct_answers, (list, dict)):
            return jsonify({"error": "correct_answers must be a list or dictionary."}), 400

        report = analyze_performance(
            student_answers=student_answers,
            correct_answers=correct_answers,
        )

        return jsonify(report), 200

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except GroqConfigurationError as exc:
        return jsonify({"error": str(exc)}), 500
    except (PerformanceAnalyzerError, GroqClientError) as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        logger.exception("Unexpected error during performance analysis.")
        return jsonify({"error": "An unexpected error occurred during performance analysis."}), 500
