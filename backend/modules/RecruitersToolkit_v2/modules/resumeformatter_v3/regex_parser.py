import re
from models import Project


class RegexParser:

    def __init__(self):

        self.sections = {

            "summary": [
                "summary",
                "professional summary",
                "profile",
                "professional profile",
                "career summary",
                "career profile",
                "objective",
                "career objective"
            ],

            "skills": [
                "technical skills",
                "skills",
                "core competencies",
                "technical expertise",
                "technologies",
                "technology"
            ],

            "education": [
                "education",
                "academic",
                "academic qualification",
                "qualification"
            ],

            "certifications": [
                "certifications",
                "certification"
            ],

            "experience": [
                "professional experience",
                "work experience",
                "employment history",
                "experience",
                "projects",
                "professional projects"
            ]

        }

    # ----------------------------------------------------
    # BASIC INFO
    # ----------------------------------------------------

    def extract_email(self, text):

        m = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            text
        )

        return m.group(0) if m else ""

    def extract_phone(self, text):

        m = re.search(
            r"(\+?\d[\d\-\(\)\s]{8,}\d)",
            text
        )

        return m.group(0).strip() if m else ""

    def extract_linkedin(self, text):

        m = re.search(

            r"(https?://)?(www\.)?linkedin\.com/[^\s]+",

            text,

            re.IGNORECASE

        )

        return m.group(0) if m else ""

    def extract_name(self, text):

        ignore = [

            "summary",
            "profile",
            "resume",
            "curriculum vitae",
            "objective"

        ]

        for line in text.splitlines()[:15]:

            line = line.strip()

            if not line:
                continue

            lower = line.lower()

            if any(x in lower for x in ignore):
                continue

            if "@" in line:
                continue

            if any(ch.isdigit() for ch in line):
                continue

            if len(line.split()) <= 5:

                return line

        return ""

    # ----------------------------------------------------
    # SECTION EXTRACTION
    # ----------------------------------------------------

    def clean(self, line):

        return (

            line.lower()

            .replace(":", "")

            .replace("-", "")

            .replace("|", "")

            .strip()

        )

    def get_sections(self, text):

        lines = text.splitlines()

        sections = {}

        current = None

        buffer = []

        for line in lines:

            value = self.clean(line)

            found = None

            for section, headings in self.sections.items():

                if any(h in value for h in headings):

                    found = section
                    break

            if found:

                if current:

                    sections[current] = "\n".join(buffer).strip()

                current = found

                buffer = []

                continue

            if current:

                buffer.append(line)

        if current:

            sections[current] = "\n".join(buffer).strip()

        return sections

    # ----------------------------------------------------
    # SIMPLE SECTIONS
    # ----------------------------------------------------

    def extract_summary(self, text):

        return self.get_sections(text).get(
            "summary",
            ""
        )

    def extract_skills(self, text):

        return self.get_sections(text).get(
            "skills",
            ""
        )

    def extract_education(self, text):

        return self.get_sections(text).get(
            "education",
            ""
        )

    def extract_certifications(self, text):

        return self.get_sections(text).get(
            "certifications",
            ""
        )

    def extract_experience(self, text):

        return self.get_sections(text).get(
            "experience",
            ""
        )

    # ----------------------------------------------------
    # PROJECT PARSER
    # ----------------------------------------------------

    def extract_projects(self, experience_text):

        if not experience_text:

            return []

        lines = experience_text.splitlines()

        projects = []

        current = None

        responsibilities = []

        for line in lines:

            value = line.strip()

            lower = value.lower()

            if lower.startswith("client"):

                if current:

                    current.responsibilities = responsibilities

                    projects.append(current)

                current = Project()

                responsibilities = []

                current.client = value.split(":", 1)[-1].strip()

            elif current and lower.startswith("role"):

                current.role = value.split(":", 1)[-1].strip()

            elif current and lower.startswith("duration"):

                current.duration = value.split(":", 1)[-1].strip()

            elif current and lower.startswith("location"):

                current.location = value.split(":", 1)[-1].strip()

            elif current and lower.startswith("project"):

                current.project_name = value.split(":", 1)[-1].strip()

            elif current and lower.startswith("environment"):

                current.environment = value.split(":", 1)[-1].strip()

            elif current and value.startswith("•"):

                responsibilities.append(

                    value.replace("•", "").strip()

                )

        if current:

            current.responsibilities = responsibilities

            projects.append(current)

        return projects
