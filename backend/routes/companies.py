"""Company and roadmap progress persistence routes."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from flask import Blueprint, jsonify, request

from config import Config
from utils.json_storage import DATA_DIR, load_json, save_json

PROGRESS_FILE = DATA_DIR / "roadmap_progress.json"

INTERVIEW_ROUND_TYPES = [
    "OA",
    "Coding Round",
    "Technical Interview",
    "Group Discussion",
    "HR Interview",
]

TERMINAL_STATUSES = ["Selected", "Rejected", "Waiting For Result"]

companies_bp = Blueprint("companies", __name__)


def _empty_progress() -> dict[str, Any]:
    return {"version": 1, "active_company_id": None, "companies": {}}


def _load_progress() -> dict[str, Any]:
    data = load_json(PROGRESS_FILE)
    if not data or "companies" not in data:
        data = _empty_progress()
    data.setdefault("version", 1)
    data.setdefault("active_company_id", None)
    if not isinstance(data.get("companies"), dict):
        data["companies"] = {}
    return data


def _save_progress(data: dict[str, Any]) -> bool:
    return save_json(PROGRESS_FILE, data)


def _make_company_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "company"
    return f"{slug}-{uuid.uuid4().hex[:8]}"


def _default_interview_rounds() -> list[dict[str, str]]:
    return [{"name": name, "status": "pending"} for name in INTERVIEW_ROUND_TYPES]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _create_company_record(name: str) -> dict[str, Any]:
    now = _now()
    return {
        "id": _make_company_id(name),
        "company_name": name,
        "name": name,
        "created_at": now,
        "updated_at": now,
        "interview_date": None,
        "hours_per_day": 2.0,
        "current_round": INTERVIEW_ROUND_TYPES[0],
        "interview_status": None,
        "interview_rounds": _default_interview_rounds(),
        "jd_text": "",
        "jd_analysis": None,
        "resume_match": None,
        "missing_skills": [],
        "weak_topics": [],
        "roadmap_data": None,
        "roadmap_topics": [],
        "completed_days": {},
        "daily_plan_progress": {},
        "performance_history": [],
        "assessments": [],
    }


def _get_company_or_404(progress: dict[str, Any], company_id: str):
    company = progress["companies"].get(company_id)
    if not company:
        return None, (jsonify({"error": "Company not found."}), 404)
    return company, None


@companies_bp.get("/")
def list_companies():
    progress = _load_progress()
    companies = list(progress["companies"].values())
    return jsonify(
        {
            "active_company_id": progress.get("active_company_id"),
            "companies": companies,
        }
    )


@companies_bp.post("/")
def create_company():
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Request body must be valid JSON."}), 400

    name = payload.get("company_name") or payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "company_name must be a non-empty string."}), 400

    progress = _load_progress()
    record = _create_company_record(name.strip())

    interview_date = payload.get("interview_date")
    if isinstance(interview_date, str) and interview_date.strip():
        record["interview_date"] = interview_date.strip()

    hours = payload.get("hours_per_day", 2)
    try:
        record["hours_per_day"] = float(hours)
    except (TypeError, ValueError):
        record["hours_per_day"] = 2.0

    progress["companies"][record["id"]] = record
    progress["active_company_id"] = record["id"]
    _save_progress(progress)

    return jsonify(record), 201


@companies_bp.get("/<company_id>")
def get_company(company_id: str):
    progress = _load_progress()
    company, err = _get_company_or_404(progress, company_id)
    if err:
        return err
    return jsonify(company)


@companies_bp.put("/<company_id>")
def update_company(company_id: str):
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Request body must be valid JSON."}), 400

    progress = _load_progress()
    company, err = _get_company_or_404(progress, company_id)
    if err:
        return err

    allowed = {
        "company_name",
        "name",
        "interview_date",
        "hours_per_day",
        "current_round",
        "interview_status",
        "interview_rounds",
        "jd_text",
        "jd_analysis",
        "resume_match",
        "missing_skills",
        "weak_topics",
        "roadmap_data",
        "roadmap_topics",
        "completed_days",
        "daily_plan_progress",
        "performance_history",
        "assessments",
    }

    for key, value in payload.items():
        if key in allowed:
            company[key] = value
            if key in {"company_name", "name"}:
                company["company_name"] = value
                company["name"] = value

    company["updated_at"] = _now()
    progress["companies"][company_id] = company
    _save_progress(progress)
    return jsonify(company)


@companies_bp.delete("/<company_id>")
def delete_company(company_id: str):
    progress = _load_progress()
    if company_id not in progress["companies"]:
        return jsonify({"error": "Company not found."}), 404

    del progress["companies"][company_id]
    if progress.get("active_company_id") == company_id:
        remaining = list(progress["companies"].keys())
        progress["active_company_id"] = remaining[0] if remaining else None

    _save_progress(progress)
    return jsonify({"message": "Company deleted."})


@companies_bp.post("/<company_id>/activate")
def activate_company(company_id: str):
    progress = _load_progress()
    _, err = _get_company_or_404(progress, company_id)
    if err:
        return err

    progress["active_company_id"] = company_id
    _save_progress(progress)
    return jsonify({"active_company_id": company_id})


@companies_bp.post("/<company_id>/round/next")
def advance_round(company_id: str):
    progress = _load_progress()
    company, err = _get_company_or_404(progress, company_id)
    if err:
        return err

    current = company.get("current_round", INTERVIEW_ROUND_TYPES[0])
    rounds = company.get("interview_rounds", _default_interview_rounds())

    for rnd in rounds:
        if rnd.get("name") == current:
            rnd["status"] = "completed"
            break

    try:
        idx = INTERVIEW_ROUND_TYPES.index(current)
        next_round = INTERVIEW_ROUND_TYPES[idx + 1] if idx + 1 < len(INTERVIEW_ROUND_TYPES) else current
    except ValueError:
        next_round = current

    company["current_round"] = next_round
    company["updated_at"] = _now()
    progress["companies"][company_id] = company
    _save_progress(progress)
    return jsonify(company)


@companies_bp.post("/<company_id>/round/status")
def set_round_status(company_id: str):
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return jsonify({"error": "Request body must be valid JSON."}), 400

    status = payload.get("status")
    if status not in TERMINAL_STATUSES + INTERVIEW_ROUND_TYPES:
        return jsonify({"error": "Invalid status."}), 400

    progress = _load_progress()
    company, err = _get_company_or_404(progress, company_id)
    if err:
        return err

    if status in TERMINAL_STATUSES:
        company["interview_status"] = status
        company["current_round"] = status
    else:
        company["current_round"] = status
        company["interview_status"] = None

    company["updated_at"] = _now()
    progress["companies"][company_id] = company
    _save_progress(progress)
    return jsonify(company)
