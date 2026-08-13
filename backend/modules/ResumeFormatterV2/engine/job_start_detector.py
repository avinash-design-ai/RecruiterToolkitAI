import re
from dataclasses import dataclass


# ----------------------------------------
# Result
# ----------------------------------------

@dataclass
class JobStart:

    found: bool = False

    confidence: int = 0

    header_type: str = "UNKNOWN"

    client: str = ""

    employer: str = ""

    role: str = ""

    duration: str = ""

    project: str = ""

    location: str = ""

    raw_lines: list = None

    lines_used: int = 0
# ----------------------------------------
# Date Patterns
# ----------------------------------------

MONTHS = (
    "jan|january|feb|february|mar|march|apr|april|may|"
    "jun|june|jul|july|aug|august|sep|sept|september|"
    "oct|october|nov|november|dec|december"
)

DATE_REGEX = re.compile(

    rf"({MONTHS})\s+\d{{4}}.*?(present|\d{{4}})",

    re.IGNORECASE

)


def has_duration(text):

    return DATE_REGEX.search(text) is not None


# ----------------------------------------
# Field Detection
# ----------------------------------------

def extract_role(text):

    text = clean(text)

    lower = text.lower()

    # Role: Senior Developer
    if lower.startswith("role:"):

        return text.split(":", 1)[1].strip()

    # Role - Senior Developer
    if lower.startswith("role"):

        parts = re.split(r"[:\-]", text, maxsplit=1)

        if len(parts) == 2:

            return parts[1].strip()

    # Standalone role line
    if looks_like_role(text):

        return text

    return ""


def extract_project(text):

    lower = text.lower()

    if lower.startswith("project"):

        return text.split(":", 1)[-1].strip()

    return ""


def extract_company(text):

    lower = text.lower()

    # Ignore labeled fields
    if lower.startswith((
        "role",
        "project",
        "environment",
        "responsibilities",
        "client",
        "location"
    )):
        return ""

    # Ignore bullets
    if text.startswith(("•", "-", "*")):
        return ""

    # Ignore very long sentences
    if len(text.split()) > 8:
        return ""

    # Ignore date-only lines
    if has_duration(text) and len(text.split()) <= 5:
        return ""

    return text.strip()

# ----------------------------------------
# Confidence Engine
# ----------------------------------------

ROLE_WORDS = {

    "developer",
    "engineer",
    "architect",
    "analyst",
    "consultant",
    "lead",
    "manager",
    "administrator",
    "specialist",
    "programmer",
    "designer",
    "tester"

}


def looks_like_role(text):

    lower = text.lower()

    # Explicit Role:
    if lower.startswith("role"):

        return True

    # Common titles
    return any(word in lower for word in ROLE_WORDS)


def score_window(lines):

    job = JobStart()

    score = 0

    for line in lines:

        text = line.strip()

        if not text:

            continue

        # ------------------------
        # Duration
        # ------------------------

        if has_duration(text):

            if not job.duration:

                job.duration = text

                score += 40

        # ------------------------
        # Role
        # ------------------------

        if looks_like_role(text):

            if not job.role:

                role = extract_role(text)

                job.role = role if role else text

                score += 25

        # ------------------------
        # Project
        # ------------------------

        project = extract_project(text)

        if project:

            if not job.project:

                job.project = project

                score += 5

        # ------------------------
        # Company
        # ------------------------

        company = extract_company(text)

        if company:

            if not job.company:

                job.company = company

                score += 25

    job.confidence = score

    job.employer = job.company

    if (

        job.duration

        and job.company

        and score >= 65

    ):

        job.found = True

        job.header_type = "EMPLOYMENT"

    else:

        job.found = False

        job.header_type = "UNKNOWN"

    job.raw_lines = lines

    return job

# ----------------------------------------
# Detect Job Start
# ----------------------------------------

def detect_job_start(

    blocks,

    start_index,

    window_size=5

):

    lines = []

    used = 0

    for i in range(

        start_index,

        min(

            start_index + window_size,

            len(blocks)

        )

    ):

        text = blocks[i].text.strip()

        if not text:

            continue

        lines.append(text)

        used += 1

    result = score_window(lines)

    result.lines_used = used

    return result


