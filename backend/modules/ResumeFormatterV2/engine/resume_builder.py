import re

from engine.models import (
    Resume,
    Job,
    Project
)


EMAIL_REGEX = r'[\w\.-]+@[\w\.-]+\.\w+'

PHONE_REGEX = (
    r'(\+?\d[\d\s().-]{8,})'
)

LINKEDIN_REGEX = (
    r'https?://(?:www\.)?'
    r'linkedin\.com/in/[^\s]+'
)


# ==========================================================
# HELPERS
# ==========================================================

def clean_text(text):

    if not text:

        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text)
    ).strip()


def get_blocks_by_indexes(
    document,
    indexes
):

    result = []

    total = len(
        document.blocks
    )

    for index in indexes:

        if (
            isinstance(index, int)
            and 0 <= index < total
        ):

            result.append(
                document.blocks[index]
            )

    return result


def get_block_texts(
    document,
    indexes
):

    result = []

    for block in get_blocks_by_indexes(
        document,
        indexes
    ):

        text = clean_text(
            block.text
        )

        if text:

            result.append(text)

    return result


def normalize_compare(text):

    value = clean_text(
        text
    ).lower()

    value = re.sub(
        r'[^a-z0-9]+',
        ' ',
        value
    )

    return re.sub(
        r'\s+',
        ' ',
        value
    ).strip()


# ==========================================================
# NAME
# ==========================================================

def extract_name(
    document,
    structure,
    resume
):

    # ------------------------------------------------------
    # Prefer the name already detected by the rule-based
    # structure parser.
    # ------------------------------------------------------

    detected_header = structure.get(
        "header",
        {}
    )

    detected_name = clean_text(
        detected_header.get(
            "name",
            ""
        )
    )

    if detected_name:
        return detected_name
    # ------------------------------------------------------
    # Find first structural content block.
    #
    # Anything before this is likely header/contact content.
    # ------------------------------------------------------

    structural_indexes = []

    for key in [

        "summary_blocks",

        "skills_blocks",

        "education_blocks",

        "certification_blocks"

    ]:

        structural_indexes.extend(
            structure.get(
                key,
                []
            )
        )

    for employment in structure.get(
        "experience",
        []
    ):

        start = employment.get(
            "start_block"
        )

        if isinstance(
            start,
            int
        ):

            structural_indexes.append(
                start
            )

    if structural_indexes:

        first_content = min(
            structural_indexes
        )

    else:

        first_content = min(
            len(document.blocks),
            10
        )

    # ------------------------------------------------------
    # Search header blocks for likely name.
    # ------------------------------------------------------

    for block in document.blocks[
        :first_content
    ]:

        text = clean_text(
            block.text
        )

        if not text:

            continue

        lower = text.lower()

        if (
            resume.email
            and resume.email.lower()
            in lower
        ):

            continue

        if (
            resume.phone
            and normalize_compare(
                resume.phone
            )
            in normalize_compare(
                text
            )
        ):

            continue

        if "linkedin.com" in lower:

            continue

        if "@" in text:

            continue

        # Avoid very long paragraph being used as name.

        if len(
            text.split()
        ) > 8:

            continue

        # Avoid obvious resume labels.

        if lower in {

            "resume",

            "curriculum vitae",

            "professional summary",

            "summary",

            "technical skills",

            "skills",

            "professional experience",

            "work experience",

            "experience"

        }:

            continue

        return text

    return ""


# ==========================================================
# SUMMARY
# ==========================================================

def build_summary(
    document,
    structure
):

    return get_block_texts(

        document,

        structure.get(
            "summary_blocks",
            []
        )

    )


# ==========================================================
# SKILLS
# ==========================================================

def build_skills(
    document,
    structure
):

    skill_lines = get_block_texts(

        document,

        structure.get(
            "skills_blocks",
            []
        )

    )

    skills = {}

    uncategorized = []

    for line in skill_lines:

        # --------------------------------------------------
        # Category: values
        # --------------------------------------------------

        if ":" in line:

            category, value = (
                line.split(
                    ":",
                    1
                )
            )

            category = clean_text(
                category
            )

            value = clean_text(
                value
            )

            if (
                category
                and value
                and len(
                    category.split()
                ) <= 8
            ):

                values = [

                    clean_text(item)

                    for item in re.split(
                        r'[,;|]',
                        value
                    )

                    if clean_text(item)

                ]

                if values:

                    if category not in skills:

                        skills[
                            category
                        ] = []

                    skills[
                        category
                    ].extend(
                        values
                    )

                    continue

        # --------------------------------------------------
        # Table extraction may produce:
        #
        # Languages
        # Python, Java, SQL
        #
        # We do not guess the category relationship here.
        # Preserve it safely.
        # --------------------------------------------------

        uncategorized.append(
            line
        )

    if uncategorized:

        skills[
            "Technical Skills"
        ] = uncategorized

    # ------------------------------------------------------
    # Remove duplicates while preserving order.
    # ------------------------------------------------------

    for category in list(
        skills.keys()
    ):

        seen = set()

        unique = []

        for item in skills[
            category
        ]:

            key = normalize_compare(
                item
            )

            if not key:

                continue

            if key in seen:

                continue

            seen.add(key)

            unique.append(
                item
            )

        skills[
            category
        ] = unique

    return skills


# ==========================================================
# EDUCATION / CERTIFICATIONS
# ==========================================================

def build_simple_section(
    document,
    indexes
):

    return get_block_texts(
        document,
        indexes
    )


# ==========================================================
# EXPERIENCE HELPERS
# ==========================================================

def is_environment_heading(
    text
):

    value = (
        normalize_compare(
            text
        )
    )

    return value in {

        "environment",

        "technical environment",

        "technology",

        "technologies",

        "technology stack",

        "technical stack",

        "tools",

        "tools technologies"

    }


def extract_environment_value(
    text
):

    match = re.search(

        r'(?:technical\s+environment|'
        r'environment|'
        r'technology\s+stack|'
        r'technologies|'
        r'technology|'
        r'tools)'
        r'\s*:\s*'
        r'(.+?)(?:\n|$)',

        text,

        re.IGNORECASE

    )

    if not match:

        return ""

    return clean_text(
        match.group(1)
    )

def extract_project_value(
    text
):

    match = re.match(

        r'^\s*project\s*:\s*(.+)$',

        text,

        re.IGNORECASE

    )

    if not match:

        return ""

    value = clean_text(
        match.group(1)
    )

    # ------------------------------------------------------
    # Project line may contain:
    #
    # Project: Debit Applications | Client: TD
    #
    # Keep only project portion.
    # ------------------------------------------------------

    value = re.split(

        r'\|\s*client\s*:',

        value,

        maxsplit=1,

        flags=re.IGNORECASE

    )[0]

    return clean_text(
        value
    )


def is_metadata_line(
    text,
    job,
    project
):

    value = normalize_compare(
        text
    )

    if not value:

        return True

    # ------------------------------------------------------
    # Standalone labels
    # ------------------------------------------------------

    if value in {

        "client",

        "employer",

        "company",

        "organization",

        "role",

        "title",

        "position",

        "project",

        "duration",

        "location",

        "responsibilities",

        "key responsibilities",

        "professional responsibilities"

    }:

        return True

    # ------------------------------------------------------
    # Explicit metadata labels
    # ------------------------------------------------------

    if re.match(
        r'^\s*client\s*:',
        text,
        re.IGNORECASE
    ):

        return True

    if re.match(
        r'^\s*(?:employer|company|organization)\s*:',
        text,
        re.IGNORECASE
    ):

        return True

    if re.match(
        r'^\s*(?:role|title|position)\s*:',
        text,
        re.IGNORECASE
    ):

        return True

    if re.match(
        r'^\s*duration\s*:',
        text,
        re.IGNORECASE
    ):

        return True

    if re.match(
        r'^\s*location\s*:',
        text,
        re.IGNORECASE
    ):

        return True

    # ------------------------------------------------------
    # Exact duplicate values extracted by AI.
    # ------------------------------------------------------

    metadata_values = [

        job.employer,

        job.client,

        job.role,

        job.location,

        job.duration,

        project.title

    ]

    for metadata in metadata_values:

        metadata_value = (
            normalize_compare(
                metadata
            )
        )

        if (
            metadata_value
            and value == metadata_value
        ):

            return True

    return False


def looks_like_header_metadata(
    text,
    job
):

    value = normalize_compare(
        text
    )

    if not value:

        return False

    # ------------------------------------------------------
    # If the source line contains multiple extracted fields,
    # it is likely the compact employment header.
    #
    # Example:
    #
    # Optum – Data Engineer | Raleigh, NC Jul 2024 - Present
    # ------------------------------------------------------

    matches = 0

    for metadata in [

        job.employer,

        job.client,

        job.role,

        job.location,

        job.duration

    ]:

        metadata_value = (
            normalize_compare(
                metadata
            )
        )

        if (
            metadata_value
            and metadata_value in value
        ):

            matches += 1

    return matches >= 2


# ==========================================================
# BUILD EXPERIENCE
# ==========================================================

def build_experience(
    document,
    structure
):

    jobs = []

    total = len(
        document.blocks
    )

    for employment_index, item in enumerate(

        structure.get(
            "experience",
            []
        ),

        start=1

    ):

        start = item.get(
            "start_block"
        )

        end = item.get(
            "end_block"
        )

        if not isinstance(
            start,
            int
        ):

            continue

        if not isinstance(
            end,
            int
        ):

            continue

        if not (
            0 <= start < total
        ):

            continue

        if not (
            0 <= end < total
        ):

            continue

        if end < start:

            start, end = (
                end,
                start
            )

        job = Job()

        job.employer = clean_text(
            item.get(
                "employer",
                ""
            )
        )

        job.client = clean_text(
            item.get(
                "client",
                ""
            )
        )

        job.role = clean_text(
            item.get(
                "role",
                ""
            )
        )

        job.location = clean_text(
            item.get(
                "location",
                ""
            )
        )

        job.duration = clean_text(
            item.get(
                "duration",
                ""
            )
        )

        current_project = Project()

        current_project.role = (
            job.role
        )

        job.projects.append(
            current_project
        )

        environment_mode = False

        # --------------------------------------------------
        # Walk ORIGINAL source blocks selected by AI.
        #
        # AI determines boundary/semantics.
        # Python preserves actual resume content.
        # --------------------------------------------------

        for block_index in range(
            start,
            end + 1
        ):

            block = document.blocks[
                block_index
            ]
            # ------------------------------------------------
            # Skip the block that was identified as the job role.
            #
            # Some resumes place the role immediately BEFORE
            # the company/date header. That role is already
            # stored in job.role and must not be processed
            # again as project/environment content.
            # ------------------------------------------------

            role_block = item.get(
                "role_block"
            )

            if (
                role_block is not None
                and block_index == role_block
            ):

                continue

            text = clean_text(
                block.text
            )

            if not text:

                continue

            # ------------------------------------------------
            # Environment on same line:
            #
            # Environment: COBOL, DB2, CICS
            # ------------------------------------------------

            environment_value = (
                extract_environment_value(
                    text
                )
            )

            if environment_value:

                job.environment.append(
                    environment_value
                )

                environment_mode = True

                continue

            # ------------------------------------------------
            # Standalone environment heading
            # ------------------------------------------------

            if is_environment_heading(
                text
            ):

                environment_mode = True

                continue

            # ------------------------------------------------
            # Project
            # ------------------------------------------------

            project_value = (
                extract_project_value(
                    text
                )
            )

            if project_value:

                if not current_project.title:

                    current_project.title = (
                        project_value
                    )

                else:

                    # Multiple projects may exist.
                    #
                    # Preserve additional project information
                    # without inventing employment boundaries.

                    new_project = Project()

                    new_project.title = (
                        project_value
                    )

                    new_project.role = (
                        job.role
                    )

                    job.projects.append(
                        new_project
                    )

                    current_project = (
                        new_project
                    )

                environment_mode = False

                continue

            # ------------------------------------------------
            # Environment continuation
            # ------------------------------------------------

            if environment_mode:

                # A clear responsibility bullet/sentence may
                # indicate environment section has ended.
                #
                # We use a conservative signal.

                if (
                    len(
                        text.split()
                    ) > 15
                    and text.endswith(".")
                ):

                    environment_mode = False

                else:

                    job.environment.append(
                        text
                    )

                    continue

            # ------------------------------------------------
            # Skip explicit/exact metadata
            # ------------------------------------------------

            if is_metadata_line(
                text,
                job,
                current_project
            ):

                continue

            # ------------------------------------------------
            # Skip compact employment header
            # ------------------------------------------------

            if looks_like_header_metadata(
                text,
                job
            ):

                continue

            # ------------------------------------------------
            # Responsibility
            # ------------------------------------------------

            current_project.responsibilities.append(
                text
            )

        # --------------------------------------------------
        # Cleanup projects
        # --------------------------------------------------

        valid_projects = []

        for project in job.projects:

            seen = set()

            responsibilities = []

            for responsibility in (
                project.responsibilities
            ):

                value = clean_text(
                    responsibility
                )

                key = normalize_compare(
                    value
                )

                if not key:

                    continue

                if key in seen:

                    continue

                seen.add(key)

                responsibilities.append(
                    value
                )

            project.responsibilities = (
                responsibilities
            )

            if (

                project.title

                or project.role

                or project.duration

                or project.responsibilities

            ):

                valid_projects.append(
                    project
                )

        job.projects = valid_projects

        print(
             "DEBUG ENV BEFORE CLEANUP:",
             job.employer,
             job.environment
        )
        # --------------------------------------------------
        # Cleanup environment
        # --------------------------------------------------

        seen_environment = set()

        environment = []

        for value in job.environment:

            value = clean_text(
                value
            )

            key = normalize_compare(
                value
            )

            if not key:

                continue

            if key in seen_environment:

                continue

            seen_environment.add(
                key
            )

            environment.append(
                value
            )

        job.environment = (
            environment
        )

        if not job.environment:

            job.environment = [
                "ADD ENVIRONMENT"
            ]

        # --------------------------------------------------
        # Keep meaningful employment
        # --------------------------------------------------

        if (

            job.employer

            or job.client

            or job.role

            or job.duration

        ):

            jobs.append(
                job
            )

            print(
                f"\nJOB {employment_index}"
            )

            print(
                "Employer :",
                job.employer
            )

            print(
                "Client   :",
                job.client
            )

            print(
                "Location :",
                job.location
            )

            print(
                "Role     :",
                job.role
            )

            print(
                "Duration :",
                job.duration
            )

            print(
                "Blocks   :",
                start,
                "-",
                end
            )

    return jobs


# ==========================================================
# BUILD RESUME
# ==========================================================

def build_resume(
    document,
    structure
):

    resume = Resume()

    resume.raw_document = (
        document
    )

    text = document.get_text()

    # ======================================================
    # CONTACT DETAILS
    # ======================================================

    email = re.search(
        EMAIL_REGEX,
        text
    )

    if email:

        resume.email = (
            email.group()
        )

    phone = re.search(
        PHONE_REGEX,
        text
    )

    if phone:

        resume.phone = (
            phone.group()
            .strip()
        )

    linkedin = re.search(

        LINKEDIN_REGEX,

        text,

        re.IGNORECASE

    )

    if linkedin:

        resume.linkedin = (
            linkedin.group()
        )

    # ======================================================
    # NAME
    # ======================================================

    resume.name = extract_name(

        document,

        structure,

        resume

    )

    # ======================================================
    # SUMMARY
    # ======================================================

    resume.summary = build_summary(

        document,

        structure

    )

    # ======================================================
    # EXPERIENCE
    # ======================================================

    resume.experience = build_experience(

        document,

        structure

    )

    # ======================================================
    # SKILLS
    # ======================================================

    resume.technical_skills = build_skills(

        document,

        structure

    )

    # ======================================================
    # EDUCATION
    # ======================================================

    resume.education = build_simple_section(

        document,

        structure.get(
            "education_blocks",
            []
        )

    )

    # ======================================================
    # CERTIFICATIONS
    # ======================================================

    resume.certifications = build_simple_section(

        document,

        structure.get(
            "certification_blocks",
            []
        )

    )

    # ======================================================
    # DEBUG
    # ======================================================

    print(
        "\n========== FINAL PARSED RESUME =========="
    )

    print(
        "Name:",
        resume.name
    )

    print(
        "Summary blocks:",
        len(
            resume.summary
        )
    )

    print(
        "Skill categories:",
        len(
            resume.technical_skills
        )
    )

    print(
        "Experience:",
        len(
            resume.experience
        )
    )

    print(
        "Education:",
        len(
            resume.education
        )
    )

    print(
        "Certifications:",
        len(
            resume.certifications
        )
    )

    for index, job in enumerate(

        resume.experience,

        start=1

    ):

        print(
            f"\nJOB {index}"
        )

        print(
            "Employer    :",
            job.employer
        )

        print(
            "Client      :",
            job.client
        )

        print(
            "Location    :",
            job.location
        )

        print(
            "Role        :",
            job.role
        )

        print(
            "Duration    :",
            job.duration
        )

        print(
            "Projects    :",
            len(
                job.projects
            )
        )

        responsibility_count = sum(

            len(
                project.responsibilities
            )

            for project in job.projects

        )

        print(
            "Responsibilities:",
            responsibility_count
        )

        print(
            "Environment :",
            job.environment
        )

    print(
        "\n=========================================\n"
    )

    return resume
