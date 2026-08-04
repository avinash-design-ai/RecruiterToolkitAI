from enum import Enum
import re

class Section(Enum):

    UNKNOWN = 0
    SUMMARY = 1
    SKILLS = 2
    EDUCATION = 3
    CERTIFICATIONS = 4
    EXPERIENCE = 5


SUMMARY_HEADERS = {
    "summary",
    "professional summary",
    "career summary",
    "profile",
    "professional profile",
    "objective",
    "career objective",
    "about me",
    "executive summary",
}

SKILL_HEADERS = {
    "technical skills",
    "skills",
    "core competencies",
    "technologies",
    "technical expertise",
    "technical proficiency",
    "tools",
}

EDUCATION_HEADERS = {
    "education",
    "academic qualification",
    "academic profile",
    "qualification",
}

CERT_HEADERS = {
    "certifications",
    "certification",
    "licenses",
    "training",
}

EXP_HEADERS = {
    "professional experience",
    "experience",
    "work experience",
    "employment history",
    "career history",
}

DATE_PATTERN = re.compile(
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec).*?(present|current|20\d\d|19\d\d)",
    re.I,
)

ROLE_WORDS = [
    "analyst",
    "developer",
    "engineer",
    "architect",
    "manager",
    "consultant",
    "lead",
    "administrator",
    "specialist",
    "scientist",
]


def classify(block):

    text = block.text.strip().lower()

    if not text:
        return Section.UNKNOWN

    if text in SUMMARY_HEADERS:
        return Section.SUMMARY

    if text in SKILL_HEADERS:
        return Section.SKILLS

    if text in EDUCATION_HEADERS:
        return Section.EDUCATION

    if text in CERT_HEADERS:
        return Section.CERTIFICATIONS

    if text in EXP_HEADERS:
        return Section.EXPERIENCE

    # Experience without heading
    if DATE_PATTERN.search(text):
        return Section.EXPERIENCE

    if any(role in text for role in ROLE_WORDS):
        return Section.EXPERIENCE

    return Section.UNKNOWN
