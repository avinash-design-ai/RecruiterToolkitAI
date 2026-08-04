import re

from engine.state import State


MONTHS = (
    "jan|january|feb|february|mar|march|apr|april|may|"
    "jun|june|jul|july|aug|august|sep|sept|september|"
    "oct|october|nov|november|dec|december"
)

DATE_REGEX = re.compile(

    rf"({MONTHS})\s+\d{{4}}.*?(present|\d{{4}})",

    re.IGNORECASE

)


DEGREE_WORDS = {

    "b.tech",
    "btech",
    "m.tech",
    "mtech",
    "b.e",
    "m.e",
    "bachelor",
    "master",
    "mba",
    "b.sc",
    "m.sc",
    "phd",
    "diploma",
    "pg diploma"

}


CERTIFICATION_WORDS = {

    "certified",
    "certification",
    "aws",
    "azure",
    "oracle",
    "scrum",
    "itil",
    "pmp",
    "psm"

}


SKILL_HEADINGS = {

    "technical skills",
    "skills",
    "technical expertise",
    "technology",
    "core competencies",
    "skill set"

}


SUMMARY_HEADINGS = {

    "summary",
    "professional summary",
    "career summary",
    "profile",
    "professional profile"

}


EXPERIENCE_HEADINGS = {

    "experience",
    "professional experience",
    "employment history",
    "work experience"

}


EDUCATION_HEADINGS = {

    "education",
    "academic",
    "academics",
    "qualification"

}


CERTIFICATION_HEADINGS = {

    "certification",
    "certifications",
    "professional certifications",
    "license",
    "licenses"

}


def detect_state(lines):

    scores = {

        State.CONTACT: 0,
        State.SUMMARY: 0,
        State.SKILLS: 0,
        State.EXPERIENCE: 0,
        State.EDUCATION: 0,
        State.CERTIFICATION: 0

    }

    for line in lines:

        lower = line.lower().strip()

        # -------------------------
        # Headings
        # -------------------------

        if lower in SUMMARY_HEADINGS:

            scores[State.SUMMARY] += 100

        if lower in SKILL_HEADINGS:

            scores[State.SKILLS] += 100

        if lower in EXPERIENCE_HEADINGS:

            scores[State.EXPERIENCE] += 100

        if lower in EDUCATION_HEADINGS:

            scores[State.EDUCATION] += 100

        if lower in CERTIFICATION_HEADINGS:

            scores[State.CERTIFICATION] += 100

        # -------------------------
        # Experience Pattern
        # -------------------------

        if DATE_REGEX.search(lower):

            scores[State.EXPERIENCE] += 35

        # -------------------------
        # Degree
        # -------------------------

        if any(word in lower for word in DEGREE_WORDS):

            scores[State.EDUCATION] += 40

        # -------------------------
        # Certification
        # -------------------------

        if any(word in lower for word in CERTIFICATION_WORDS):

            scores[State.CERTIFICATION] += 40

        # -------------------------
        # Skills
        # -------------------------

        if "," in line or "|" in line:

            scores[State.SKILLS] += 10

    best_state = max(

        scores,

        key=scores.get

    )

    if scores[best_state] == 0:

        return None

    return best_state
