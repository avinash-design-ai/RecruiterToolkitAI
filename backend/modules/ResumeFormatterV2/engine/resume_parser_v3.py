from engine.models import Resume
from engine.state import State
from engine.section_mapper import map_sections


class ResumeParserV3:

    def __init__(self, document):

        self.document = document

        self.resume = Resume()

        self.state = State.CONTACT

    def parse(self):

        sections = map_sections(self.document)

        self.state = State.CONTACT

        for block in sections.header:
            text = block.text.strip()
            if text:
                self.handle_header(text)

        self.state = State.SUMMARY

        for block in sections.summary:
            text = block.text.strip()
            if text:
                self.handle_summary(text)

        self.state = State.SKILLS

        for block in sections.skills:
            text = block.text.strip()
            if text:
                self.handle_skills(text)

        self.state = State.EXPERIENCE

        for block in sections.experience:
            text = block.text.strip()
            if text:
                self.handle_experience(text)

        self.state = State.EDUCATION

        for block in sections.education:
            text = block.text.strip()
            if text:
                self.handle_education(text)

        self.state = State.CERTIFICATION

        for block in sections.certifications:
            text = block.text.strip()
            if text:
                self.handle_certification(text)

        self.debug()

        return self.resume

    def handle_header(self, text):

        pass

    def handle_summary(self, text):

        self.resume.summary.append(text)

    def handle_skills(self, text):

        if not hasattr(self.resume, "raw_skills"):

            self.resume.raw_skills = []

        self.resume.raw_skills.append(text)

    def handle_experience(self, text):

        if not hasattr(self.resume, "raw_experience"):

            self.resume.raw_experience = []

        self.resume.raw_experience.append(text)

    def handle_education(self, text):

        if not hasattr(self.resume, "raw_education"):

            self.resume.raw_education = []

        self.resume.raw_education.append(text)

    def handle_certification(self, text):

        if not hasattr(self.resume, "raw_certifications"):

            self.resume.raw_certifications = []

        self.resume.raw_certifications.append(text)

    def debug(self):

        print("\n========== V3 ==========")

        print("\nCurrent State:")
        print(self.state)

        print("\nSummary:")
        print(getattr(self.resume, "summary", []))

        print("\nSkills:")
        print(getattr(self.resume, "raw_skills", []))

        print("\nExperience:")
        print(getattr(self.resume, "raw_experience", []))

        print("\nEducation:")
        print(getattr(self.resume, "raw_education", []))

        print("\nCertifications:")
        print(getattr(self.resume, "raw_certifications", []))

        print("========================")
