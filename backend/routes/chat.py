"""Chat assistant routes."""

import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Blueprint, jsonify, request

from ai_module.chat_assistant import ChatAssistant, ChatAssistantError
from ai_module.groq_client import GroqClientError, GroqConfigurationError

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__)


@chat_bp.post("/", strict_slashes=False)
def chat():
    """Answer a placement preparation question."""
    try:
        payload = request.get_json(silent=True)
        if payload is None or not isinstance(payload, dict):
            return jsonify({"error": "Request body must be valid JSON."}), 400

        message = payload.get("message")
        if message is None:
            return jsonify({"error": "Missing required field: message."}), 400

        assistant = ChatAssistant()
        answer = assistant.chat(message)

        return jsonify({"answer": answer}), 200

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except GroqConfigurationError as exc:
        return jsonify({"error": str(exc)}), 500
    except (ChatAssistantError, GroqClientError) as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        logger.exception("Unexpected error during chat.")
        return jsonify({"error": "An unexpected error occurred during chat."}), 500
