"""
Resume matcher for the Placement Preparation Assistant.

Extracts skills from a plain-text resume, compares them against a parsed
Job Description (JD) analysis, computes a match score, and uses Groq to
generate actionable resume improvement suggestions.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from ai_module.groq_client import (
    GroqClient,
    GroqClientError,
    generate_response,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ResumeMatcherError(GroqClientError):
    """Raised when resume matching or Groq interaction fails."""


# ---------------------------------------------------------------------------
# Private helpers  (mirrors assessment_generator conventions)
# ---------------------------------------------------------------------------


def _strip_code_fence(text: str) -> str:
    """Remove leading/trailing markdown code fences from a string."""
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    return cleaned.strip()


def _parse_json_response(raw: str) -> dict[str, Any]:
    """Parse a raw Groq response string into a dict, raising on failure."""
    if not raw or not raw.strip():
        raise ResumeMatcherError("Groq returned an empty response.")

    try:
        return json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        raise ResumeMatcherError("Groq returned invalid JSON.") from exc


def _normalise(items: list[str]) -> set[str]:
    """Lower-case and strip a list of skill/technology strings for comparison."""
    return {item.strip().lower() for item in items if item.strip()}


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------


class ResumeMatcher:
    """
    Compares a plain-text resume against a structured JD analysis and
    produces a match report with an actionable improvement plan.

    Expected ``jd_analysis`` shape (subset used here)::

        {
            "technologies": ["Python", "Docker", "Kubernetes", ...],
            "skills":        ["Problem Solving", "System Design", ...]
        }

    Output of :meth:`analyze_resume`::

        {
            "match_score":        int,          # 0-100
            "matched_skills":     list[str],
            "missing_skills":     list[str],
            "resume_suggestions": list[str]
        }
    """

    def __init__(self, groq_client: Optional[GroqClient] = None) -> None:
        self.groq_client = groq_client or GroqClient()

    # ------------------------------------------------------------------
    # 1. Extract resume skills
    # ------------------------------------------------------------------

    def extract_resume_skills(self, resume_text: str) -> list[str]:
        """
        Use Groq to extract a deduplicated list of technical and soft skills
        from plain-text resume content.

        Args:
            resume_text: Raw text of the candidate's resume.

        Returns:
            A list of skill strings, e.g. ``["Python", "REST APIs", ...]``.

        Raises:
            ValueError: If ``resume_text`` is empty.
            ResumeMatcherError: If Groq returns an invalid response.
        """
        if not resume_text or not resume_text.strip():
            raise ValueError("resume_text cannot be empty.")

        prompt = f"""
You are a resume parser.

Extract every technical skill, programming language, framework, tool,
platform, and relevant soft skill mentioned in the resume below.

Resume:
\"\"\"
{resume_text.strip()}
\"\"\"

Rules:
- Return each skill exactly as it appears (preserve casing).
- Deduplicate: include each skill only once.
- Do NOT include job titles, company names, or education institutions.
- Return ONLY valid JSON — no preamble, no explanation.

JSON format:
{{
  "skills": ["skill1", "skill2", ...]
}}
"""

        raw = generate_response(
            prompt,
            model=self.groq_client.model,
            api_key=self.groq_client.api_key,
            temperature=0.2,
            max_tokens=1000,
        )

        parsed = _parse_json_response(raw)
        skills: list[str] = parsed.get("skills", [])

        logger.debug("Extracted %d skills from resume.", len(skills))
        return skills

    # ------------------------------------------------------------------
    # 2. Compare resume skills with JD
    # ------------------------------------------------------------------

    def compare_with_jd(
        self,
        resume_skills: list[str],
        jd_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Compare extracted resume skills against JD technologies and skills.

        Match score formula::

            score = len(matched) / (len(jd_technologies) + len(jd_skills)) × 100

        Args:
            resume_skills: Skills extracted from the resume.
            jd_analysis:   Parsed JD dict containing ``"technologies"``
                           and ``"skills"`` keys.

        Returns:
            ::

                {
                    "match_score":    int,
                    "matched_skills": list[str],
                    "missing_skills": list[str]
                }

        Raises:
            ValueError: If ``jd_analysis`` is missing required keys or
                        the combined JD skill set is empty.
        """
        jd_technologies: list[str] = jd_analysis.get("technologies", [])
        jd_skills: list[str] = jd_analysis.get("skills", [])

        if not jd_technologies and not jd_skills:
            raise ValueError(
                "jd_analysis must contain at least one of "
                "'technologies' or 'skills' with non-empty values."
            )

        # Build normalised sets for comparison
        resume_set = _normalise(resume_skills)
        jd_tech_set = _normalise(jd_technologies)
        jd_skills_set = _normalise(jd_skills)
        jd_combined = jd_tech_set | jd_skills_set

        matched_normalised = resume_set & jd_combined
        missing_normalised = jd_combined - resume_set

        # Preserve original casing from JD for readability
        original_casing: dict[str, str] = {
            item.strip().lower(): item.strip()
            for item in (jd_technologies + jd_skills)
        }

        matched_skills = sorted(
            original_casing.get(n, n) for n in matched_normalised
        )
        missing_skills = sorted(
            original_casing.get(n, n) for n in missing_normalised
        )

        total_jd = len(jd_combined)
        match_score = round(len(matched_normalised) / total_jd * 100) if total_jd else 0

        logger.debug(
            "Comparison done — matched: %d, missing: %d, score: %d%%",
            len(matched_skills),
            len(missing_skills),
            match_score,
        )

        return {
            "match_score": match_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
        }

    # ------------------------------------------------------------------
    # 3. Generate resume improvement suggestions
    # ------------------------------------------------------------------

    def generate_resume_suggestions(
        self,
        resume_text: str,
        jd_analysis: dict[str, Any],
        missing_skills: list[str],
    ) -> list[str]:
        """
        Use Groq to generate concrete, actionable resume improvement
        suggestions based on the gap between the resume and the JD.

        Args:
            resume_text:    Raw text of the candidate's resume.
            jd_analysis:    Parsed JD dict (used for role/industry context).
            missing_skills: Skills present in the JD but absent in the resume.

        Returns:
            A list of suggestion strings, e.g.:

            - ``"Add Spring Boot project experience"``
            - ``"Highlight SQL optimisation work"``
            - ``"Include measurable impact (e.g. 'reduced latency by 30%')"``

        Raises:
            ResumeMatcherError: If Groq returns an invalid response.
        """
        role: str = jd_analysis.get("role", "the target role")
        job_description: str = jd_analysis.get("description", "")

        missing_str = (
            ", ".join(missing_skills) if missing_skills else "None identified"
        )

        prompt = f"""
You are a professional resume coach with expertise in tech hiring.

A candidate is applying for: {role}

Job description context:
\"\"\"
{job_description.strip()}
\"\"\"

Skills missing from the candidate's resume that appear in the JD:
{missing_str}

Candidate's current resume:
\"\"\"
{resume_text.strip()}
\"\"\"

Your task:
Generate 6-8 specific, actionable suggestions to improve the resume for
this role. Each suggestion must:
- Be a single, concrete action the candidate can take.
- Reference actual skills, tools, or experiences where relevant.
- Include guidance on adding measurable impact where applicable.
- Be no longer than one sentence.

Examples of good suggestions:
- "Add a Spring Boot project to the Projects section to demonstrate backend experience."
- "Highlight SQL query optimisation work with a measurable outcome (e.g. reduced query time by 40%)."
- "Include hands-on experience with AWS or GCP to address the cloud technology gap."
- "Quantify team collaboration impact (e.g. 'led a 4-person agile team to deliver X on time')."

Return ONLY valid JSON — no preamble, no explanation.

JSON format:
{{
  "suggestions": ["suggestion1", "suggestion2", ...]
}}
"""

        raw = generate_response(
            prompt,
            model=self.groq_client.model,
            api_key=self.groq_client.api_key,
            temperature=0.5,
            max_tokens=1500,
        )

        parsed = _parse_json_response(raw)
        suggestions: list[str] = parsed.get("suggestions", [])

        logger.debug("Generated %d resume suggestions.", len(suggestions))
        return suggestions

    # ------------------------------------------------------------------
    # 4. Full analysis pipeline
    # ------------------------------------------------------------------

    def analyze_resume(
        self,
        resume_text: str,
        jd_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """
        End-to-end resume analysis pipeline.

        Steps:
            1. Extract skills from the resume via Groq.
            2. Compare extracted skills against JD technologies + skills.
            3. Generate Groq-powered resume improvement suggestions.
            4. Return the consolidated match report.

        Args:
            resume_text: Raw plain-text resume content.
            jd_analysis: Parsed JD dict with at minimum::

                {
                    "technologies": [...],
                    "skills":       [...],
                    "role":         "...",   # optional but recommended
                    "description":  "..."    # optional but recommended
                }

        Returns:
            ::

                {
                    "match_score":        int,        # 0-100
                    "matched_skills":     list[str],
                    "missing_skills":     list[str],
                    "resume_suggestions": list[str]
                }

        Raises:
            ValueError: If inputs are invalid.
            ResumeMatcherError: If any Groq call fails.
        """
        logger.info("Starting resume analysis.")

        # Step 1 — extract skills
        resume_skills = self.extract_resume_skills(resume_text)

        # Step 2 — compare with JD
        comparison = self.compare_with_jd(resume_skills, jd_analysis)

        # Step 3 — generate suggestions
        suggestions = self.generate_resume_suggestions(
            resume_text=resume_text,
            jd_analysis=jd_analysis,
            missing_skills=comparison["missing_skills"],
        )

        result: dict[str, Any] = {
            "match_score": comparison["match_score"],
            "matched_skills": comparison["matched_skills"],
            "missing_skills": comparison["missing_skills"],
            "resume_suggestions": suggestions,
        }

        logger.info(
            "Resume analysis complete. Score: %d%%  Matched: %d  Missing: %d",
            result["match_score"],
            len(result["matched_skills"]),
            len(result["missing_skills"]),
        )

        return result


# ---------------------------------------------------------------------------
# Module-level convenience wrapper
# ---------------------------------------------------------------------------


def analyze_resume(
    resume_text: str,
    jd_analysis: dict[str, Any],
) -> dict[str, Any]:
    """
    Convenience wrapper around :class:`ResumeMatcher`.

    Example::

        result = analyze_resume(
            resume_text=open("resume.txt").read(),
            jd_analysis={
                "role": "Backend Engineer",
                "technologies": ["Python", "Django", "PostgreSQL", "Docker"],
                "skills": ["REST APIs", "System Design", "Agile"],
                "description": "We are looking for ..."
            }
        )
        print(result["match_score"])       # e.g. 75
        print(result["matched_skills"])    # ["Python", "Docker", ...]
        print(result["missing_skills"])    # ["Django", ...]
        print(result["resume_suggestions"])
    """
    matcher = ResumeMatcher()
    return matcher.analyze_resume(resume_text=resume_text, jd_analysis=jd_analysis)
