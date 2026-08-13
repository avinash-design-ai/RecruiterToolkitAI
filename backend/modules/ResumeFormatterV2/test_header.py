from engine.ai_header_detector import detect_header_ai

window = [
    "CGI, Toronto, Canada",
    "Project: Debit Applications | Client: TD",
    "Role: batch specialist / Technical Lead",
]

result = detect_header_ai(window, False)

print("\n===== RESULT =====")
print("Type      :", result.header_type)
print("Confidence:", result.confidence)
print("Employer  :", result.employer)
print("Client    :", result.client)
print("Role      :", result.role)
print("Location  :", result.location)
print("Duration  :", result.duration)
