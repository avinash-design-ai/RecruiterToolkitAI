"""
field_parser.py
Recruiter's Toolkit
"""

import re

from models import Project

from knowledge_base import (
    CLIENT_LABELS,
    ROLE_LABELS,
    PROJECT_LABELS,
    LOCATION_LABELS,
    DURATION_LABELS,
    RESPONSIBILITY_LABELS,
    ENVIRONMENT_LABELS,
    TECHNOLOGY_KEYWORDS,
    US_STATE_CODES,
    US_STATE_NAMES,
    WORK_MODES,
    ROLE_KEYWORDS,
    starts_with_any,
    contains_date,
)


class FieldParser:

    # --------------------------------------------------

    def extract(self, job_text):

        project = Project()

        if self.parse_labeled(job_text, project):

            pass

        elif self.parse_company_first(job_text, project):

            pass

        elif self.parse_three_line(job_text, project):

            pass

        else:

            self.parse_single_line(job_text, project)

        self.extract_responsibilities(job_text, project)

        self.extract_environment(job_text, project)

        return project

    # --------------------------------------------------
    # Strategy 1
    # Client:
    # Role:
    # Duration:
    # --------------------------------------------------

    def parse_labeled(self, text, project):

        found = False

        for line in text.splitlines():

            s = line.strip()

            if starts_with_any(s, CLIENT_LABELS):

                project.client = self.after_colon(s)

                found = True

            elif starts_with_any(s, LOCATION_LABELS):

                project.location = self.after_colon(s)

                found = True

            elif starts_with_any(s, ROLE_LABELS):

                project.role = self.after_colon(s)

                found = True

            elif starts_with_any(s, DURATION_LABELS):

                project.duration = self.after_colon(s)

                found = True

            elif starts_with_any(s, PROJECT_LABELS):

                project.project_name = self.after_colon(s)

                found = True

        return found

    # --------------------------------------------------
    # Strategy 2
    # Bank of America
    # Senior Data Engineer
    # Mar 2024 - Present
    # --------------------------------------------------

    def parse_company_first(self, text, project):

        lines = [

            line.strip()

            for line in text.splitlines()

            if line.strip()

        ]

        if len(lines) < 3:

            return False

        project.client = lines[0]

        project.role = lines[1]

        for line in lines:

            if contains_date(line):

                project.duration = line

                break

        return True

    # --------------------------------------------------
    # Strategy 3
    #
    # USAC, Washington, DC
    #
    # Technical Project Analyst
    #
    # Oct 2023 - Present
    # --------------------------------------------------

    def parse_three_line(self, text, project):

        lines = [

            line.strip()

            for line in text.splitlines()

            if line.strip()

        ]

        if len(lines) < 3:

            return False

        header = lines[0]

        location = ""

        for state in US_STATE_CODES:

            if "," + state in header.upper():

                idx = header.upper().rfind("," + state)

                left = header[:idx]

                right = header[idx + 1 :]

                project.client = left.rsplit(",", 1)[0].strip()

                location = left.rsplit(",", 1)[1].strip() + "," + right

                project.location = location.strip()

                break

        if not project.location:

            for state in US_STATE_NAMES:

                if state.lower() in header.lower():

                    pieces = header.split(",")

                    if len(pieces) >= 2:

                        project.client = pieces[0].strip()

                        project.location = ",".join(
                            pieces[1:]
                        ).strip()

                        break

        if not project.client:

            return False

        project.role = lines[1]

        for line in lines:

            if contains_date(line):

                project.duration = line

                break

        return True

    # --------------------------------------------------
    # Strategy 4
    #
    # HCL / USAA, Plano, TX
    # Lead ETL Developer, Sept'21-Till Date
    # --------------------------------------------------

    def parse_single_line(self, text, project):

        lines = [

            line.strip()

            for line in text.splitlines()

            if line.strip()

        ]

        if len(lines) == 0:

            return False

        header = lines[0]

        if contains_date(header):

            project.duration = header

        for role in ROLE_KEYWORDS:

            if role.lower() in header.lower():

                project.role = header

                break

        return True

    # --------------------------------------------------

    def extract_responsibilities(self, text, project):

        bullets = []

        for line in text.splitlines():

            s = line.strip()

            if not s:

                continue

            if starts_with_any(s, ENVIRONMENT_LABELS):

                break

            if s.startswith(("•", "-", "*")):

                bullets.append(

                    s.lstrip("•-* ").strip()

                )

        project.responsibilities = bullets

    # --------------------------------------------------

    def extract_environment(self, text, project):

        env = []

        for tech in TECHNOLOGY_KEYWORDS:

            if tech.lower() in text.lower():

                env.append(tech)

        project.environment = ", ".join(

            sorted(set(env))

        )

    # --------------------------------------------------

    def after_colon(self, text):

        if ":" in text:

            return text.split(":", 1)[1].strip()

        return text.strip()
