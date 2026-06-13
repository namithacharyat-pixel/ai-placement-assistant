from ai_module.resume_matcher import analyze_resume

resume_text = """
Java
SQL
HTML
CSS
React
Git
Problem Solving
"""

jd_analysis = {
    "role": "Backend Engineer",
    "description": "Looking for Java, Spring Boot, SQL, AWS developers",
    "technologies": [
        "Java",
        "Spring Boot",
        "SQL",
        "AWS"
    ],
    "skills": [
        "Problem Solving",
        "Communication"
    ]
}

result = analyze_resume(
    resume_text,
    jd_analysis
)

print(result)