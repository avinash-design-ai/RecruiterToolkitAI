import re
from dataclasses import dataclass


# -------------------------------------------------------
# Education Record
# -------------------------------------------------------

@dataclass
class EducationRecord:

    degree: str = ""
    specialization: str = ""
    university: str = ""
    location: str = ""
    year: str = ""


# -------------------------------------------------------
# Degree Keywords
# -------------------------------------------------------

DEGREE_KEYWORDS = [

    "phd",
    "doctorate",
    "doctoral",

    "master",
    "masters",
    "m.s",
    "ms",
    "m.sc",
    "msc",
    "m.tech",
    "mtech",
    "m.e",
    "me",
    "mba",
    "mca",
    "m.com",
    "ma",

    "bachelor",
    "bachelors",
    "b.s",
    "bs",
    "b.sc",
    "bsc",
    "b.tech",
    "btech",
    "be",
    "b.e",
    "bca",
    "b.com",
    "ba",

    "post graduate diploma",
    "pg diploma",
    "graduate diploma",
    "advanced diploma",
    "diploma",

    "associate degree"

]


# -------------------------------------------------------
# University Keywords
# -------------------------------------------------------

UNIVERSITY_WORDS = [

    "university",
    "college",
    "institute",
    "school",
    "academy",
    "polytechnic"

]


YEAR_REGEX = r"(19|20)\d{2}"


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def clean(text):

    return " ".join(text.split()).strip()


def contains_degree(text):

    value = clean(text).lower()

    for word in DEGREE_KEYWORDS:

        if word in value:

            return True

    return False


def contains_university(text):

    value = clean(text).lower()

    for word in UNIVERSITY_WORDS:

        if word in value:

            return True

    return False


def extract_year(text):

    match = re.search(YEAR_REGEX, text)

    if match:

        return match.group()

    return ""

# -------------------------------------------------------
# Build Education Records
# -------------------------------------------------------

def build_records(sections):

    records = []

    current = None

    for block in sections.education:

        text = clean(block.text)

        if not text:

            continue

        # -----------------------------------
        # New Degree Found
        # -----------------------------------

        if contains_degree(text):

            if current:

                records.append(current)

            current = EducationRecord()

            current.degree = text

            continue

        # Ignore anything before first degree
        if current is None:

            continue

        # -----------------------------------
        # University
        # -----------------------------------

        if contains_university(text):

            if not current.university:

                current.university = text

                continue

        # -----------------------------------
        # Year
        # -----------------------------------

        year = extract_year(text)

        if year:

            if not current.year:

                current.year = year

            continue

        # -----------------------------------
        # Everything else
        # -----------------------------------

        if not current.specialization:

            current.specialization = text

        elif not current.location:

            current.location = text

        else:

            current.location += " " + text

    if current:

        records.append(current)

    return records

# -------------------------------------------------------
# Improve Education Records
# -------------------------------------------------------

LOCATION_WORDS = [

    "usa",
    "india",
    "canada",
    "uk",
    "united states",
    "united kingdom",
    "australia",
    "hyderabad",
    "mumbai",
    "bangalore",
    "chennai",
    "delhi",
    "new york",
    "texas",
    "california"

]


def improve_records(records):

    for record in records:

        # -----------------------------------
        # Degree contains specialization
        # -----------------------------------

        if " in " in record.degree.lower():

            continue

        if record.specialization:

            degree_lower = record.degree.lower()

            if (

                "master" in degree_lower

                or "bachelor" in degree_lower

                or "diploma" in degree_lower

                or "phd" in degree_lower

            ):

                record.degree = (

                    record.degree

                    + " in "

                    + record.specialization

                )

                record.specialization = ""

        # -----------------------------------
        # Guess Location
        # -----------------------------------

        if record.location:

            continue

        if not record.specialization:

            continue

        value = record.specialization.lower()

        if any(word in value for word in LOCATION_WORDS):

            record.location = record.specialization

            record.specialization = ""

    return records

# -------------------------------------------------------
# Main Parser
# -------------------------------------------------------

def parse_education(
    blocks,
    sections
):

    # No education section
    if not sections.education:

        return []

    # Step 1
    records = build_records(sections)

    # Step 2
    records = improve_records(records)

    # Step 3
    education = []

    seen = set()

    for record in records:

        parts = []

        if record.degree:

            parts.append(clean(record.degree))

        if record.university:

            parts.append(clean(record.university))

        if record.location:

            parts.append(clean(record.location))

        if record.year:

            parts.append(clean(record.year))

        line = " | ".join(parts)

        if not line:

            continue

        key = line.lower()

        if key in seen:

            continue

        seen.add(key)

        education.append(line)

    return education
