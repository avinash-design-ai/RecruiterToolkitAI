import json
from ollama import chat

from engine.header_patterns import PatternMatch


MODEL = "phi4-mini:latest"


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


PROMPT = """
You are an expert resume parser.

You will receive several lines from the beginning of ONE employment entry.

Extract ONLY these fields.

Employer
Client
Role
Location
Duration

Rules:

- Do not invent information.
- Do not invent information.
- Leave missing fields empty.
- Ignore responsibilities.
- Ignore environment.
- Ignore technologies.
- Ignore project description.
- Return ONLY JSON.
"""


def detect_header_ai(lines, inside_employment=False):

    result = PatternMatch()

    result.pattern = "AI"

    result.header_type = (
        "PROJECT"
        if inside_employment
        else "EMPLOYMENT"
    )

    result.raw_lines = lines

    try:

        text = "\n".join(lines)

        import time

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
                    "content": text
                }
            ]
        )

        print(f"AI call took {time.perf_counter() - start:.2f} seconds")

        data = json.loads(response.message.content)

        result.employer = data.get("employer", "").strip()
        result.client = data.get("client", "").strip()
        result.role = data.get("role", "").strip()
        result.location = data.get("location", "").strip()
        result.duration = data.get("duration", "").strip()

        # ---------------------------------------
        # Determine if this is a valid employment header
        # ---------------------------------------

        result.matched_fields = []

        if result.client:
            result.matched_fields.append("client")

        if result.employer:
            result.matched_fields.append("employer")

        if result.role:
            result.matched_fields.append("role")

        if result.location:
            result.matched_fields.append("location")

        if result.duration:
            result.matched_fields.append("duration")

        if (
            result.role
            and result.duration
            and (result.client or result.employer)
        ):
            result.confidence = 100
        else:
            result.confidence = 0

        return result

    except Exception as ex:

        result.errors.append(str(ex))
        result.confidence = 0

        return result
