import json
from pathlib import Path

from flask import Blueprint, jsonify, request

company_bp = Blueprint("company", __name__)

DATA_FILE = Path("roadmap_progress.json")


def load_data():
    if not DATA_FILE.exists():
        return {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


@company_bp.get("/")
def get_companies():
    data = load_data()

    companies = []

    for company_name, details in data.items():
        companies.append({
            "name": company_name,
            "interview_date": details.get("interview_date"),
            "round": details.get("current_round", "OA"),
        })

    return jsonify(companies)


@company_bp.post("/")
def create_company():
    payload = request.get_json()

    company_name = payload.get("name")

    if not company_name:
        return jsonify({"error": "Company name required"}), 400

    data = load_data()

    data[company_name] = {
        "interview_date": None,
        "current_round": "OA",
        "completed_days": [],
        "roadmap_topics": []
    }

    save_data(data)

    return jsonify({"message": "Company created"})


@company_bp.delete("/<company_name>")
def delete_company(company_name):
    data = load_data()

    if company_name in data:
        del data[company_name]
        save_data(data)

    return jsonify({"message": "Deleted"})