import re

# ----------------------------------------------------
# Common Resume Headings
# ----------------------------------------------------

HEADINGS = {

    "summary": [
        "summary",
        "professional summary",
        "career summary",
        "executive summary",
        "profile",
        "professional profile",
        "objective"
    ],

    "skills": [
        "skills",
        "technical skills",
        "technical expertise",
        "core competencies",
        "technology",
        "technology stack",
        "technical proficiency",
        "skill set"
    ],

    "experience": [
        "professional experience",
        "experience",
        "work experience",
        "employment history",
        "career history"
    ],

    "education": [
        "education",
        "academic qualifications",
        "academic background"
    ],

    "certifications": [
        "certifications",
        "licenses",
        "professional certifications"
    ]
}


# ----------------------------------------------------
# Date Patterns
# ----------------------------------------------------

MONTHS = (
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec"
)

DATE_PATTERN = re.compile(
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    r".*?(present|current|20\d\d|19\d\d)",
    re.IGNORECASE
)


# ----------------------------------------------------
# Normalize
# ----------------------------------------------------

def normalize(text):

    return re.sub(
        r"[^a-z0-9 ]",
        "",
        text.lower()
    ).strip()


# ----------------------------------------------------
# Heading
# ----------------------------------------------------

def is_heading(text):

    value = normalize(text)

    for items in HEADINGS.values():

        if value in items:
            return True

    return False


def heading_name(text):

    value = normalize(text)

    for section, items in HEADINGS.items():

        if value in items:
            return section

    return None


# ----------------------------------------------------
# Bullet
# ----------------------------------------------------

def is_bullet(text):

    text = text.strip()

    return text.startswith((
        "•",
        "-",
        "*",
        "▪",
        "◦"
    ))


# ----------------------------------------------------
# Date
# ----------------------------------------------------

def is_date(text):

    return bool(
        DATE_PATTERN.search(text)
    )


# ----------------------------------------------------
# Email
# ----------------------------------------------------

def is_email(text):

    return bool(
        re.search(
            r'[\w\.-]+@[\w\.-]+\.\w+',
            text
        )
    )


# ----------------------------------------------------
# Phone
# ----------------------------------------------------

def is_phone(text):

    return bool(
        re.search(
            r'(\+?\d[\d\s().-]{8,})',
            text
        )
    )


# ----------------------------------------------------
# LinkedIn
# ----------------------------------------------------

def is_linkedin(text):

    return "linkedin.com" in text.lower()


# ----------------------------------------------------
# Company
# ----------------------------------------------------

COMPANY_WORDS = [

    "inc",

    "corp",

    "corporation",

    "llc",

    "limited",

    "ltd",

    "technologies",

    "solutions",

    "systems",

    "consulting",

    "services",

    "bank",

    "insurance",

    "health",

    "hospital",

    "client"

]


def is_company(text):

    value = text.lower()

    for word in COMPANY_WORDS:

        if word in value:
            return True

    return False


# ----------------------------------------------------
# Role
# ----------------------------------------------------

ROLE_WORDS = [

    "analyst",

    "developer",

    "engineer",

    "architect",

    "consultant",

    "manager",

    "lead",

    "administrator",

    "scientist",

    "specialist",

    "director",

    "coordinator"

]


def is_role(text):

    value = text.lower()

    for word in ROLE_WORDS:

        if word in value:
            return True

    return False
