from ai_module.groq_client import generate_response

response = generate_response(
    "Say hello in one sentence."
)

print(response)