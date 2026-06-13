"""Job description routes."""

import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Blueprint, jsonify, request

from ai_module.groq_client import GroqClientError, GroqConfigurationError
from ai_module.jd_analyzer import JDAnalyzer, JDAnalyzerError

logger = logging.getLogger(__name__)

jd_bp = Blueprint("jd", __name__)
_analyzer = JDAnalyzer()


@jd_bp.post("/analyze")
def analyze_jd():
    """Analyze a job description and return structured preparation insights."""
    try:
        payload = request.get_json(silent=True)
        if payload is None or not isinstance(payload, dict):
            return jsonify({"error": "Request body must be valid JSON."}), 400

        jd_text = payload.get("jdText")
        if jd_text is None:
            return jsonify({"error": "Missing required field: jdText."}), 400

        result = _analyzer.analyze(jd_text)
        return jsonify(result), 200

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except GroqConfigurationError as exc:
        return jsonify({"error": str(exc)}), 500
    except (JDAnalyzerError, GroqClientError) as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        logger.exception("Unexpected error during JD analysis.")
        return jsonify({"error": "An unexpected error occurred during JD analysis."}), 500
