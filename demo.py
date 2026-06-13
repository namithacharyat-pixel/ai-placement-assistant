"""
demo.py — End-to-end demonstration of the AI-Powered Placement Preparation Assistant.

Workflow:
  STEP 0  Company Dashboard — select or add a company (roadmap_progress.json).
  STEP 1  Upload and parse a Job Description (PDF or TXT) — when adding a company.
  STEP 2  Run JD Analyzer → extract skills, technologies, DSA/CS topics.
  STEP 3  Branch:
            Option 1 → Resume Match Analysis
            Option 2 → Interview Preparation
            Option 3 → AI Chat Assistant
            Option 4 → Exit
          (Option 1 may chain into Option 2.)

Multi-company state and interview rounds (OA, Technical, HR, Managerial) are
persisted in roadmap_progress.json at the project root.

Usage:
    python demo.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import textwrap
import uuid
from datetime import date, datetime
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Module imports — each module is already implemented and tested.
# ---------------------------------------------------------------------------

try:
    from ai_module.file_parser import parse_file
except ImportError:
    print("[WARN] file_parser.py not found; falling back to plain text input.")
    parse_file = None  # handled gracefully below

from ai_module.jd_analyzer import JDAnalyzer, JDAnalyzerError
from ai_module.resume_matcher import ResumeMatcher, ResumeMatcherError
from ai_module.assessment_generator import AssessmentGenerator, AssessmentGeneratorError

from ai_module.roadmap_generator import generate_roadmap, RoadmapGeneratorError
from ai_module.chat_assistant import ChatAssistant, ChatAssistantError

from ai_module.performance_analyzer import (
    PerformanceAnalyzerError,
    analyze_performance,
)

# ===========================================================================
# Console formatting helpers
# ===========================================================================

DIVIDER = "=" * 60
THIN_DIVIDER = "-" * 60
OPTION_LETTERS = ["A", "B", "C", "D", "E", "F"]

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roadmap_progress.json")
DEFAULT_ROUND_TYPES = ["OA", "Technical", "HR", "Managerial"]


def _section(title: str) -> None:
    """Print a bold section header."""
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)


def _subsection(title: str) -> None:
    print(f"\n{THIN_DIVIDER}")
    print(f"  {title}")
    print(THIN_DIVIDER)


def _bullet_list(items: list[str], indent: int = 4) -> None:
    """Print a bulleted list."""
    pad = " " * indent
    for item in items:
        print(f"{pad}• {item}")


def _numbered_list(items: list[str], indent: int = 4) -> None:
    """Print a numbered list."""
    pad = " " * indent
    for idx, item in enumerate(items, 1):
        print(f"{pad}{idx}. {item}")


def _kv(label: str, value: Any, indent: int = 4) -> None:
    """Print a key-value pair."""
    print(f"{' ' * indent}{label}: {value}")


def _wrap(text: str, width: int = 76, indent: int = 4) -> None:
    """Print word-wrapped text."""
    pad = " " * indent
    for line in textwrap.wrap(str(text), width=width, subsequent_indent=pad):
        print(pad + line if not line.startswith(pad) else line)


# ===========================================================================
# Input helpers
# ===========================================================================

def _prompt(message: str, default: str = "") -> str:
    """Read non-empty input from the user, with an optional default."""
    while True:
        raw = input(message).strip()
        if raw:
            return raw
        if default:
            return default
        print("  [!] Input cannot be empty. Please try again.")


def _prompt_choice(message: str, choices: list[str]) -> str:
    """Force the user to pick from a list of valid choices."""
    valid = {c.lower() for c in choices}
    while True:
        raw = input(message).strip().lower()
        if raw in valid:
            return raw
        print(f"  [!] Please enter one of: {', '.join(choices)}")


def _prompt_int(message: str, min_val: int = 1, max_val: int = 100) -> int:
    """Read a valid integer within [min_val, max_val]."""
    while True:
        raw = input(message).strip()
        try:
            value = int(raw)
            if min_val <= value <= max_val:
                return value
            print(f"  [!] Please enter a number between {min_val} and {max_val}.")
        except ValueError:
            print("  [!] That doesn't look like a number. Try again.")


def _prompt_float(message: str, min_val: float = 0.5, max_val: float = 24.0) -> float:
    """Read a valid float within [min_val, max_val]."""
    while True:
        raw = input(message).strip()
        try:
            value = float(raw)
            if min_val <= value <= max_val:
                return value
            print(f"  [!] Please enter a value between {min_val} and {max_val}.")
        except ValueError:
            print("  [!] That doesn't look like a number. Try again.")


def _prompt_date(message: str) -> Optional[str]:
    """Read a future date in YYYY-MM-DD format, or return None on skip."""
    while True:
        raw = input(message).strip()
        if raw.lower() in {"", "skip", "s"}:
            return None
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d").date()
            if parsed <= date.today():
                print("  [!] Interview date must be in the future.")
                continue
            return raw
        except ValueError:
            print("  [!] Invalid format. Use YYYY-MM-DD or press Enter to skip.")


# ===========================================================================
# File loading
# ===========================================================================

def _load_text_from_file(label: str, supported: str = "PDF or TXT") -> Optional[str]:
    """
    Prompt the user for a file path and extract its text content.

    Uses file_parser.parse_file when available; falls back to plain UTF-8
    reading for .txt files when the module is absent.

    Returns the extracted text, or None if loading fails.
    """
    file_path = _prompt(f"\nEnter path to {label} ({supported}): ").strip('"').strip("'")

    if not os.path.isfile(file_path):
        print(f"  [ERROR] File not found: {file_path}")
        return None

    ext = os.path.splitext(file_path)[1].lower()

    # --- Use file_parser if available ---
    if parse_file is not None:
        try:
            text = parse_file(file_path)
            if not text or not text.strip():
                print("  [ERROR] file_parser returned empty content.")
                return None
            print(f"  [OK] Loaded {label} ({len(text)} characters).")
            return text
        except Exception as exc:  # noqa: BLE001
            print(f"  [ERROR] file_parser failed: {exc}")
            return None

    # --- Fallback: plain text only ---
    if ext == ".txt":
        try:
            with open(file_path, encoding="utf-8") as fh:
                text = fh.read()
            if not text.strip():
                print("  [ERROR] File is empty.")
                return None
            print(f"  [OK] Loaded {label} ({len(text)} characters).")
            return text
        except OSError as exc:
            print(f"  [ERROR] Could not read file: {exc}")
            return None

    print(
        "  [ERROR] file_parser.py is not available. "
        "Only .txt files can be read without it."
    )
    return None


# ===========================================================================
# Extract company name from JD text
# ===========================================================================

_COMPANY_SIGNALS = re.compile(
    r"(?:at|join|about|company[:\s]+|employer[:\s]+|hiring\s+at)\s+([A-Z][A-Za-z0-9&.\-\s]{1,40})",
    re.IGNORECASE,
)


def _infer_company_from_jd(jd_text: str, jd_analysis: dict[str, Any]) -> str:
    """
    Try to extract a company name from the raw JD text.

    Strategy (in priority order):
      1. Look for explicit signal phrases ("Join Acme Corp", "About Acme Corp").
      2. Look for a line that starts with a short all-caps or title-case word
         cluster before the first blank line (common in structured JDs).
      3. Fall back to "JD-Based Preparation".

    The user is NEVER asked for a company name — this replaces that prompt.
    """
    match = _COMPANY_SIGNALS.search(jd_text[:800])
    if match:
        candidate = match.group(1).strip().rstrip(".,;")
        if 2 <= len(candidate.split()) <= 5:
            return candidate

    for line in jd_text.splitlines()[:10]:
        stripped = line.strip()
        if not stripped:
            continue
        words = stripped.split()
        if 1 <= len(words) <= 4 and all(
            w[0].isupper() or w.isupper() for w in words if w.isalpha()
        ):
            return stripped

    return "JD-Based Preparation"


# ===========================================================================
# roadmap_progress.json — multi-company persistence
# ===========================================================================

def _empty_progress() -> dict[str, Any]:
    """Default on-disk schema for roadmap_progress.json."""
    return {
        "version": 1,
        "active_company_id": None,
        "companies": {},
    }


def _default_interview_rounds() -> list[dict[str, str]]:
    """Initial interview round pipeline for a new company."""
    return [{"name": name, "status": "pending"} for name in DEFAULT_ROUND_TYPES]


def _load_progress() -> dict[str, Any]:
    """Load persisted progress from roadmap_progress.json."""
    if not os.path.isfile(PROGRESS_FILE):
        return _empty_progress()

    try:
        with open(PROGRESS_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  [WARN] Could not read {PROGRESS_FILE}: {exc}")
        return _empty_progress()

    if not isinstance(data, dict):
        return _empty_progress()

    data.setdefault("version", 1)
    data.setdefault("active_company_id", None)
    data.setdefault("companies", {})
    if not isinstance(data["companies"], dict):
        data["companies"] = {}

    return data


def _save_progress(progress: dict[str, Any]) -> None:
    """Write progress data to roadmap_progress.json."""
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as fh:
            json.dump(progress, fh, indent=2, ensure_ascii=False)
    except OSError as exc:
        print(f"  [WARN] Could not save progress to {PROGRESS_FILE}: {exc}")


class CompanySession:
    """Active company context backed by roadmap_progress.json."""

    def __init__(self, progress: dict[str, Any], company_id: str) -> None:
        self.progress = progress
        self.company_id = company_id
        self.progress["active_company_id"] = company_id

    @property
    def company(self) -> dict[str, Any]:
        return self.progress["companies"][self.company_id]

    def update(self, **fields: Any) -> None:
        """Merge fields into the active company record and persist."""
        self.company.update(fields)
        self.company["updated_at"] = datetime.now().isoformat(timespec="seconds")
        _save_progress(self.progress)

    def save_assessment(self, assessment_record: dict[str, Any]) -> None:
        """Append an assessment snapshot to the company history."""
        assessments: list[dict[str, Any]] = list(self.company.get("assessments", []))
        assessments.append(assessment_record)
        self.update(assessments=assessments)

    def save_roadmap_state(
        self,
        *,
        roadmap: Optional[dict[str, Any]],
        prioritized_topics: list[str],
        daily_plan: list[tuple[int, list[tuple[str, float]]]],
        interview_date_str: Optional[str],
        days_remaining: int,
        hours_per_day: float,
        weak_topics: list[str],
    ) -> None:
        """Persist roadmap output and initialise day-level progress tracking."""
        existing_progress: dict[str, Any] = dict(self.company.get("daily_plan_progress", {}))
        daily_plan_progress: dict[str, Any] = {}

        for day_num, _slots in daily_plan:
            key = str(day_num)
            if key in existing_progress:
                daily_plan_progress[key] = existing_progress[key]
            else:
                daily_plan_progress[key] = {
                    "completed": False,
                    "completed_at": None,
                }

        self.update(
            roadmap=roadmap,
            prioritized_topics=prioritized_topics,
            daily_plan_progress=daily_plan_progress,
            interview_date=interview_date_str,
            days_remaining=days_remaining,
            hours_per_day=hours_per_day,
            weak_topics=weak_topics,
        )


def _make_company_id(name: str) -> str:
    """Create a stable, filesystem-safe company identifier."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "company"
    return f"{slug}-{uuid.uuid4().hex[:8]}"


def _create_company_record(
    name: str,
    jd_analysis: dict[str, Any],
    jd_text: str,
) -> dict[str, Any]:
    """Build a new company entry for roadmap_progress.json."""
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "id": _make_company_id(name),
        "name": name,
        "created_at": now,
        "updated_at": now,
        "jd_analysis": jd_analysis,
        "jd_text": jd_text,
        "target_company": name,
        "interview_date": None,
        "hours_per_day": 2.0,
        "days_remaining": -1,
        "missing_skills": [],
        "weak_topics": [],
        "interview_rounds": _default_interview_rounds(),
        "current_round": DEFAULT_ROUND_TYPES[0],
        "roadmap": None,
        "prioritized_topics": [],
        "daily_plan_progress": {},
        "assessments": [],
        "resume_match": None,
    }


def _round_status_label(company: dict[str, Any]) -> str:
    """Short label for dashboard listings."""
    current = company.get("current_round", DEFAULT_ROUND_TYPES[0])
    rounds: list[dict[str, Any]] = company.get("interview_rounds", [])
    completed = sum(1 for r in rounds if r.get("status") == "completed")
    total = len(rounds) or len(DEFAULT_ROUND_TYPES)
    return f"{current} ({completed}/{total} done)"


def _display_company_summary(company: dict[str, Any]) -> None:
    """Show stored company state including rounds and progress."""
    _subsection(f"COMPANY — {company.get('name', 'Unknown')}")

    _kv("Current Round", company.get("current_round", "N/A"))
    _kv("Interview Date", company.get("interview_date") or "Not set")
    _kv("Study Hours / Day", company.get("hours_per_day", "N/A"))

    if company.get("days_remaining", -1) > 0:
        _kv("Days Remaining", company["days_remaining"])

    print("\n  Interview Rounds:")
    for rnd in company.get("interview_rounds", _default_interview_rounds()):
        name = rnd.get("name", "?")
        status = rnd.get("status", "pending")
        marker = " ← current" if name == company.get("current_round") else ""
        print(f"    • {name}: {status}{marker}")

    weak = company.get("weak_topics", [])
    if weak:
        print("\n  Weak Topics:")
        _bullet_list(weak[:6])

    missing = company.get("missing_skills", [])
    if missing:
        print("\n  Missing Skills:")
        _bullet_list(missing[:6])

    progress_map: dict[str, Any] = company.get("daily_plan_progress", {})
    if progress_map:
        done = sum(1 for d in progress_map.values() if d.get("completed"))
        print(f"\n  Study Progress: {done}/{len(progress_map)} days completed")

    assessments: list[dict[str, Any]] = company.get("assessments", [])
    if assessments:
        print(f"\n  Saved Assessments: {len(assessments)}")
        latest = assessments[-1]
        _kv("Latest Type", latest.get("type", "N/A"), indent=6)
        if latest.get("score") is not None:
            _kv("Latest Score", f"{latest['score']:.1f}%", indent=6)


def _manage_interview_rounds(session: CompanySession) -> None:
    """View and update interview rounds for the active company."""
    company = session.company

    while True:
        _subsection("INTERVIEW ROUNDS")
        _kv("Current Round", company.get("current_round", "N/A"))

        print("\n  Rounds:")
        for idx, rnd in enumerate(company.get("interview_rounds", _default_interview_rounds()), 1):
            name = rnd.get("name", "?")
            status = rnd.get("status", "pending")
            marker = "  ← CURRENT" if name == company.get("current_round") else ""
            print(f"    {idx}. {name} [{status}]{marker}")

        print("""
  1. Mark Current Round Complete & Advance
  2. Set Current Round Manually
  3. Back
""")
        choice = _prompt_choice("  Select option (1/2/3): ", choices=["1", "2", "3"])

        if choice == "3":
            break

        rounds: list[dict[str, Any]] = list(company.get("interview_rounds", _default_interview_rounds()))

        if choice == "1":
            current_name = company.get("current_round", DEFAULT_ROUND_TYPES[0])
            advanced = False

            for rnd in rounds:
                if rnd.get("name") == current_name:
                    rnd["status"] = "completed"
                    advanced = True
                    break

            if not advanced and rounds:
                rounds[0]["status"] = "completed"

            next_round = current_name
            for idx, rnd in enumerate(rounds):
                if rnd.get("name") == current_name and idx + 1 < len(rounds):
                    next_round = rounds[idx + 1]["name"]
                    break

            session.update(interview_rounds=rounds, current_round=next_round)
            print(f"\n  [OK] Advanced to round: {next_round}\n")

        elif choice == "2":
            round_names = [r.get("name", "") for r in rounds if r.get("name")]
            if not round_names:
                print("  [WARN] No rounds configured.")
                continue

            print("\n  Available rounds:\n")
            _numbered_list(round_names)
            pick = _prompt_int(
                f"\n  Select round number (1–{len(round_names)}): ",
                min_val=1,
                max_val=len(round_names),
            )
            selected = round_names[pick - 1]
            session.update(current_round=selected)
            print(f"\n  [OK] Current round set to: {selected}\n")


def _view_study_progress(session: CompanySession) -> None:
    """Display and update day-level roadmap completion."""
    company = session.company
    progress_map: dict[str, Any] = dict(company.get("daily_plan_progress", {}))

    if not progress_map:
        print("\n  [INFO] No study plan saved yet. Complete Interview Preparation first.\n")
        return

    _subsection("STUDY PROGRESS")

    day_keys = sorted(progress_map.keys(), key=lambda k: int(k) if k.isdigit() else 0)
    for day_key in day_keys:
        entry = progress_map[day_key]
        status = "completed" if entry.get("completed") else "pending"
        print(f"    Day {day_key}: {status}")

    print("""
  1. Mark a Day Complete
  2. Back
""")
    choice = _prompt_choice("  Select option (1/2): ", choices=["1", "2"])
    if choice == "2":
        return

    pick = _prompt_int(
        f"\n  Enter day number to mark complete (1–{len(day_keys)}): ",
        min_val=1,
        max_val=len(day_keys),
    )
    day_key = day_keys[pick - 1]
    progress_map[day_key] = {
        "completed": True,
        "completed_at": datetime.now().isoformat(timespec="seconds"),
    }
    session.update(daily_plan_progress=progress_map)
    print(f"\n  [OK] Day {day_key} marked complete.\n")


def _select_existing_company(progress: dict[str, Any]) -> Optional[CompanySession]:
    """Let the user pick a saved company and optionally manage rounds."""
    companies: dict[str, Any] = progress.get("companies", {})
    if not companies:
        print("\n  [INFO] No saved companies yet. Choose 'Add New Company'.\n")
        return None

    ordered = sorted(
        companies.values(),
        key=lambda c: c.get("updated_at", c.get("created_at", "")),
        reverse=True,
    )

    _subsection("EXISTING COMPANIES")
    print()
    for idx, company in enumerate(ordered, 1):
        interview = company.get("interview_date") or "No date"
        print(
            f"    {idx}. {company.get('name', 'Unknown')}  "
            f"[Round: {_round_status_label(company)}]  "
            f"Interview: {interview}"
        )

    pick = _prompt_int(
        f"\n  Select company (1–{len(ordered)}) or 0 to go back: ",
        min_val=0,
        max_val=len(ordered),
    )
    if pick == 0:
        return None

    company = ordered[pick - 1]
    session = CompanySession(progress, company["id"])
    _display_company_summary(session.company)

    print("""
  1. Continue With This Company
  2. Manage Interview Rounds
  3. View Study Progress
  4. Back
""")
    action = _prompt_choice("  Select option (1/2/3/4): ", choices=["1", "2", "3", "4"])

    if action == "2":
        _manage_interview_rounds(session)
        return _select_existing_company(progress)
    if action == "3":
        _view_study_progress(session)
        return _select_existing_company(progress)
    if action == "4":
        return None

    return session


def _add_new_company(progress: dict[str, Any]) -> Optional[CompanySession]:
    """Upload JD, analyse, and persist a new company record."""
    _subsection("ADD NEW COMPANY")

    jd_analysis, jd_text = step_jd_analysis()
    if jd_analysis is None or jd_text is None:
        print("\n  [SKIP] Company not created — JD analysis failed.\n")
        return None

    inferred_name = _infer_company_from_jd(jd_text, jd_analysis)
    print(f"\n  Detected company name: {inferred_name}")

    use_detected = _prompt_choice(
        "\n  Use detected name? (yes/no): ",
        choices=["yes", "no", "y", "n"],
    )

    if use_detected in {"yes", "y"}:
        company_name = inferred_name
    else:
        company_name = _prompt("  Enter company name: ")

    record = _create_company_record(company_name, jd_analysis, jd_text)
    progress.setdefault("companies", {})[record["id"]] = record
    progress["active_company_id"] = record["id"]
    _save_progress(progress)

    print(f"\n  [OK] Company '{company_name}' saved to roadmap_progress.json.\n")
    return CompanySession(progress, record["id"])


def _company_dashboard(progress: dict[str, Any]) -> Optional[CompanySession]:
    """
    Company dashboard — existing companies or add new.

    Returns an active CompanySession, or None when the user exits.
    """
    while True:
        _section("COMPANY DASHBOARD")
        print("""
  1. Existing Companies
  2. Add New Company
  3. Exit
""")

        choice = _prompt_choice(
            "  Enter your choice (1/2/3): ",
            choices=["1", "2", "3"],
        )

        if choice == "1":
            session = _select_existing_company(progress)
            if session is not None:
                return session
        elif choice == "2":
            session = _add_new_company(progress)
            if session is not None:
                return session
        else:
            return None


# ===========================================================================
# Topic helpers
# ===========================================================================

def _combine_jd_topics(jd_analysis: dict[str, Any]) -> list[str]:
    """
    Merge technologies, DSA topics, and CS topics into one ordered list
    with duplicates removed while preserving order.
    """
    technologies: list[str] = jd_analysis.get("technologies", [])
    dsa: list[str] = jd_analysis.get("dsa_topics", [])
    cs: list[str] = jd_analysis.get("cs_topics", [])

    combined: list[str] = []
    seen: set[str] = set()

    for item in technologies + dsa + cs:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key not in seen:
            seen.add(key)
            combined.append(cleaned)

    return combined


def _select_topic_and_assessment_type(
    jd_analysis: dict[str, Any],
) -> tuple[str, list[str], str]:
    """
    Let the user choose a topic from technologies + DSA + CS topics, then pick
    the assessment type (MCQ / Coding / Mixed).

    Returns (selected_topic, context_topics, assessment_type).
    """
    all_topics = _combine_jd_topics(jd_analysis)

    if not all_topics:
        all_topics = ["Data Structures", "Algorithms", "OOP", "DBMS"]
        print(f"  [WARN] No topics found in JD; using defaults: {all_topics}")

    _subsection("TOPIC SELECTION")
    print("\n  Available Topics:\n")
    _numbered_list(all_topics)

    topic_idx = _prompt_int(
        f"\n  Select topic number (1–{len(all_topics)}): ",
        min_val=1,
        max_val=len(all_topics),
    )
    selected_topic = all_topics[topic_idx - 1]
    print(f"  Selected: {selected_topic}")

    print("""
  Assessment Type:
    1. MCQ Quiz
    2. Coding Question
    3. Mixed Assessment
""")
    type_choice = _prompt_choice(
        "  Select assessment type (1/2/3): ",
        choices=["1", "2", "3"],
    )

    type_map = {"1": "mcq", "2": "coding", "3": "mixed"}
    assessment_type = type_map[type_choice]

    context_topics = all_topics[:6]
    if selected_topic not in context_topics:
        context_topics.insert(0, selected_topic)

    return selected_topic, context_topics, assessment_type


# ===========================================================================
# MCQ assessment — interactive, no answers until completion
# ===========================================================================

def _normalize_correct_letter(
    correct_raw: Any,
    options: list[str],
) -> str:
    """Map a correct_answer value to a letter (A/B/C/D)."""
    letter_map = {
        1: "A", 2: "B", 3: "C", 4: "D",
        "1": "A", "2": "B", "3": "C", "4": "D",
        "a": "A", "b": "B", "c": "C", "d": "D",
    }

    if isinstance(correct_raw, str):
        stripped = correct_raw.strip()
        if len(stripped) == 1 and stripped.upper() in OPTION_LETTERS[:4]:
            return stripped.upper()
        if stripped.casefold() in letter_map:
            return letter_map[stripped.casefold()]
        for idx, opt in enumerate(options):
            if str(opt).strip().casefold() == stripped.casefold():
                return OPTION_LETTERS[idx]

    mapped = letter_map.get(correct_raw)
    if mapped:
        return mapped

    if isinstance(correct_raw, int) and 1 <= correct_raw <= len(options):
        return OPTION_LETTERS[correct_raw - 1]

    return str(correct_raw).strip().upper()[:1] or "A"


def _collect_mcq_answers(mcqs: list[dict[str, Any]]) -> dict[str, str]:
    """Ask the user to answer MCQs one at a time without revealing answers."""
    user_answers: dict[str, str] = {}

    _section("MCQ ASSESSMENT")

    for idx, mcq in enumerate(mcqs, start=1):
        question_text = str(mcq.get("question", "")).strip()
        options: list[str] = mcq.get("options", [])

        print(f"\nQ{idx}. {question_text}\n")

        valid_letters = []
        for option_idx, option in enumerate(options[:4]):
            letter = OPTION_LETTERS[option_idx]
            valid_letters.append(letter.lower())
            print(f"   {letter}. {str(option).strip()}")

        if not valid_letters:
            valid_letters = ["a", "b", "c", "d"]

        answer = _prompt_choice(
            "\nEnter answer (A/B/C/D): ",
            valid_letters,
        )
        user_answers[str(idx)] = answer.upper()

    return user_answers


def _display_mcq_results(
    mcqs: list[dict[str, Any]],
    user_answers: dict[str, str],
) -> None:
    """Show score, correct answers, and explanations after the assessment."""
    _subsection("MCQ RESULTS")

    correct_count = 0

    for idx, mcq in enumerate(mcqs, start=1):
        qid = str(idx)
        options: list[str] = mcq.get("options", [])
        correct_letter = _normalize_correct_letter(mcq.get("correct_answer"), options)
        user_letter = user_answers.get(qid, "").upper()
        is_correct = user_letter == correct_letter

        if is_correct:
            correct_count += 1

        question_text = str(mcq.get("question", "")).strip()
        explanation = str(mcq.get("explanation", "")).strip()
        status = "CORRECT" if is_correct else "INCORRECT"

        print(f"\n  Q{idx}. {question_text}")
        _kv("Your answer", user_letter or "(no answer)", indent=6)
        _kv("Correct answer", correct_letter, indent=6)
        _kv("Result", status, indent=6)
        if explanation:
            print("      Explanation:")
            _wrap(explanation, indent=9)

    total = len(mcqs)
    score_pct = (correct_count / total * 100) if total else 0.0
    print(f"\n  Score: {correct_count}/{total} ({score_pct:.1f}%)")


def _build_performance_input(
    mcqs: list[dict[str, Any]],
    user_answers: dict[str, str],
    topic: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Convert MCQs and user answers into student_answers / correct_answers
    lists expected by analyze_performance().
    """
    student_answers: list[dict[str, Any]] = []
    correct_answers: list[dict[str, Any]] = []

    for idx, mcq in enumerate(mcqs):
        qid = str(idx + 1)
        options: list[str] = mcq.get("options", [])
        correct = _normalize_correct_letter(mcq.get("correct_answer"), options)

        correct_answers.append({"question_id": qid, "topic": topic, "answer": correct})
        student_answers.append(
            {"question_id": qid, "topic": topic, "answer": user_answers.get(qid, "")}
        )

    return student_answers, correct_answers


def _run_performance_analysis(
    mcqs: list[dict[str, Any]],
    user_answers: dict[str, str],
    topic: str,
) -> tuple[dict[str, Any], list[str]]:
    """
    Run performance analysis on actual user answers.

    Returns (perf_report, weak_topics).
    """
    _subsection("PERFORMANCE ANALYSIS")

    if not mcqs:
        print("  [SKIP] No MCQs available; skipping performance analysis.")
        return {}, []

    _display_mcq_results(mcqs, user_answers)

    student_answers, correct_answers = _build_performance_input(mcqs, user_answers, topic)

    print("\n  Generating performance report … please wait.\n")

    perf_report: dict[str, Any] = {}
    weak_topics: list[str] = []

    try:
        perf_report = analyze_performance(student_answers, correct_answers)
    except PerformanceAnalyzerError as exc:
        print(f"  [ERROR] Performance analysis failed: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] Unexpected error during performance analysis: {exc}")

    if perf_report:
        score: float = perf_report.get("score", 0.0)
        strong: list[str] = perf_report.get("strong_topics", [])
        weak_topics = perf_report.get("weak_topics", [])
        recommendations: list[str] = perf_report.get("recommendations", [])

        _kv("Overall Score", f"{score:.1f}%")

        print("\n  Strong Topics:")
        _bullet_list(strong) if strong else print("    (none identified)")

        print("\n  Weak Topics:")
        _bullet_list(weak_topics) if weak_topics else print("    (none identified)")

        print("\n  Recommendations:")
        for rec in recommendations:
            print("    • ", end="")
            _wrap(rec, indent=6)

    return perf_report, weak_topics


# ===========================================================================
# Coding question display and practice loop
# ===========================================================================

def _display_coding_question(cq: dict[str, Any]) -> None:
    """Display all available coding question fields, skipping missing ones."""
    if not cq:
        print("  [WARN] No coding question to display.")
        return

    title = str(cq.get("title", "")).strip()
    difficulty = str(cq.get("difficulty", "")).strip()
    statement = str(cq.get("problem_statement", "")).strip()
    constraints = cq.get("constraints")
    sample_input = cq.get("sample_input")
    sample_output = cq.get("sample_output")

    if title:
        _kv("Title", title)
    if difficulty:
        _kv("Difficulty", difficulty)
    if statement:
        print("\n  Problem Statement:")
        _wrap(statement, indent=4)

    if constraints:
        print("\n  Constraints:")
        if isinstance(constraints, list):
            _bullet_list([str(c).strip() for c in constraints if str(c).strip()])
        else:
            _wrap(str(constraints).strip(), indent=4)

    if sample_input is not None and str(sample_input).strip():
        print("\n  Sample Input:")
        _wrap(str(sample_input).strip(), indent=4)

    if sample_output is not None and str(sample_output).strip():
        print("\n  Sample Output:")
        _wrap(str(sample_output).strip(), indent=4)


def _run_coding_practice(
    topic: str,
    assessment_gen: AssessmentGenerator,
    initial_questions: Optional[list[dict[str, Any]]] = None,
) -> None:
    """
    Interactive coding practice: display questions and allow repeated generation
    until the user chooses to continue to the roadmap.
    """
    _section("CODING PRACTICE")

    pending: list[dict[str, Any]] = list(initial_questions or [])
    question_num = 0

    while True:
        if pending:
            cq = pending.pop(0)
        else:
            print("\n  Generating coding question … please wait.\n")
            try:
                cq = assessment_gen.generate_coding_question(topic=topic, difficulty="medium")
            except AssessmentGeneratorError as exc:
                print(f"  [ERROR] Coding question generation failed: {exc}")
                break
            except Exception as exc:  # noqa: BLE001
                print(f"  [ERROR] Unexpected error: {exc}")
                break

        question_num += 1
        print(f"\n  --- Coding Question {question_num} ---\n")
        _display_coding_question(cq)

        print("""
  Next Step:
    1. Generate Another Coding Question
    2. Continue To Roadmap
""")
        choice = _prompt_choice(
            "  Select option (1/2): ",
            choices=["1", "2"],
        )

        if choice == "2":
            break


# ===========================================================================
# Roadmap — prioritized topics and day-based display
# ===========================================================================

def _build_roadmap_topics(
    jd_analysis: dict[str, Any],
    weak_topics: list[str],
    missing_skills: list[str],
    days_remaining: int,
    hours_per_day: float,
) -> list[str]:
    """
    Build a prioritized, deduplicated topic list for roadmap generation.

    Priority order:
      1. Missing resume skills
      2. Weak topics from assessment
      3. JD technologies
      4. DSA topics
      5. CS topics
    """
    if days_remaining > 0:
        total_hours = days_remaining * hours_per_day
        print(
            f"  Preparation capacity: {days_remaining} days × "
            f"{hours_per_day} h/day = {total_hours:.1f} total hours"
        )
        print()

    technologies: list[str] = jd_analysis.get("technologies", [])
    dsa_topics: list[str] = jd_analysis.get("dsa_topics", [])
    cs_topics: list[str] = jd_analysis.get("cs_topics", [])

    seen: set[str] = set()
    prioritized: list[str] = []

    for group in (missing_skills, weak_topics, technologies, dsa_topics, cs_topics):
        for item in group:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            key = cleaned.casefold()
            if key and key not in seen:
                seen.add(key)
                prioritized.append(cleaned)

    if not prioritized:
        prioritized = ["Data Structures", "Algorithms", "OOP", "DBMS"]

    print("  Roadmap topic priority order:")
    _numbered_list(prioritized[:10])
    print()

    return prioritized


def _build_daily_study_plan(
    prioritized_topics: list[str],
    days_remaining: int,
    hours_per_day: float,
) -> list[tuple[int, list[tuple[str, float]]]]:
    """
    Build a day-by-day study plan from available days and hours.

    Returns a list of (day_number, [(topic, hours), ...]) tuples.
    """
    topics = prioritized_topics or ["General Preparation"]

    if days_remaining <= 0:
        days_remaining = max(len(topics), 7)

    topics_per_day = 2 if hours_per_day >= 2 else 1
    slot_hours = round(hours_per_day / topics_per_day, 1)

    plan: list[tuple[int, list[tuple[str, float]]]] = []

    for day in range(1, days_remaining + 1):
        day_slots: list[tuple[str, float]] = []
        for slot in range(topics_per_day):
            topic_idx = ((day - 1) * topics_per_day + slot) % len(topics)
            day_slots.append((topics[topic_idx], slot_hours))
        plan.append((day, day_slots))

    return plan


def _display_daily_roadmap(
    prioritized_topics: list[str],
    days_remaining: int,
    hours_per_day: float,
    target_company: str,
    roadmap: Optional[dict[str, Any]] = None,
) -> None:
    """Display a day-based study plan instead of week-based summaries."""
    _subsection("STUDY ROADMAP")

    effective_days = days_remaining if days_remaining > 0 else -1
    if roadmap and roadmap.get("days_remaining", -1) > 0:
        effective_days = roadmap["days_remaining"]

    if roadmap:
        _kv("Roadmap Type", roadmap.get("roadmap_type", "N/A"))
        _kv("Target Company", roadmap.get("target_company", target_company))
        if effective_days > 0:
            _kv("Days Remaining", effective_days)
        _kv("Study Hours / Day", roadmap.get("hours_per_day", hours_per_day))

    daily_plan = _build_daily_study_plan(
        prioritized_topics,
        effective_days if effective_days > 0 else max(len(prioritized_topics), 7),
        hours_per_day,
    )

    print("\n  Daily Study Plan:\n")

    for day_num, slots in daily_plan:
        print(f"    Day {day_num}")
        for topic, hrs in slots:
            hr_label = f"{hrs:g} hr" if hrs == 1 else f"{hrs:g} hrs"
            print(f"      {hr_label} {topic}")
        print()


def _generate_and_display_roadmap(
    jd_analysis: dict[str, Any],
    weak_topics: list[str],
    missing_skills: list[str],
    target_company: str,
    interview_date_str: Optional[str],
    days_remaining: int,
    hours_per_day: float,
    session: Optional[CompanySession] = None,
) -> None:
    """Build prioritized topics, generate roadmap, display day-based plan, and persist."""
    print("  Building prioritized topic list …\n")

    prioritized_topics = _build_roadmap_topics(
        jd_analysis=jd_analysis,
        weak_topics=weak_topics,
        missing_skills=missing_skills,
        days_remaining=days_remaining,
        hours_per_day=hours_per_day,
    )

    print("  Generating roadmap … please wait.\n")

    roadmap: Optional[dict[str, Any]] = None

    try:
        roadmap = generate_roadmap(
            weak_topics=prioritized_topics,
            target_company=target_company,
            interview_date=interview_date_str,
            hours_per_day=hours_per_day,
        )
    except (RoadmapGeneratorError, ValueError) as exc:
        print(f"  [ERROR] Roadmap generation failed: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] Unexpected error during roadmap generation: {exc}")

    effective_days = days_remaining if days_remaining > 0 else -1
    if roadmap and roadmap.get("days_remaining", -1) > 0:
        effective_days = roadmap["days_remaining"]

    daily_plan = _build_daily_study_plan(
        prioritized_topics,
        effective_days if effective_days > 0 else max(len(prioritized_topics), 7),
        hours_per_day,
    )

    _display_daily_roadmap(
        prioritized_topics=prioritized_topics,
        days_remaining=days_remaining,
        hours_per_day=hours_per_day,
        target_company=target_company,
        roadmap=roadmap,
    )

    if session is not None:
        session.save_roadmap_state(
            roadmap=roadmap,
            prioritized_topics=prioritized_topics,
            daily_plan=daily_plan,
            interview_date_str=interview_date_str,
            days_remaining=effective_days if effective_days > 0 else days_remaining,
            hours_per_day=hours_per_day,
            weak_topics=weak_topics,
        )
        print(f"  [OK] Roadmap progress saved for {session.company.get('name', 'company')}.\n")


# ===========================================================================
# STEP 1 + 2 — JD Upload & Analysis
# ===========================================================================

def step_jd_analysis() -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """
    STEP 1 — Parse JD file.
    STEP 2 — Analyze with JDAnalyzer.

    Returns (jd_analysis, jd_raw_text), either of which may be None on failure.
    """
    _section("STEP 1 — Upload Job Description")

    jd_text = _load_text_from_file("Job Description", supported="PDF or TXT")
    if not jd_text:
        print("  [SKIP] Cannot proceed without a job description.")
        return None, None

    _section("STEP 2 — JD ANALYSIS")

    print("  Analyzing job description … please wait.\n")

    analyzer = JDAnalyzer()
    try:
        analysis = analyzer.analyze(jd_text)
    except JDAnalyzerError as exc:
        print(f"  [ERROR] JD analysis failed: {exc}")
        return None, None
    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] Unexpected error during JD analysis: {exc}")
        return None, None

    print("  Skills:")
    _bullet_list(analysis.get("skills", []))

    print("\n  Technologies:")
    _bullet_list(analysis.get("technologies", []))

    print("\n  DSA Topics:")
    _bullet_list(analysis.get("dsa_topics", []))

    print("\n  CS Topics:")
    _bullet_list(analysis.get("cs_topics", []))

    return analysis, jd_text


# ===========================================================================
# OPTION 1 — Resume Match Analysis
# ===========================================================================

def option_resume_match(
    jd_analysis: dict[str, Any],
    session: Optional[CompanySession] = None,
) -> tuple[bool, list[str]]:
    """
    Upload resume → run ResumeMatcher → display full match report.

    Returns:
        (continue_to_prep: bool, missing_skills: list[str])
    """
    _section("OPTION 1 — RESUME MATCH ANALYSIS")

    resume_text = _load_text_from_file("Resume", supported="PDF or TXT")
    if not resume_text:
        print("  [SKIP] Resume could not be loaded; skipping match analysis.")
        return False, []

    print("\n  Running resume analysis … please wait.\n")

    matcher = ResumeMatcher()
    try:
        result = matcher.analyze_resume(resume_text=resume_text, jd_analysis=jd_analysis)
    except ResumeMatcherError as exc:
        print(f"  [ERROR] Resume match failed: {exc}")
        return False, []
    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] Unexpected error during resume analysis: {exc}")
        return False, []

    _subsection("RESUME MATCH RESULTS")

    match_score: int = result.get("match_score", 0)
    matched: list[str] = result.get("matched_skills", [])
    missing: list[str] = result.get("missing_skills", [])
    suggestions: list[str] = result.get("resume_suggestions", [])

    if match_score >= 80:
        ats_rating = "Excellent"
    elif match_score >= 60:
        ats_rating = "Good"
    elif match_score >= 40:
        ats_rating = "Average"
    else:
        ats_rating = "Needs Improvement"

    _kv("Match Score", f"{match_score}%")
    _kv("ATS Rating", ats_rating)

    print("\n  Matched Skills:")
    _bullet_list(matched) if matched else print("    (none)")

    print("\n  Missing Skills:")
    _bullet_list(missing) if missing else print("    (none)")

    print("\n  Resume Suggestions:")
    for idx, suggestion in enumerate(suggestions, 1):
        print(f"    {idx}. ", end="")
        _wrap(suggestion, indent=7)

    if session is not None:
        session.update(
            missing_skills=missing,
            resume_match={
                "match_score": match_score,
                "matched_skills": matched,
                "missing_skills": missing,
                "resume_suggestions": suggestions,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
            },
        )
        print("\n  [OK] Resume match results saved.\n")

    print()
    choice = _prompt_choice(
        "\nDo you also want Interview Preparation? (yes/no): ",
        choices=["yes", "no", "y", "n"],
    )
    return choice in {"yes", "y"}, missing


# ===========================================================================
# OPTION 2 — Interview Preparation (full flow)
# ===========================================================================

def option_interview_prep(
    jd_analysis: dict[str, Any],
    target_company: str,
    missing_skills: Optional[list[str]] = None,
    session: Optional[CompanySession] = None,
) -> None:
    """
    Full Interview Preparation flow:

    MCQ path:       MCQ → Performance → Roadmap
    Coding path:    Coding Practice (repeatable) → Roadmap
    Mixed path:     MCQ → Performance → Coding Practice → Roadmap
    """
    _section("OPTION 2 — INTERVIEW PREPARATION")

    if missing_skills is None:
        missing_skills = []

    if session is not None and not missing_skills:
        missing_skills = list(session.company.get("missing_skills", []))

    current_round = session.company.get("current_round") if session else None
    if current_round:
        print(f"\n  Preparing for {target_company} — Current Round: {current_round}")

    print()
    interview_date_str = _prompt_date(
        "  Enter your interview date (YYYY-MM-DD) or press Enter to skip: "
    )

    hours_per_day = _prompt_float(
        "  Hours available for study per day (e.g. 2.5): ",
        min_val=0.5,
        max_val=24.0,
    )

    days_remaining = -1
    if interview_date_str:
        try:
            interview_date_obj = datetime.strptime(interview_date_str, "%Y-%m-%d").date()
            days_remaining = (interview_date_obj - date.today()).days
        except ValueError:
            pass

    selected_topic, context_topics, assessment_type = _select_topic_and_assessment_type(
        jd_analysis
    )

    _subsection("ASSESSMENT GENERATION")
    print("  Generating assessment … please wait.\n")

    assessment_gen = AssessmentGenerator()
    weak_topics: list[str] = []
    perf_report: dict[str, Any] = {}

    try:
        if assessment_type == "mcq":
            mcq_list = assessment_gen.generate_mcq(
                topic=selected_topic,
                count=10,
                difficulty="medium",
            )
            mcqs = mcq_list or []

            if not mcqs:
                print("  [WARN] No MCQs were generated.")
            else:
                print(f"  [OK] Generated {len(mcqs)} MCQs on {selected_topic}.\n")
                user_answers = _collect_mcq_answers(mcqs)
                perf_report, weak_topics = _run_performance_analysis(
                    mcqs, user_answers, selected_topic
                )
                if session is not None:
                    session.save_assessment(
                        {
                            "id": uuid.uuid4().hex[:12],
                            "type": "mcq",
                            "topic": selected_topic,
                            "current_round": current_round,
                            "created_at": datetime.now().isoformat(timespec="seconds"),
                            "mcqs": mcqs,
                            "user_answers": user_answers,
                            "score": perf_report.get("score"),
                            "performance_report": perf_report,
                        }
                    )

        elif assessment_type == "coding":
            _run_coding_practice(selected_topic, assessment_gen)
            if session is not None:
                session.save_assessment(
                    {
                        "id": uuid.uuid4().hex[:12],
                        "type": "coding",
                        "topic": selected_topic,
                        "current_round": current_round,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                    }
                )

        else:  # mixed — MCQ round → performance → coding practice → roadmap
            assessment = assessment_gen.generate(
                topics=context_topics[:6],
                difficulty="medium",
                num_questions=10,
            )
            mcqs = assessment.get("mcqs", [])
            coding_questions = assessment.get("coding_questions", [])

            if mcqs:
                print(f"  [OK] Generated {len(mcqs)} MCQs.\n")
                user_answers = _collect_mcq_answers(mcqs)
                perf_report, weak_topics = _run_performance_analysis(
                    mcqs, user_answers, selected_topic
                )
            else:
                print("  [WARN] No MCQs were generated for the mixed assessment.")
                user_answers = {}

            if coding_questions:
                print(f"\n  [OK] {len(coding_questions)} coding question(s) ready for practice.\n")

            _run_coding_practice(
                selected_topic,
                assessment_gen,
                initial_questions=coding_questions,
            )

            if session is not None:
                session.save_assessment(
                    {
                        "id": uuid.uuid4().hex[:12],
                        "type": "mixed",
                        "topic": selected_topic,
                        "current_round": current_round,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                        "mcqs": mcqs,
                        "user_answers": user_answers if mcqs else {},
                        "score": perf_report.get("score") if perf_report else None,
                        "performance_report": perf_report if perf_report else {},
                        "coding_questions": coding_questions,
                    }
                )

    except AssessmentGeneratorError as exc:
        print(f"  [ERROR] Assessment generation failed: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] Unexpected error during assessment generation: {exc}")

    _generate_and_display_roadmap(
        jd_analysis=jd_analysis,
        weak_topics=weak_topics,
        missing_skills=missing_skills,
        target_company=target_company,
        interview_date_str=interview_date_str,
        days_remaining=days_remaining,
        hours_per_day=hours_per_day,
        session=session,
    )


# ===========================================================================
# OPTION 3 — AI Chat Assistant (standalone)
# ===========================================================================

def option_chat_assistant(
    jd_analysis: dict[str, Any],
    target_company: str,
    session: Optional[CompanySession] = None,
) -> None:
    """Interactive AI chat assistant — only runs when explicitly selected."""
    _section("OPTION 3 — AI CHAT ASSISTANT")

    print("\n  Ask placement preparation questions.")
    print("  Type 'exit' or 'quit' to return to the main menu.\n")

    weak_for_chat = _combine_jd_topics(jd_analysis)[:4]
    if session is not None:
        stored_weak = session.company.get("weak_topics", [])
        if stored_weak:
            weak_for_chat = stored_weak[:4]

    chat = ChatAssistant()
    chat.set_context(
        {
            "target_company": target_company,
            "weak_topics": weak_for_chat,
            "jd_analysis": jd_analysis,
            "current_round": session.company.get("current_round") if session else None,
        }
    )

    while True:
        question = input("  Enter your question: ").strip()

        if question.lower() in {"exit", "quit", "q"}:
            print("\n  Returning to main menu.\n")
            break

        if not question:
            question = "Explain Dynamic Programming with an example."
            print(f"  (Using example: {question})")

        print("\n  Thinking … please wait.\n")

        try:
            answer = chat.chat(question)
        except ChatAssistantError as exc:
            print(f"  [ERROR] Chat assistant failed: {exc}")
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"  [ERROR] Unexpected error in chat assistant: {exc}")
            continue

        if answer:
            _subsection("CHAT ASSISTANT RESPONSE")
            for para in answer.split("\n"):
                if para.strip():
                    _wrap(para, indent=4)
                else:
                    print()
            print()


# ===========================================================================
# Main entry point
# ===========================================================================

def main() -> None:
    """Orchestrate the full end-to-end demonstration workflow."""
    print(f"\n{DIVIDER}")
    print("  AI-POWERED PLACEMENT PREPARATION ASSISTANT")
    print("  End-to-End Demo")
    print(DIVIDER)

    progress = _load_progress()
    session = _company_dashboard(progress)

    if session is None:
        print("\n  [EXIT] No company selected. Goodbye.\n")
        return

    company = session.company
    jd_analysis: dict[str, Any] = company.get("jd_analysis", {})
    if not jd_analysis:
        print("\n  [EXIT] Selected company has no JD analysis. Exiting demo.")
        sys.exit(1)

    target_company = company.get("target_company") or company.get("name", "JD-Based Preparation")
    print(f"\n  Active company: {target_company}")
    print(f"  Current interview round: {company.get('current_round', DEFAULT_ROUND_TYPES[0])}")

    missing_skills: list[str] = list(company.get("missing_skills", []))

    while True:
        _section("MAIN MENU")
        print(f"""
  Company : {target_company}
  Round   : {session.company.get("current_round", DEFAULT_ROUND_TYPES[0])}

  1. Resume Match Analysis
  2. Interview Preparation
  3. AI Chat Assistant
  4. Exit
""")

        choice = _prompt_choice(
            "  Enter your choice (1/2/3/4): ",
            choices=["1", "2", "3", "4"],
        )

        if choice == "1":
            continue_to_prep, missing_skills = option_resume_match(jd_analysis, session=session)
            if continue_to_prep:
                option_interview_prep(
                    jd_analysis,
                    target_company=target_company,
                    missing_skills=missing_skills,
                    session=session,
                )
        elif choice == "2":
            option_interview_prep(
                jd_analysis,
                target_company=target_company,
                missing_skills=missing_skills,
                session=session,
            )
        elif choice == "3":
            option_chat_assistant(jd_analysis, target_company, session=session)
        else:
            break

    _section("DEMO COMPLETE")
    print("  Thank you for using the Placement Preparation Assistant.")
    print(f"  Progress saved in: {PROGRESS_FILE}")
    print(f"  Good luck with your interview!\n{DIVIDER}\n")


if __name__ == "__main__":
    main()
