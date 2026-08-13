import json
import time
from ollama import chat

MODEL = "phi4-mini:latest"

PROMPT = """
You are repairing a resume parsed by Python.

Python has already extracted most fields.

Only fill EMPTY fields.

Never change fields that already contain values.

Return only JSON.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "employer": {"type": "string"},
        "client": {"type": "string"},
        "role": {"type": "string"},
        "location": {"type": "string"},
        "duration": {"type": "string"}
    },
    "required": [
        "employer",
        "client",
        "role",
        "location",
        "duration"
    ]
}


def repair_header(job, header_lines):

    # Nothing missing, no need to call AI
    if all([
        job.employer,
        job.client,
        job.role,
        job.location,
        job.duration
    ]):
        return job

    prompt = f"""
Python extracted:

Employer: {job.employer}
Client: {job.client}
Role: {job.role}
Location: {job.location}
Duration: {job.duration}

Original Header:

{chr(10).join(header_lines)}

Only fill the EMPTY fields.
Do NOT change fields that already have values.
Return ONLY valid JSON.
"""

    print("\n================ AI REPAIR ================")
    print("Python extracted:")
    print(f"Employer : {job.employer}")
    print(f"Client   : {job.client}")
    print(f"Role     : {job.role}")
    print(f"Location : {job.location}")
    print(f"Duration : {job.duration}")

    print("\nOriginal Header:")
    print("\n".join(header_lines))

    start = time.perf_counter()

    response = chat(
        model=MODEL,
        think=False,
        format=SCHEMA,
        messages=[
            {
                "role": "system",
                "content": PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    print(f"\nAI repair took {time.perf_counter() - start:.2f} seconds")

    data = json.loads(response.message.content)

    print("\nAI Returned:")
    print(json.dumps(data, indent=2))

    if not job.employer:
        job.employer = data.get("employer", "").strip()

    if not job.client:
        job.client = data.get("client", "").strip()

    if not job.role:
        job.role = data.get("role", "").strip()

    if not job.location:
        job.location = data.get("location", "").strip()

    if not job.duration:
        job.duration = data.get("duration", "").strip()

    print("\nFinal Job:")
    print(f"Employer : {job.employer}")
    print(f"Client   : {job.client}")
    print(f"Role     : {job.role}")
    print(f"Location : {job.location}")
    print(f"Duration : {job.duration}")
    print("===========================================\n")

    return job
