import re

# ------------------------------------------------------
# Section Headers
# ------------------------------------------------------

SUMMARY_HEADERS = {
    "summary",
    "professional summary",
    "career summary",
    "objective",
    "profile",
    "professional profile",
    "executive summary",
}

SKILL_HEADERS = {
    "skills",
    "technical skills",
    "technical expertise",
    "technology",
    "technology stack",
    "core competencies",
}

EDUCATION_HEADERS = {
    "education",
    "academic qualifications",
    "academic background",
}

CERTIFICATION_HEADERS = {
    "certifications",
    "certification",
    "licenses",
    "professional certifications",
}

EXPERIENCE_HEADERS = {
    "experience",
    "professional experience",
    "work experience",
    "employment history",
    "career history",
}

# ------------------------------------------------------
# Environment Headers
# ------------------------------------------------------

ENVIRONMENT_HEADERS = {
    "environment",
    "technical environment",
    "tools",
    "technology used",
    "technology stack",
}

# ------------------------------------------------------
# Month Pattern
# ------------------------------------------------------

MONTH_PATTERN = (
    r"\b(?:"
    r"jan(?:uary)?|"
    r"feb(?:ruary)?|"
    r"mar(?:ch)?|"
    r"apr(?:il)?|"
    r"may|"
    r"jun(?:e)?|"
    r"jul(?:y)?|"
    r"aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|"
    r"oct(?:ober)?|"
    r"nov(?:ember)?|"
    r"dec(?:ember)?"
    r")\b"
)

# ------------------------------------------------------
# Date Range Pattern
# Examples:
# Sep 2016 - Present
# September 2016 – March 2019
# Jan 2020 to Current
# ------------------------------------------------------

DATE_PATTERN = re.compile(

    rf"""
    (
        {MONTH_PATTERN}
        \s+
        (?:19|20)\d{{2}}
    )

    \s*

    (?:-|–|to)?

    \s*

    (
        {MONTH_PATTERN}
        \s+
        (?:19|20)\d{{2}}

        |

        Present

        |

        Current

        |

        Till\s+Date

    )?
    """,

    re.IGNORECASE | re.VERBOSE

)

YEAR_PATTERN = re.compile(
    r"(19\d{2}|20\d{2})"
)

# ------------------------------------------------------
# Month Normalization
# ------------------------------------------------------

MONTH_MAP = {

    "january": "Jan",
    "jan": "Jan",

    "february": "Feb",
    "feb": "Feb",

    "march": "Mar",
    "mar": "Mar",

    "april": "Apr",
    "apr": "Apr",

    "may": "May",

    "june": "Jun",
    "jun": "Jun",

    "july": "Jul",
    "jul": "Jul",

    "august": "Aug",
    "aug": "Aug",

    "september": "Sep",
    "sept": "Sep",
    "sep": "Sep",

    "october": "Oct",
    "oct": "Oct",

    "november": "Nov",
    "nov": "Nov",

    "december": "Dec",
    "dec": "Dec",

}

# ------------------------------------------------------
# Generic Role Keywords
#
# Used ONLY to identify whether a line
# looks like a Job Title.
#
# Never use for company detection.
# ------------------------------------------------------

ROLE_KEYWORDS = {

    "analyst",
    "business analyst",
    "systems analyst",

    "developer",
    "software developer",

    "engineer",
    "software engineer",
    "data engineer",

    "data analyst",

    "architect",
    "solution architect",
    "technical architect",

    "consultant",

    "lead",
    "technical lead",
    "team lead",

    "manager",
    "project manager",
    "program manager",
    "product manager",

    "administrator",

    "designer",

    "tester",
    "qa",
    "qa analyst",
    "qa engineer",

    "scrum master",

    "product owner",

    "coordinator",

    "specialist",

    "associate",

    "director",

    "vice president",
    "vp",

    "intern",

    "graduate assistant",

    "research assistant",

    "assistant"

}

# ------------------------------------------------------
# Generic Location Keywords
# ------------------------------------------------------

LOCATION_KEYWORDS = {

    "remote",

    "hybrid",

    "onsite",

    "wfh",

    "work from home"

}

# ------------------------------------------------------
# Bullet Characters
# ------------------------------------------------------

BULLETS = (
    "•",
    "-",
    "*",
    "▪",
    "◦",
    "►",
    "●",
)

# ------------------------------------------------------
# Generic Prefixes
#
# These are optional hints only.
# Never required for parsing.
# ------------------------------------------------------

CLIENT_PREFIXES = (
    "client",
    "customer",
    "end client",
)

PROJECT_PREFIXES = (
    "project",
    "application",
    "assignment",
    "initiative",
)
