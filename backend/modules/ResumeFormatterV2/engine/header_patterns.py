from dataclasses import dataclass
from abc import ABC, abstractmethod
import re

from engine.rules import (
    DATE_PATTERN,
    ROLE_KEYWORDS,
    MONTH_MAP,
    LOCATION_KEYWORDS
)


# -------------------------------------------------------
# Pattern Match
# -------------------------------------------------------

@dataclass
class PatternMatch:

    pattern: str = ""

    header_type: str = "UNKNOWN"

    confidence: int = 0

    employer: str = ""

    client: str = ""

    location: str = ""

    role: str = ""

    duration: str = ""

    project: str = ""

    raw_lines: list = None

    matched_fields: list = None

    errors: list = None

    def __post_init__(self):

        if self.raw_lines is None:
            self.raw_lines = []

        if self.matched_fields is None:
            self.matched_fields = []

        if self.errors is None:
            self.errors = []


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

import re

# -------------------------------------------------------
# Text Helpers
# -------------------------------------------------------

SEPARATORS = [
    "|",
    "/",
    "\\",
    " - ",
    " – ",
    " — "
]


def clean(text):

    if text is None:
        return ""

    return " ".join(str(text).split()).strip()


def normalize(text):

    return re.sub(
        r"\s+",
        " ",
        clean(text)
    ).strip()


# -------------------------------------------------------
# Header Splitter
# -------------------------------------------------------

def split_header(line):
    """
    Splits

    Client | Role | Duration

    Employer / Client | Role | Duration

    Client - Remote | Role | Duration
    """

    line = normalize(line)

    parts = [line]

    for sep in SEPARATORS:

        if sep in line:

            parts = [
                normalize(x)
                for x in line.split(sep)
                if normalize(x)
            ]

            break

    return parts


# -------------------------------------------------------
# Duration
# -------------------------------------------------------

from engine.rules import MONTH_MAP


def normalize_month(month):

    if not month:

        return ""

    return MONTH_MAP.get(
        month.lower(),
        month.title()[:3]
    )


def extract_duration(text):

    """
    Extracts employment duration and removes it
    from the remaining text.

    Examples

    Sep 2016 - Present

    September 2016 – March 2020

    Jan 2020 to Current
    """

    text = normalize(text)

    match = DATE_PATTERN.search(text)

    print("TEXT     :", repr(text))

    if match:
        print("MATCHED  :", repr(match.group()))

    if not match:

        return "", text

    start = match.group(1)

    end = match.group(2)

    # --------------------------
    # Normalize Month Names
    # --------------------------

    start_parts = start.split()

    if len(start_parts) >= 2:

        start = (
            normalize_month(start_parts[0])
            + " "
            + start_parts[1]
        )

    else:

        start = normalize_month(start_parts[0])

    if end:

        end_parts = end.split()

        if len(end_parts) >= 2:

            end = (
                normalize_month(end_parts[0])
                + " "
                + end_parts[1]
            )

        else:

            end = end.title()

        duration = f"{start} - {end}"

    else:

        duration = start

    remaining = normalize(

        text.replace(match.group(), "")

    )

    remaining = remaining.strip(

        "|,-– "

    )

    return duration, remaining


# -------------------------------------------------------
# Employer / Client
# -------------------------------------------------------

def split_employer_client(text):
    """
    Splits employer/client when both are present.

    Examples

    Infosys / Apple

    Infosys | Apple

    Employer: Infosys
    Client: Apple

    Infosys (Client: Apple)

    Otherwise the entire text is treated
    as the Client.
    """

    text = normalize(text)

    if not text:

        return "", ""

    lower = text.lower()

    # -----------------------------------
    # Employer: ... Client: ...
    # -----------------------------------

    employer_match = re.search(
        r"employer\s*:\s*(.*?)(?:client\s*:|$)",
        text,
        re.IGNORECASE
    )

    client_match = re.search(
        r"client\s*:\s*(.*)",
        text,
        re.IGNORECASE
    )

    if employer_match and client_match:

        return (
            normalize(employer_match.group(1)),
            normalize(client_match.group(1))
        )

    # -----------------------------------
    # Company (Client: XYZ)
    # -----------------------------------

    m = re.search(
        r"^(.*?)\(\s*client\s*:\s*(.*?)\)$",
        text,
        re.IGNORECASE
    )

    if m:

        return (
            normalize(m.group(1)),
            normalize(m.group(2))
        )

    # -----------------------------------
    # Slash
    # -----------------------------------

    if "/" in text:

        left, right = text.split("/", 1)

        return (
            normalize(left),
            normalize(right)
        )

    # -----------------------------------
    # Pipe
    # -----------------------------------

    if "|" in text:

        left, right = text.split("|", 1)

        return (
            normalize(left),
            normalize(right)
        )

    # -----------------------------------
    # Default
    # -----------------------------------

    return "", text


# -------------------------------------------------------
# Client / Location
# -------------------------------------------------------


def split_client_location(text):
    """
    Splits:

    ABC Corp, Dallas TX

    ABC Corp - Remote

    ABC Corp | Chicago IL

    ABC Corp (Hybrid)

    into

    client
    location
    """

    text = normalize(text)

    if not text:

        return "", ""

    # -------------------------
    # Parentheses
    # -------------------------

    m = re.search(r"\((.*?)\)$", text)

    if m:

        client = normalize(
            text[:m.start()]
        )

        location = normalize(
            m.group(1)
        )

        return client, location

    # -------------------------
    # Pipe
    # -------------------------

    if "|" in text:

        left, right = text.split("|", 1)

        return normalize(left), normalize(right)

    # -------------------------
    # Dash
    # -------------------------

    if " - " in text:

        left, right = text.rsplit(" - ", 1)

        return normalize(left), normalize(right)

    # -------------------------
    # Comma
    # -------------------------

    parts = [x.strip() for x in text.split(",")]

    if len(parts) >= 2:

        client = parts[0]

        location = ", ".join(parts[1:])

        return client, location

    # -------------------------
    # Remote / Hybrid / Onsite
    # -------------------------

    lower = text.lower()

    for keyword in LOCATION_KEYWORDS:

        if lower.endswith(keyword):

            idx = lower.rfind(keyword)

            client = normalize(text[:idx])

            location = text[idx:]

            return client, location

    return text, ""


# -------------------------------------------------------
# Role Heuristic
# -------------------------------------------------------

ROLE_WORDS = {

    "developer",
    "software developer",
    "software engineer",
    "engineer",
    "technical lead",
    "team lead",
    "lead developer",
    "lead engineer",
    "architect",
    "solution architect",
    "analyst",
    "business analyst",
    "systems analyst",
    "data analyst",
    "data engineer",
    "consultant",
    "manager",
    "project manager",
    "delivery manager",
    "administrator",
    "system administrator",
    "specialist",
    "support analyst",
    "support engineer",
    "tester",
    "test engineer",
    "qa engineer",
    "qa analyst",
    "scrum master",
    "programmer",
    "mainframe developer"

}


def looks_like_role(text):

    text = clean(text)

    lower = text.lower()

    if lower.startswith("role:"):

        return True

    if lower.startswith("role"):

        return True

    for role in ROLE_WORDS:

        if role in lower:

            return True

    return False

# -------------------------------------------------------
# Base Pattern
# -------------------------------------------------------

class HeaderPattern(ABC):

    # Every derived class MUST override this
    name = "BASE"

    # ---------------------------------------------------

    def empty_result(self):

        result = PatternMatch()

        result.pattern = self.name

        return result

    # ---------------------------------------------------

    def success(
        self,
        confidence,
        header_type,
        employer="",
        client="",
        location="",
        role="",
        duration="",
        project="",
        raw_lines=None,
        matched_fields=None,
    ):

        result = PatternMatch()

        result.pattern = self.name

        result.confidence = confidence

        result.header_type = header_type

        result.employer = employer

        result.client = client

        result.location = location

        result.role = role

        result.duration = duration

        result.project = project

        result.raw_lines = raw_lines or []

        result.matched_fields = matched_fields or []

        return result

    # ---------------------------------------------------

    def fail(
        self,
        reason=""
    ):

        result = self.empty_result()

        if reason:

            result.errors.append(reason)

        return result

    # ---------------------------------------------------

    def prepare(self, lines):

        cleaned = []

        for line in lines:

            line = normalize(line)

            if line:

                cleaned.append(line)

        return cleaned

    # ---------------------------------------------------

    @abstractmethod
    def match(
        self,
        lines,
        inside_employment=False
    ):
        pass

# -------------------------------------------------------
# Header Confidence
# -------------------------------------------------------

def calculate_confidence(

    client="",
    role="",
    duration="",
    employer="",
    location=""

):

    score = 0

    if client:
        score += 30

    if role:
        score += 30

    if duration:
        score += 30

    if employer:
        score += 5

    if location:
        score += 5

    return score

# -------------------------------------------------------
# Universal Employment Pattern
# -------------------------------------------------------

# -------------------------------------------------------
# Universal Employment Pattern
# -------------------------------------------------------

class EmploymentPattern(HeaderPattern):

    name = "EMPLOYMENT"

    def match(
        self,
        lines,
        inside_employment=False
    ):

        result = self.empty_result()

        lines = self.prepare(lines)

        if not lines:
            return result

        # -----------------------------------
        # Scan every line in the header window
        # -----------------------------------

        for line in lines:

            lower = line.lower()

            # -----------------------------------
            # Duration
            # -----------------------------------

            duration, remaining = extract_duration(line)

            if duration and not result.duration:

                result.duration = duration

                if remaining:

                    employer, client = split_employer_client(remaining)

                    if employer:
                        result.employer = employer

                    if client:
                        result.client = client

                continue

            # -----------------------------------
            # Explicit Client
            # -----------------------------------

            if lower.startswith("client:"):

                value = line.split(":", 1)[1].strip()

                if value:
                    result.client = value

                continue

            # -----------------------------------
            # Explicit Employer
            # -----------------------------------

            if lower.startswith("employer:"):

                value = line.split(":", 1)[1].strip()

                if value:
                    result.employer = value

                continue

            # -----------------------------------
            # Explicit Role
            # -----------------------------------

            if lower.startswith("role:"):

                value = line.split(":", 1)[1].strip()

                if value:
                    result.role = value

                continue

            # -----------------------------------
            # Project
            # -----------------------------------

            if lower.startswith("project:"):

                value = line.split(":", 1)[1].strip()

                if value:
                    result.project = value

                continue

            # -----------------------------------
            # Standalone Role
            # -----------------------------------

            if not result.role and looks_like_role(line):

                result.role = line

                continue

            # -----------------------------------
            # Standalone Client / Employer
            # -----------------------------------

            if (
                not looks_like_role(line)
                and not result.client
            ):

                employer, client = split_employer_client(line)

                if employer and not result.employer:
                    result.employer = employer

                if client and not result.client:
                    result.client = client

        # -----------------------------------
        # Split Client / Location
        # -----------------------------------

        if result.client:

            result.client, result.location = split_client_location(
                result.client
            )

        # -----------------------------------
        # Confidence
        # -----------------------------------

        result.confidence = calculate_confidence(

            client=result.client,
            employer=result.employer,
            role=result.role,
            duration=result.duration,
            location=result.location

        )

        # -----------------------------------
        # Final Decision
        # -----------------------------------

        if (
            result.duration
            and result.role
            and (
                result.client
                or result.employer
            )
        ):

            result.header_type = (
                "PROJECT"
                if inside_employment
                else "EMPLOYMENT"
            )

            result.raw_lines = lines

        return result
    
# -------------------------------------------------------
# Pattern Registry
# -------------------------------------------------------

PATTERNS = [

    EmploymentPattern()

]
