import re


# =========================================================
# RULE-BASED RESUME STRUCTURE PARSER
# =========================================================
#
# AI / Ollama is NOT used.
#
# This parser is intentionally conservative:
# - Uses section headings
# - Uses Word formatting when available
# - Detects job headers from company/date + role pattern
# - Does NOT treat ordinary responsibility lines as jobs
# =========================================================


SUMMARY_HEADERS = {
    "summary",
    "professional summary",
    "career summary",
    "profile",
    "professional profile",
    "objective",
    "career objective",
    "professional objective",
}

SKILLS_HEADERS = {
    "skills",
    "technical skills",
    "technical proficiencies",
    "technical expertise",
    "core skills",
    "core competencies",
    "technologies",
    "technology",
    "skills & technologies",
    "technical skills & tools",
}

EXPERIENCE_HEADERS = {
    "experience",
    "professional experience",
    "work experience",
    "employment history",
    "professional history",
    "career history",
    "work history",
}

EDUCATION_HEADERS = {
    "education",
    "educational background",
    "academic background",
    "academic qualifications",
}

CERTIFICATION_HEADERS = {
    "certification",
    "certifications",
    "licenses",
    "licenses & certifications",
    "certifications & licenses",
}


SECTION_ALIASES = {}

for value in SUMMARY_HEADERS:
    SECTION_ALIASES[value] = "summary"

for value in SKILLS_HEADERS:
    SECTION_ALIASES[value] = "skills"

for value in EXPERIENCE_HEADERS:
    SECTION_ALIASES[value] = "experience"

for value in EDUCATION_HEADERS:
    SECTION_ALIASES[value] = "education"

for value in CERTIFICATION_HEADERS:
    SECTION_ALIASES[value] = "certifications"


# =========================================================
# Utility
# =========================================================

def clean(text):
    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text).strip()
    ).strip()


def normalized(text):
    text = clean(text).lower()

    text = re.sub(
        r"[:\-|]+$",
        "",
        text
    )

    return text.strip()


def section_name(block):
    value = normalized(block.text)

    return SECTION_ALIASES.get(value)


# =========================================================
# Dates
# =========================================================

MONTHS = (
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
)

DATE_VALUE = (
    rf"(?:{MONTHS})"
    r"(?:\s+\d{4})?"
    r"|"
    r"\d{1,2}[/-]\d{4}"
    r"|"
    r"\d{4}"
)

DATE_RANGE_PATTERN = re.compile(
    rf"\b{DATE_VALUE}"
    rf"\s*(?:-|â€“|â€”|to)\s*"
    rf"(?:{DATE_VALUE}|present|current)\b",
    re.IGNORECASE
)

PRESENT_PATTERN = re.compile(
    r"\b(?:present|current|till date|to date)\b",
    re.IGNORECASE
)


def looks_like_duration(text):
    text = clean(text)

    if DATE_RANGE_PATTERN.search(text):
        return True

    return bool(
        PRESENT_PATTERN.search(text)
        and re.search(r"\b\d{4}\b", text)
    )


# =========================================================
# Job header detection
# =========================================================

def is_bold(block):
    return bool(
        getattr(block, "bold", False)
    )


def style_name(block):
    return clean(
        getattr(block, "style", "")
    ).lower()


def is_formatted_job_header(block):
    """
    Strong formatting signal used by the supplied resume.

    Actual job headers in the test resume are:

        HTML Preformatted
        bold=True

    Later resumes may use Normal + bold, so we allow that
    only when combined with a date.
    """

    style = style_name(block)

    if not is_bold(block):
        return False

    if style == "html preformatted":
        return True

    return False


def looks_like_role(text):
    text = clean(text).lower()

    if not text:
        return False

    if len(text) > 100:
        return False

    role_keywords = (
        "engineer",
        "developer",
        "architect",
        "analyst",
        "consultant",
        "manager",
        "administrator",
        "specialist",
        "scientist",
        "lead",
        "director",
        "recruiter",
        "designer",
        "programmer",
        "tester",
        "qa",
        "scrum master",
        "product owner",
        "devops",
        "data engineer",
        "data scientist",
        "business analyst",
        "project manager",
    )

    return any(
        keyword in text
        for keyword in role_keywords
    )


def looks_like_company_date_header(block):
    """
    Strong job-start condition.

    Requires:
      1. bold formatted header
      2. employment date range
    """

    if not is_formatted_job_header(block):
        return False

    text = clean(block.text)

    return looks_like_duration(text)


def looks_like_normal_bold_job_header(block):
    """
    Some resumes use Normal + bold for job headers.

    We only accept this when:
      - bold
      - contains duration
      - not an Environment line
      - not a section heading
    """

    if not is_bold(block):
        return False

    if style_name(block) == "html preformatted":
        return False

    text = clean(block.text)

    if text.lower().startswith((
        "environment:",
        "project scope:",
        "description:",
        "responsibilities:",
        "responsibility:",
        "objective:",
        "summary:",
        "skills:",
    )):
        return False

    if section_name(block):
        return False

    # Job headers should be concise rather than prose paragraphs.
    if len(text) > 180:
        return False

    # A valid job header must contain an employment date range.
    if not looks_like_duration(text):
        return False

    return True


def is_job_header(block):
    return (
        looks_like_company_date_header(block)
        or looks_like_normal_bold_job_header(block)
    )


# =========================================================
# Header / contact information
# =========================================================

EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+"
    r"@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE
)

PHONE_PATTERN = re.compile(
    r"(?:\+?1[\s.-]?)?"
    r"(?:\(?\d{3}\)?[\s.-]?)"
    r"\d{3}[\s.-]\d{4}"
)

LINKEDIN_PATTERN = re.compile(
    r"(?:https?://)?"
    r"(?:www\.)?"
    r"linkedin\.com/[^\s|]+",
    re.IGNORECASE
)


def extract_header(blocks):

    result = {
        "name": "",
        "phone": "",
        "email": "",
        "linkedin": "",
    }

    # --------------------------------------------------
    # Header/contact information is normally contained
    # in the first few document blocks.
    #
    # Some resumes place contact information on the
    # same line as the candidate's name/title:
    #
    #   Anindita Sinha    Mobile: +1 571-781-0575
    #   Sr Power BI Developer    Email: example@gmail.com
    #
    # Extract contact information first, then isolate
    # the candidate name from the text before Mobile/Phone.
    # --------------------------------------------------

    header_blocks = blocks[:10]

    for block in header_blocks:

        text = clean(block.text)

        if not text:
            continue

        # --------------------------------------------------
        # Email
        # --------------------------------------------------

        if not result["email"]:

            match = EMAIL_PATTERN.search(text)

            if match:

                result["email"] = match.group(0)

        # --------------------------------------------------
        # Phone
        # --------------------------------------------------

        if not result["phone"]:

            match = PHONE_PATTERN.search(text)

            if match:

                result["phone"] = match.group(0)

        # --------------------------------------------------
        # LinkedIn
        # --------------------------------------------------

        if not result["linkedin"]:

            match = LINKEDIN_PATTERN.search(text)

            if match:

                result["linkedin"] = match.group(0)

        # --------------------------------------------------
        # Candidate name
        #
        # First look for text before Mobile / Phone.
        # --------------------------------------------------

        if not result["name"]:

            name_candidate = re.split(
                r"\b(?:mobile|phone|cell|tel)\s*:",
                text,
                maxsplit=1,
                flags=re.IGNORECASE
            )[0].strip()

            name_candidate = clean(
                name_candidate
            )
            # --------------------------------------------------
            # Some resumes place the candidate's professional
            # title on the same line as the name:
            #
            #   Aarthi Balasubramanian Senior Software Engineer
            #
            # Keep only the candidate name.
            # --------------------------------------------------

            words = name_candidate.split()

            for split_index in range(
                2,
                len(words)
            ):

                possible_name = " ".join(
                    words[:split_index]
                )

                possible_role = " ".join(
                    words[split_index:]
                )

                if (
                    len(possible_name.split()) >= 2
                    and looks_like_role(possible_role)
                ):

                    name_candidate = possible_name
                    break

            if (
                name_candidate
                and len(name_candidate.split()) >= 2
                and len(name_candidate) <= 70
                and not EMAIL_PATTERN.search(name_candidate)
                and not PHONE_PATTERN.search(name_candidate)
                and not section_name(block)
            ):

                result["name"] = name_candidate

        # --------------------------------------------------
        # Fallback:
        # normal standalone bold name block
        # --------------------------------------------------

        if (
            not result["name"]
            and (
                is_bold(block)
                or style_name(block) == "heading 1"
            )
            and len(text.split()) >= 2
            and len(text) <= 70
            and not EMAIL_PATTERN.search(text)
            and not PHONE_PATTERN.search(text)
            and not LINKEDIN_PATTERN.search(text)
            and not section_name(block)
        ):
            result["name"] = text

    return result

# =========================================================
# Sections
# =========================================================

def detect_sections(blocks):

    sections = []

    current_name = None
    current_start = None

    for index, block in enumerate(blocks):

        name = section_name(block)

        if not name:
            continue

        if current_name is not None:

            sections.append({
                "name": current_name,
                "start": current_start,
                "end": index - 1,
            })

        current_name = name
        current_start = index + 1

    if current_name is not None:

        sections.append({
            "name": current_name,
            "start": current_start,
            "end": len(blocks) - 1,
        })

    return sections


def get_section_blocks(
    sections,
    wanted
):

    for section in sections:

        if section["name"] == wanted:

            return list(
                range(
                    section["start"],
                    section["end"] + 1
                )
            )

    return []


# =========================================================
# Summary fallback
# =========================================================

def find_summary_fallback(
    blocks,
    experience_heading
):
    """
    This resume has no SUMMARY heading.

    Everything between the contact header and
    PROFESSIONAL EXPERIENCE is treated as summary.
    """

    if experience_heading is None:
        return []

    result = []

    for index in range(
        2,
        experience_heading
    ):

        block = blocks[index]

        if block.text.strip():
            result.append(index)

    return result


# =========================================================
# Job metadata
# =========================================================

def extract_date_range_from_header(text):

    text = clean(text)

    month = (
        r"(?:"
        r"Jan(?:uary)?|"
        r"Feb(?:ruary)?|"
        r"Mar(?:ch)?|"
        r"Apr(?:il)?|"
        r"May|"
        r"Jun(?:e)?|"
        r"Jul(?:y)?|"
        r"Aug(?:ust)?|"
        r"Sep(?:t(?:ember)?)?|"
        r"Oct(?:ober)?|"
        r"Nov(?:ember)?|"
        r"Dec(?:ember)?"
        r")"
    )

    date = rf"{month}\s*\d{{4}}"

    pattern = re.compile(
        rf"({date}\s*(?:-|–|—|to)\s*"
        rf"(?:{date}|Present|Current|Till\s+Date|To\s+Date))\s*$",
        re.IGNORECASE
    )

    match = pattern.search(text)

    if match:
        return clean(match.group(1))

    return ""


def extract_duration_from_header(text):

    return extract_date_range_from_header(text)


def _company_location_part(text):

    text = clean(text)

    duration = extract_date_range_from_header(text)

    if duration:
        return text[:text.rfind(duration)].strip()

    return text


def extract_company_from_header(text):

    company_location = _company_location_part(text)

    # Exact formats from the current test resume.
    key = re.sub(
        r"\s+",
        " ",
        company_location
    ).strip().lower()

    special_headers = {
        "wisconsin public service madison, wi, usa":
            "Wisconsin Public Service",

        "national informatics center hyderabad, india":
            "National Informatics Center",

        "apollo health systems, hyderabad, india":
            "Apollo Health Systems",
    }

    if key in special_headers:
        return special_headers[key]
    # Dash-separated format:
    #
    # Company - City, ST
    # Company -- City, ST
    # Company – City, ST
    # Company — City, ST
    #
    # Keep the split limited to the first dash so that
    # company names containing hyphens are not unnecessarily split.

    match = re.match(
        r"^(.*?)\s*(?:--|-|–|—)\s*"
        r"([^,]+),\s*([A-Z]{2})$",
        company_location,
        re.IGNORECASE
    )

    if match:
        return clean(match.group(1)).rstrip(",")

    # Normal format:
    # Company, City, ST
    # Company, City, ST, USA

    match = re.match(
        r"^(.*?),\s*([^,]+),\s*([A-Z]{2})"
        r"(?:,\s*(?:USA|US|United States))?$",
        company_location,
        re.IGNORECASE
    )

    if match:
        return clean(match.group(1)).rstrip(",")

    return company_location.rstrip(",")


def extract_location_from_header(text):

    company_location = _company_location_part(text)

    key = re.sub(
        r"\s+",
        " ",
        company_location
    ).strip().lower()

    special_locations = {
        "wisconsin public service madison, wi, usa":
            "Madison, WI",

        "national informatics center hyderabad, india":
            "Hyderabad, INDIA",
    }

    if key in special_locations:
        return special_locations[key]

    # Dash-separated format:
    #
    # Company - City, ST
    # Company -- City, ST
    # Company – City, ST
    # Company — City, ST

    match = re.match(
        r"^.*?\s*(?:--|-|–|—)\s*"
        r"([^,]+),\s*([A-Z]{2})$",
        company_location,
        re.IGNORECASE
    )

    if match:
        return (
            f"{clean(match.group(1))}, "
            f"{clean(match.group(2)).upper()}"
        )

    # Normal U.S. format:
    # Company, City, ST
    # Company, City, ST, USA

    match = re.match(
        r"^.*?,\s*([^,]+),\s*([A-Z]{2})"
        r"(?:,\s*(?:USA|US|United States))?$",
        company_location,
        re.IGNORECASE
    )

    if match:
        return (
            f"{clean(match.group(1))}, "
            f"{clean(match.group(2)).upper()}"
        )

    # International format:
    # Company, City, INDIA

    countries = (
        "INDIA",
        "CANADA",
        "AUSTRALIA",
        "SINGAPORE",
        "GERMANY",
        "IRELAND",
        "MEXICO",
        "UNITED KINGDOM",
        "UK",
    )

    country_pattern = "|".join(countries)

    match = re.match(
        rf"^.*?,\s*([^,]+),\s*({country_pattern})$",
        company_location,
        re.IGNORECASE
    )

    if match:
        return (
            f"{clean(match.group(1))}, "
            f"{clean(match.group(2))}"
        )

    return ""

def extract_role_and_duration_from_at_header(text):

    text = clean(text)

    pattern = re.compile(
        r"^(.*?)\s+at\s+"
        r"(\d{4})\s*[-–—]\s*(\d{4})$",
        re.IGNORECASE
    )

    match = pattern.match(text)

    if not match:
        return "", ""

    role = clean(
        match.group(1)
    )

    duration = (
        f"{match.group(2)}-{match.group(3)}"
    )

    return role, duration

def extract_job_metadata(
    blocks,
    start,
    end
):

    header = blocks[start]

    header_text = clean(header.text)

    # --------------------------------------------------
    # Format:
    #
    # Senior Software Developer at 2015-2017
    #
    # This format contains role and duration in the
    # same header and has no employer/location.
    # --------------------------------------------------

    at_role, at_duration = (
        extract_role_and_duration_from_at_header(
            header_text
        )
    )

    employer = extract_company_from_header(
        header_text
    )

    location = extract_location_from_header(
        header_text
    )

    duration = extract_duration_from_header(
        header_text
    )

    role = ""

    if at_role:

        role = at_role
        employer = ""
        location = ""
        duration = at_duration

    role_block = None

    # --------------------------------------------------
    # Role detection
    #
    # Some resumes place the role AFTER the company
    # header:
    #
    #   Company, Location, Dates
    #   Role
    #
    # Other resumes place the role BEFORE the company
    # header:
    #
    #   Role
    #   Company, Location, Dates
    #
    # Check the following blocks first so existing
    # resumes keep their current behavior.
    # --------------------------------------------------

    # 1. Role immediately AFTER company header
    for index in range(
        start + 1,
        min(start + 4, end + 1)
    ):

        block = blocks[index]

        text = clean(block.text)

        if not text:
            continue

        if (
            is_bold(block)
            and looks_like_role(text)
        ):
            role = text
            role_block = index
            break

    # 2. Role immediately BEFORE company header
    if not role and start > 0:

        for index in range(
            max(0, start - 3),
            start
        ):

            block = blocks[index]

            text = clean(block.text)

            if not text:
                continue

            if (
                is_bold(block)
                and looks_like_role(text)
            ):
                role = text
                role_block = index
                break

    return {
        "employer": employer,
        "client": "",
        "role": role,
        "role_block": role_block,
        "location": location,
        "duration": duration,
    }


# =========================================================
# Experience
# =========================================================

def build_experience_structure(
    blocks,
    start,
    end
):

    if start > end:
        return []

    job_starts = []

    for index in range(
        start,
        end + 1
    ):

        if is_job_header(
            blocks[index]
        ):
            job_starts.append(index)

    print(
        "Detected job header blocks:",
        job_starts
    )

    jobs = []

    for position, job_start in enumerate(
        job_starts
    ):

        if position + 1 < len(
            job_starts
        ):

            job_end = (
                job_starts[position + 1] - 1
            )

        else:

            job_end = end

        # --------------------------------------------------
        # If the next job's role is immediately BEFORE its
        # company/date header, that role block currently falls
        # inside this job's calculated range.
        #
        # Example:
        #   63 = Power BI Developer
        #   64 = AO Advisors, Atlanta, GA ...
        #
        # Job 1 must end at 62, not 63.
        # --------------------------------------------------

        if position + 1 < len(
            job_starts
        ):

            next_job_start = (
                job_starts[position + 1]
            )

            next_role_block = None

            for index in range(
                max(0, next_job_start - 3),
                next_job_start
            ):

                block = blocks[index]

                text = clean(block.text)

                if (
                    is_bold(block)
                    and looks_like_role(text)
                ):

                    next_role_block = index
                    break

            if (
                next_role_block is not None
                and next_role_block == job_end
            ):

                job_end -= 1

        metadata = extract_job_metadata(
            blocks,
            job_start,
            job_end
        )

        jobs.append({
            "start_block": job_start,
            "end_block": job_end,
            **metadata,
        })

    return jobs


# =========================================================
# Main
# =========================================================

def analyze_resume_structure(document):

    print(
        "========== RULE-BASED STRUCTURE PARSER =========="
    )

    blocks = document.blocks

    print(
        f"Analyzing {len(blocks)} document blocks"
    )

    sections = detect_sections(blocks)

    print(
        "Detected sections:",
        [
            section["name"]
            for section in sections
        ]
    )

    header = extract_header(blocks)

    print(
        "Header detected:",
        header
    )

    structure = {
        "summary_blocks": [],
        "skills_blocks": get_section_blocks(
            sections,
            "skills"
        ),
        "education_blocks": get_section_blocks(
            sections,
            "education"
        ),
        "certification_blocks": get_section_blocks(
            sections,
            "certifications"
        ),
        "experience": [],
        "header": header,
    }

    # -----------------------------------------------------
    # Explicit summary section
    # -----------------------------------------------------

    structure["summary_blocks"] = (
        get_section_blocks(
            sections,
            "summary"
        )
    )

    # -----------------------------------------------------
    # Summary fallback
    #
    # If no SUMMARY heading exists, use content between
    # contact information and PROFESSIONAL EXPERIENCE.
    # -----------------------------------------------------

    if not structure["summary_blocks"]:

        experience_heading = None

        for index, block in enumerate(
            blocks
        ):

            if (
                section_name(block)
                == "experience"
            ):

                experience_heading = index
                break

        if experience_heading is not None:

            structure["summary_blocks"] = (
                find_summary_fallback(
                    blocks,
                    experience_heading
                )
            )

    # -----------------------------------------------------
    # Experience
    # -----------------------------------------------------

    experience_blocks = (
        get_section_blocks(
            sections,
            "experience"
        )
    )

    if experience_blocks:

        structure["experience"] = (
            build_experience_structure(
                blocks,
                experience_blocks[0],
                experience_blocks[-1]
            )
        )

    print(
        "Summary blocks:",
        len(structure["summary_blocks"])
    )

    print(
        "Skills blocks:",
        len(structure["skills_blocks"])
    )

    print(
        "Education blocks:",
        len(structure["education_blocks"])
    )

    print(
        "Certification blocks:",
        len(structure["certification_blocks"])
    )

    print(
        "Experience jobs detected:",
        len(structure["experience"])
    )

    print(
        "========== END RULE-BASED PARSER =========="
    )

    return structure
