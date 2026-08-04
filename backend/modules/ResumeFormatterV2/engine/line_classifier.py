from dataclasses import dataclass
from enum import Enum

from engine.rules import (
    DATE_PATTERN,
    BULLETS,
    ENVIRONMENT_HEADERS,
    CLIENT_PREFIXES,
    PROJECT_PREFIXES
)


# ----------------------------------------------------
# Line Types
# ----------------------------------------------------

class LineType(Enum):

    UNKNOWN = 0

    DATE = 1

    ROLE = 2

    COMPANY = 3

    PROJECT = 4

    RESPONSIBILITY = 5

    ENVIRONMENT = 6

    CLIENT = 7

    LOCATION = 8


# ----------------------------------------------------
# Result
# ----------------------------------------------------

@dataclass

class LineClassification:

    type: LineType

    confidence: int


# ----------------------------------------------------
# Helpers
# ----------------------------------------------------

def clean(text):

    return " ".join(text.split()).strip()


def word_count(text):

    return len(text.split())


def is_title_case(text):

    words = text.split()

    if not words:

        return False

    good = 0

    for w in words:

        if len(w) <= 2:
            continue

        if w[0].isupper():

            good += 1

    return good >= max(1, len(words) // 2)


# ----------------------------------------------------
# Classifier
# ----------------------------------------------------

def classify(line):

    line = clean(line)

    lower = line.lower()

    if not line:

        return LineClassification(
            LineType.UNKNOWN,
            0
        )

    # ------------------------
    # Date
    # ------------------------

    if DATE_PATTERN.search(line):

        return LineClassification(
            LineType.DATE,
            100
        )

    # ------------------------
    # Bullet
    # ------------------------

    if line.startswith(BULLETS):

        return LineClassification(
            LineType.RESPONSIBILITY,
            100
        )

    # ------------------------
    # Environment
    # ------------------------

    if lower in ENVIRONMENT_HEADERS:

        return LineClassification(
            LineType.ENVIRONMENT,
            100
        )

    if lower.startswith("environment"):

        return LineClassification(
            LineType.ENVIRONMENT,
            95
        )

    # ------------------------
    # Client
    # ------------------------

    for p in CLIENT_PREFIXES:

        if lower.startswith(p):

            return LineClassification(
                LineType.CLIENT,
                95
            )

    # ------------------------
    # Project
    # ------------------------

    for p in PROJECT_PREFIXES:

        if lower.startswith(p):

            return LineClassification(
                LineType.PROJECT,
                95
            )

    # ------------------------
    # Possible Header
    # ------------------------

    score = 0

    if word_count(line) <= 8:

        score += 2

    if len(line) < 70:

        score += 2

    if is_title_case(line):

        score += 3

    if ":" not in line:

        score += 1

    if score >= 7:

        return LineClassification(
            LineType.UNKNOWN,
            score * 10
        )

    return LineClassification(
        LineType.UNKNOWN,
        10
    )
