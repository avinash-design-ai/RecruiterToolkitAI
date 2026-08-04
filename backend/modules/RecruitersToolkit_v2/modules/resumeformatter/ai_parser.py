ai_parser.py (starter)

import json from models import Resume, Project from llm import ask_ai

SYSTEM_PROMPT = ’’’ You are an expert IT Resume Parser.

Return ONLY valid JSON.

Extract: - name - phone - email - linkedin - summary - education -
technical_skills (categorized) - certifications - projects ’’’

def parse_resume_ai(resume_text: str) -> Resume: response =
ask_ai(SYSTEM_PROMPT, resume_text)

    data = json.loads(response)

    resume = Resume()

    resume.name = data.get("name", "")
    resume.phone = data.get("phone", "")
    resume.email = data.get("email", "")
    resume.linkedin = data.get("linkedin", "")

    resume.summary = data.get("summary", [])
    resume.education = data.get("education", [])
    resume.technical_skills = data.get("technical_skills", {})
    resume.certifications = data.get("certifications", [])

    for p in data.get("projects", []):
        project = Project()
        project.client = p.get("client", "")
        project.project_name = p.get("project_name", "")
        project.role = p.get("role", "")
        project.duration = p.get("duration", "")
        project.location = p.get("location", "")
        project.description = p.get("description", "")
        project.environment = p.get("environment", "")
        project.responsibilities = p.get("responsibilities", [])
        resume.projects.append(project)

    return resume
