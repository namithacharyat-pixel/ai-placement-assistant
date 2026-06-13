print("=" * 50)
print("TEST 4: ROADMAP GENERATOR")
print("=" * 50)

from ai_module.roadmap_generator import generate_roadmap

roadmap_result = generate_roadmap(
    weak_topics=["SQL", "Spring Boot", "AWS"],
    target_company="Amazon",
    interview_date="2026-06-18",
    hours_per_day=5
)

print(roadmap_result)