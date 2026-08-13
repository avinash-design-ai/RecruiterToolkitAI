import json
import ollama

from engine.document_reader import read_document

MODEL = "phi4-mini:latest"

SYSTEM_PROMPT = """
You are an expert resume parser.

Extract the resume into VALID JSON ONLY.

Never explain anything.

Never use markdown.

Return only one JSON object.

Schema:

{
  "name":"",
  "phone":"",
  "email":"",
  "linkedin":"",
  "summary":[],
  "technical_skills":{
      "Programming Languages":[],
      "Databases":[],
      "Cloud":[],
      "ETL / Big Data":[],
      "BI / Reporting":[],
      "DevOps":[],
      "Testing":[],
      "Methodologies":[],
      "Operating Systems":[],
      "Others":[]
  },
  "experience":[
      {
          "company":"",
          "location":"",
          "role":"",
          "duration":"",
          "project":"",
          "responsibilities":[],
          "environment":[]
      }
  ],
  "education":[],
  "certifications":[]
}

Rules:

- Never invent information.
- If data is missing, leave it blank.
- Preserve every responsibility.
- Preserve every job.
- Return valid JSON only.
"""

# ----------------------------------------------------

import os

folder = r"D:\Avinash\avi itech\myresumes\test resumes"

resume_file = "Vrushali_Patki.docx"

resume = read_document(
    os.path.join(folder, resume_file)
)

text = "\n".join(
    block.text
    for block in resume.blocks
)

print("Sending resume to Phi-4 Mini...")

response = ollama.chat(
    model=MODEL,
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

print(content)

try:

    parsed = json.loads(content)

    with open(
        "resume.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            parsed,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("\n✅ resume.json created")

except Exception as ex:

    print("\n❌ JSON parsing failed")

    print(ex)
