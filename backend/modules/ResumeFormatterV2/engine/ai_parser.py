import json
import ollama


SYSTEM_PROMPT = """
You are an expert resume parser.

You will receive ONE employment section from a resume.

Extract ONLY the following fields.

Return ONLY valid JSON.

{
    "company":"",
    "location":"",
    "role":"",
    "duration":"",
    "project":"",
    "responsibilities":[],
    "environment":[]
}

Rules

1. Never invent information.

2. If a field is missing, return "".

3. Responsibilities must be an array.

4. Environment must be an array.

5. Do not include explanations.

6. Output ONLY JSON.
"""


def parse_job(job_blocks):

    text = "\n".join(
        block.text
        for block in job_blocks
    )

    response = ollama.chat(

        model="qwen2.5:7b",

        messages=[

            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },

            {
                "role": "user",
                "content": text
            }

        ],

        options={
            "temperature": 0
        }

    )

    content = response["message"]["content"]

    try:

        return json.loads(content)

    except Exception:

        return {

            "company": "",

            "location": "",

            "role": "",

            "duration": "",

            "project": "",

            "responsibilities": [],

            "environment": []

        }
