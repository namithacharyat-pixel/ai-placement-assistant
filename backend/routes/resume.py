"""Resume matching routes."""

import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Blueprint, jsonify, request

from ai_module.groq_client import GroqClientError, GroqConfigurationError
from ai_module.jd_analyzer import JDAnalyzer, JDAnalyzerError
from ai_module.resume_matcher import ResumeMatcher, ResumeMatcherError

logger = logging.getLogger(__name__)

resume_bp = Blueprint("resume", __name__)
_jd_analyzer = JDAnalyzer()
_resume_matcher = ResumeMatcher()


@resume_bp.post("/analyze")
def analyze_resume():
    """Analyze a resume against a job description and return a match report."""
    try:
        payload = request.get_json(silent=True)
        if payload is None or not isinstance(payload, dict):
            return jsonify({"error": "Request body must be valid JSON."}), 400

        resume_text = payload.get("resumeText")
        if resume_text is None:
            return jsonify({"error": "Missing required field: resumeText."}), 400

        jd_text = payload.get("jdText")
        if jd_text is None:
            return jsonify({"error": "Missing required field: jdText."}), 400

        jd_analysis = _jd_analyzer.analyze(jd_text)
        jd_analysis["description"] = jd_text

        result = _resume_matcher.analyze_resume(
            resume_text=resume_text,
            jd_analysis=jd_analysis,
        )

        return jsonify(result), 200

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except GroqConfigurationError as exc:
        return jsonify({"error": str(exc)}), 500
    except (JDAnalyzerError, ResumeMatcherError, GroqClientError) as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        logger.exception("Unexpected error during resume analysis.")
        return jsonify({"error": "An unexpected error occurred during resume analysis."}), 500
