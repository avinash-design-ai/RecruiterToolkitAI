from models import Resume

from parser import ResumeReader

from section_parser import SectionParser

from experience_parser import ExperienceParser

from field_parser import FieldParser


class ResumeParser:

    def __init__(self):

        self.reader = ResumeReader()

        self.section_parser = SectionParser()

        self.experience_parser = ExperienceParser()

        self.field_parser = FieldParser()

    # --------------------------------------------------------

    def lines_to_list(self, text):

        if not text:

            return []

        return [

            line.strip()

            for line in text.splitlines()

            if line.strip()

        ]

    # --------------------------------------------------------

    def parse(self, resume_file):

        print("\n========================================")
        print("Reading Resume")
        print("========================================")

        text = self.reader.read(resume_file)

        resume = Resume()

        # ----------------------------------------------------
        # Basic Details
        # ----------------------------------------------------

        import re

        email = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            text
        )

        if email:

            resume.email = email.group()

        phone = re.search(
            r"(\+?\d[\d\-\(\)\s]{8,}\d)",
            text
        )

        if phone:

            resume.phone = phone.group().strip()

        # Name

        for line in text.splitlines():

            line = line.strip()

            if not line:

                continue

            if "@" in line:

                continue

            if any(c.isdigit() for c in line):

                continue

            if len(line.split()) <= 5:

                resume.name = line

                break

        # ----------------------------------------------------
        # Sections
        # ----------------------------------------------------

        print("\nExtracting Sections...")

        sections = self.section_parser.extract(text)

        self.section_parser.print_sections(sections)

        resume.summary = self.lines_to_list(

            sections.get("summary", "")

        )

        resume.technical_skills = self.lines_to_list(

            sections.get("skills", "")

        )

        resume.education = self.lines_to_list(

            sections.get("education", "")

        )

        resume.certifications = self.lines_to_list(

            sections.get("certifications", "")

        )

        # ----------------------------------------------------
        # Experience
        # ----------------------------------------------------

        print("\nSplitting Jobs...")

        jobs = self.experience_parser.split_jobs(

            sections.get("experience", "")

        )

        self.experience_parser.print_jobs(jobs)

        print("\nExtracting Project Details...")

        for job in jobs:

            project = self.field_parser.extract(job)

            resume.projects.append(project)

        # ----------------------------------------------------

        print("\n========================================")

        print("Resume Parsed Successfully")

        print("========================================")

        print("Name :", resume.name)

        print("Phone :", resume.phone)

        print("Email :", resume.email)

        print("Summary :", len(resume.summary))

        print("Skills :", len(resume.technical_skills))

        print("Education :", len(resume.education))

        print("Certifications :", len(resume.certifications))

        print("Projects :", len(resume.projects))

        print("========================================\n")

        return resume
