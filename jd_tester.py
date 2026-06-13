print("=" * 50)
print("TEST 1: JD ANALYZER")
print("=" * 50)

from ai_module.jd_analyzer import analyze_job_description

jd = """
Software Engineer Intern

Requirements:
Java
Spring Boot
SQL
DSA
OOPs
DBMS
"""

jd_result = analyze_job_description(jd)

print(jd_result)

print("\n\n")

# --------------------------------------------------

print("=" * 50)
print("TEST 2: ASSESSMENT GENERATOR")
print("=" * 50)

from ai_module.assessment_generator import generate_assessment

assessment_result = generate_assessment(jd_result)

print(assessment_result)

print("\n\n")

# --------------------------------------------------

print("=" * 50)
print("TEST 3: PERFORMANCE ANALYZER")
print("=" * 50)

from ai_module.performance_analyzer import analyze_performance

student_answers = [
    {
        "question_id": "q1",
        "topic": "Arrays",
        "answer": "A"
    },
    {
        "question_id": "q2",
        "topic": "SQL",
        "answer": "B"
    },
    {
        "question_id": "q3",
        "topic": "OOPs",
        "answer": "C"
    }
]

correct_answers = [
    {
        "question_id": "q1",
        "topic": "Arrays",
        "answer": "A"
    },
    {
        "question_id": "q2",
        "topic": "SQL",
        "answer": "D"
    },
    {
        "question_id": "q3",
        "topic": "OOPs",
        "answer": "C"
    }
]

performance_result = analyze_performance(
    student_answers,
    correct_answers
)

print(performance_result)

# --------------------------------------------------

print("=" * 50)
print("TEST 4: ROADMAP GENERATOR")
print("=" * 50)

from ai_module.roadmap_generator import generate_roadmap

roadmap_result = generate_roadmap(
    weak_topics=performance_result["weak_topics"],
    target_company="Amazon"
)

print(roadmap_result)
# --------------------------------------------------

print("=" * 50)
print("TEST 5: CHAT ASSISTANT")
print("=" * 50)

from ai_module.chat_assistant import ask_question

response = ask_question(
    "Explain Dynamic Programming in simple words."
)

print(response)