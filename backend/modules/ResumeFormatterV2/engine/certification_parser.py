import re
from dataclasses import dataclass


@dataclass
class CertificationRecord:

    certification: str = ""
    organization: str = ""
    year: str = ""


YEAR_REGEX = r"(19|20)\d{2}"


CERTIFICATION_WORDS = [

    "certified",
    "certification",
    "certificate",
    "aws",
    "azure",
    "gcp",
    "oracle",
    "scrum",
    "scrum master",
    "scrum product owner",
    "pmp",
    "safe",
    "csm",
    "cspo",
    "itil",
    "comptia",
    "cissp",
    "ccna",
    "ccnp",
    "salesforce",
    "sap",
    "informatica",
    "databricks",
    "snowpro",
    "kubernetes",
    "terraform"

]


ORG_WORDS = [

    "amazon",
    "aws",
    "microsoft",
    "oracle",
    "google",
    "scrum alliance",
    "pmi",
    "isc2",
    "comptia",
    "salesforce",
    "sap",
    "cisco",
    "vmware",
    "informatica",
    "databricks"

]


def clean(text):

    return " ".join(text.split()).strip()


def extract_year(text):

    match = re.search(YEAR_REGEX, text)

    if match:

        return match.group()

    return ""


def contains_certification(text):

    value = clean(text).lower()

    return any(word in value for word in CERTIFICATION_WORDS)


def contains_organization(text):

    value = clean(text).lower()

    return any(word in value for word in ORG_WORDS)


def parse_certifications(
    blocks,
    sections
):

    # -----------------------------------
    # Source
    # -----------------------------------

    if sections.certifications:

        source = sections.certifications

    else:

        source = sections.education

    certifications = []

    seen = set()

    current = None

    for block in source:

        text = clean(block.text)

        if not text:

            continue

        # Ignore education

        if (

            "bachelor" in text.lower()

            or "master" in text.lower()

            or "diploma" in text.lower()

            or "phd" in text.lower()

            or "b.tech" in text.lower()

            or "m.tech" in text.lower()

        ):

            if current:

                certifications.append(current)

                current = None

            continue

        # New Certification

        if contains_certification(text):

            if current:

                certifications.append(current)

            current = CertificationRecord()

            current.certification = text

            continue

        if current is None:

            continue

        # Organization

        if contains_organization(text):

            if not current.organization:

                current.organization = text

                continue

        # Year

        year = extract_year(text)

        if year:

            current.year = year

            continue

        # Append remaining text

        current.certification += " " + text

    if current:

        certifications.append(current)

    result = []

    for cert in certifications:

        parts = []

        if cert.certification:

            parts.append(cert.certification)

        if cert.organization:

            parts.append(cert.organization)

        if cert.year:

            parts.append(cert.year)

        line = " | ".join(parts)

        key = line.lower()

        if key in seen:

            continue

        seen.add(key)

        result.append(line)

    return result
