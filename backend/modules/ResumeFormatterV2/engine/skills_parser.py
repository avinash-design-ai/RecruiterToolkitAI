import re
from collections import OrderedDict


# -------------------------------------------------------
# Known Categories
# -------------------------------------------------------

KNOWN_CATEGORIES = {

    "programming languages",
    "languages",
    "database",
    "databases",
    "cloud",
    "frameworks",
    "framework",
    "web technologies",
    "technologies",
    "technology",
    "technical skills",
    "skills",
    "tools",
    "operating systems",
    "operating system",
    "platforms",
    "etl",
    "etl tools",
    "big data",
    "messaging",
    "middleware",
    "reporting",
    "bi tools",
    "devops",
    "testing",
    "methodologies",
    "security",
    "analytics",
    "data warehouse",
    "data warehousing",
    "scripting",
    "version control"

}


# -------------------------------------------------------
# Environment Headings
# -------------------------------------------------------

ENVIRONMENT_HEADERS = {

    "environment",
    "technical environment",
    "technology stack",
    "technology",
    "tools"

}


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def clean(text):

    return " ".join(str(text).split()).strip()


def normalize(text):

    return clean(text).lower()


def add_skill(

    skills,

    category,

    skill

):

    category = clean(category)

    skill = clean(skill)

    if not skill:

        return

    if not category:

        category = "Technical Skills"

    if category not in skills:

        skills[category] = []

    existing = {

        value.lower()

        for value in skills[category]

    }

    if skill.lower() not in existing:

        skills[category].append(skill)


def split_skills(text):

    values = re.split(

        r"[|,/;]+",

        text

    )

    return [

        clean(item)

        for item in values

        if clean(item)

    ]


def looks_like_category(text):

    value = normalize(text)

    if len(value) > 40:

        return False

    value = value.replace(":", "")

    return value in KNOWN_CATEGORIES


def is_environment_heading(text):

    value = normalize(text)

    value = value.replace(":", "")

    return value in ENVIRONMENT_HEADERS


def looks_like_skill_list(text):

    value = clean(text)

    if not value:

        return False

    if "," in value:

        return True

    if "|" in value:

        return True

    if ";" in value:

        return True

    return False

def looks_like_skill(text):

    text = clean(text)

    if not text:

        return False

    words = text.split()

    # Too long = probably responsibility
    if len(words) > 4:

        return False

    lower = text.lower()

    # Ignore dates
    if re.search(r"(19|20)\d{2}", lower):

        return False

    # Ignore common resume words
    BAD_WORDS = {

        "client",
        "project",
        "role",
        "responsibilities",
        "responsibility",
        "location",
        "company",
        "employer",
        "duration",
        "present"

    }

    if any(word in lower for word in BAD_WORDS):

        return False

    return True
# -------------------------------------------------------
# Extract Explicit Skills Section
# -------------------------------------------------------

def extract_explicit_skills(

    sections,

    skills

):

    if not sections.skills:

        return False

    current_category = "Technical Skills"

    found = False

    for block in sections.skills:

        text = clean(block.text)

        if not text:

            continue

        # ----------------------------
        # Category
        # ----------------------------

        if looks_like_category(text):

            current_category = text.replace(":", "")

            continue

        # ----------------------------
        # Comma / Pipe Lists
        # ----------------------------

        if looks_like_skill_list(text):

            for skill in split_skills(text):

                add_skill(

                    skills,

                    current_category,

                    skill

                )

                found = True

            continue

        # ----------------------------
        # Single Skill
        # ----------------------------

        add_skill(

            skills,

            current_category,

            text

        )

        found = True

    return found

# -------------------------------------------------------
# Extract Environment
# -------------------------------------------------------

def extract_environment(

    jobs,

    skills

):

    found = False

    # Experience parser may not have run yet
    if not jobs:

        return False

    categorized = len(skills) > 0

    for job in jobs:

        if not getattr(job, "environment", None):

            continue

        category = "Additional Technologies"

        if not categorized:

            category = "Technical Skills"

        for line in job.environment:

            line = clean(line)

            if not line:

                continue

            if is_environment_heading(line):

                continue

            if looks_like_skill_list(line):

                for item in split_skills(line):

                    add_skill(

                        skills,

                        category,

                        item

                    )

                    found = True

            else:

                if looks_like_skill(line):

                    add_skill(

                        skills,

                        category,

                        line

                    )

                    found = True

    return found


# -------------------------------------------------------
# Extract Uncategorized Skill Lists
# -------------------------------------------------------

def extract_skill_lists(

    blocks,

    skills

):

    category = "Technical Skills"

    found = False

    for block in blocks:

        text = clean(block.text)

        if not text:

            continue

        # Ignore very long sentences
        if len(text.split()) > 12:

            continue

        # Skip headings
        if looks_like_category(text):

            continue

        if is_environment_heading(text):

            continue

        # Comma / Pipe / Slash list
        if looks_like_skill_list(text):

            for item in split_skills(text):

                add_skill(

                    skills,

                    category,

                    item

                )

                found = True

            continue

        # One-word technologies
        if looks_like_skill(text):

                add_skill(

                    skills,

                    category,

                    text

                )

                found = True

    return found

# -------------------------------------------------------
# Main Parser
# -------------------------------------------------------

def parse_skills(

    blocks,

    sections,

    jobs=None

):

    skills = OrderedDict()

    # -----------------------------------
    # Priority 1
    # Explicit Skills Section
    # -----------------------------------

    extract_explicit_skills(

        sections,

        skills

    )

    # -----------------------------------
    # Priority 2
    # Environment
    # -----------------------------------

    extract_environment(

        jobs,

        skills

    )

    # -----------------------------------
    # Priority 3
    # Uncategorized Skill Lists
    # -----------------------------------

    if not skills:

        extract_skill_lists(

            blocks,

            skills

        )

    # -----------------------------------
    # Cleanup
    # -----------------------------------

    cleaned = OrderedDict()

    for category, values in skills.items():

        unique = []

        seen = set()

        for value in values:

            key = normalize(value)

            if not key:

                continue

            if key in seen:

                continue

            seen.add(key)

            unique.append(clean(value))

        if unique:

            cleaned[category] = unique

    return cleaned
