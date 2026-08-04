import re
from engine.models import Job, Project
from engine.ai_repair import repair_header


# -------------------------------------------------------
# Environment Headers
# -------------------------------------------------------

ENV_HEADERS = {

    "environment",
    "environment:",
    "technical environment",
    "technical environment:",
    "technology",
    "technology:",
    "technology stack",
    "technology stack:",
    "tools",
    "tools:"

}


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def clean(text):

    return " ".join(
        str(text).split()
    ).strip()


def is_environment(text):

    value = clean(text).lower()

    return (

        value in ENV_HEADERS

        or value.startswith("environment")

    )

DATE_PATTERN = re.compile(
    r"(Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December).*(Present|\d{4})",
    re.IGNORECASE,
)


def is_duration_line(text):

    return bool(

        DATE_PATTERN.search(text)

    )

# -------------------------------------------------------
# Split Professional Experience into Employment Blocks
# -------------------------------------------------------

def split_employment_blocks(experience_blocks):

    employment_blocks = []

    current_block = []

    current_header = None

    i = 0

    while i < len(experience_blocks):

        block = experience_blocks[i]
        line = clean(block.text)

        if not line:

            if current_block:
                current_block.append(block)

            i += 1
            continue

        # --------------------------------------------------
        # Candidate employment boundary
        #
        # We do NOT ask AI here.
        # We only look for structural evidence that a new
        # employment entry may be starting.
        # --------------------------------------------------

        new_employment = False

        if is_duration_line(line):

            # Gather nearby NON-EMPTY lines before/after date.
            before = []
            after = []

            j = i - 1

            while j >= 0 and len(before) < 3:

                value = clean(experience_blocks[j].text)

                if value:
                    before.insert(0, value)

                j -= 1

            j = i + 1

            while j < len(experience_blocks) and len(after) < 3:

                value = clean(experience_blocks[j].text)

                if value:
                    after.append(value)

                j += 1

            # --------------------------------------------------
            # Structural signals only.
            #
            # We are NOT deciding:
            # employer vs client,
            # project vs company,
            # role semantics.
            #
            # Those ambiguous fields can be repaired later.
            # --------------------------------------------------

            nearby = before + [line] + after

            lower_nearby = [
                value.lower()
                for value in nearby
            ]

            has_role_label = any(
                value.startswith("role:")
                or value.startswith("title:")
                or value.startswith("position:")
                for value in lower_nearby
            )

            has_client_label = any(
                value.startswith("client:")
                or "| client:" in value
                for value in lower_nearby
            )

            has_employer_label = any(
                value.startswith("employer:")
                or value.startswith("company:")
                or value.startswith("organization:")
                for value in lower_nearby
            )

            has_project_label = any(
                value.startswith("project:")
                for value in lower_nearby
            )

            # A date near explicit employment metadata is a
            # strong candidate.
            if (
                has_role_label
                or has_client_label
                or has_employer_label
            ):
                new_employment = True

            else:

                # --------------------------------------------------
                # Unlabelled compact header:
                #
                # Example:
                # BLUE SHIELD OF CALIFORNIA, SAN FRANCISCO, CA
                # September 2016 – Present
                # Sr. Product Analyst ...
                #
                # Or:
                # Optum – Data Engineer | Raleigh, NC Jul 2024 - Present
                #
                # The date itself may be on the same line.
                #
                # We only accept this when the date appears near the
                # beginning of a candidate block, rather than deep
                # inside responsibilities.
                # --------------------------------------------------

                meaningful_before = [
                    clean(item.text)
                    for item in current_block[-4:]
                    if clean(item.text)
                ]

                if not current_block:

                    new_employment = True

                elif len(meaningful_before) <= 2:

                    new_employment = True

                else:

                    # Look at the immediately preceding meaningful line.
                    previous = before[-1] if before else ""

                    previous_lower = previous.lower()

                    # Reject obvious project-only duration context.
                    project_context = (
                        previous_lower.startswith("project:")
                        or (
                            has_project_label
                            and not has_role_label
                            and not has_client_label
                            and not has_employer_label
                        )
                    )

                    if not project_context:

                        # A new header after a substantial existing
                        # employment block is possible when the line
                        # before the date is short/header-like rather
                        # than a responsibility sentence.
                        previous_word_count = len(previous.split())

                        previous_looks_header_like = (
                            bool(previous)
                            and previous_word_count <= 12
                            and not previous.endswith(".")
                        )

                        if previous_looks_header_like:
                            new_employment = True

        # --------------------------------------------------
        # Start new employment block
        # --------------------------------------------------

        if new_employment:

            if current_block:

                employment_blocks.append({
                    "header": current_header,
                    "blocks": current_block
                })

                current_block = []

            # No AI header object here.
            # Header parsing/repair happens later.
            current_header = None

        current_block.append(block)

        i += 1

    # --------------------------------------------------
    # Final employment block
    # --------------------------------------------------

    if current_block:

        employment_blocks.append({
            "header": current_header,
            "blocks": current_block
        })

    print("\n===================================")
    print(
        f"Employment Blocks Found : "
        f"{len(employment_blocks)}"
    )
    print("===================================\n")

    return employment_blocks

# -------------------------------------------------------
# Parse One Employment
# -------------------------------------------------------

def parse_employment(employment, header=None):

    job = Job()

    current_project = Project()

    job.projects.append(current_project)

    environment_mode = False

    # --------------------------------------------------
    # Collect beginning of employment block.
    #
    # This is the context used for Python extraction
    # and, only if needed, AI repair.
    #
    # Do NOT send the entire employment history to AI.
    # --------------------------------------------------

    header_lines = []

    for block in employment[:8]:

        text = clean(block.text)

        if text:

            header_lines.append(text)

    # --------------------------------------------------
    # Use existing Python header result if available.
    # --------------------------------------------------

    if header is not None:

        job.client = clean(
            getattr(header, "client", "")
        )

        job.employer = clean(
            getattr(header, "employer", "")
        )

        job.location = clean(
            getattr(header, "location", "")
        )

        job.role = clean(
            getattr(header, "role", "")
        )

        job.duration = clean(
            getattr(header, "duration", "")
        )

        existing_raw_lines = getattr(
            header,
            "raw_lines",
            []
        )

        if existing_raw_lines:

            header_lines = [
                clean(line)
                for line in existing_raw_lines
                if clean(line)
            ]

    # --------------------------------------------------
    # Lightweight Python extraction.
    #
    # IMPORTANT:
    # These rules only extract information when explicit.
    # They do NOT guess employer/client semantics.
    #
    # Ambiguous missing fields are left for AI repair.
    # --------------------------------------------------

    consumed_indexes = set()

    for index, block in enumerate(employment[:8]):

        line = clean(block.text)

        if not line:

            continue

        lower = line.lower()

        # ----------------------------------------------
        # Explicit Client
        # ----------------------------------------------

        client_match = re.search(
            r'\bclient\s*:\s*([^|]+)',
            line,
            re.IGNORECASE
        )

        if client_match and not job.client:

            job.client = clean(
                client_match.group(1)
            )

            consumed_indexes.add(index)

        # ----------------------------------------------
        # Explicit Employer / Company / Organization
        # ----------------------------------------------

        employer_match = re.search(
            r'\b(?:employer|company|organization)\s*:\s*([^|]+)',
            line,
            re.IGNORECASE
        )

        if employer_match and not job.employer:

            job.employer = clean(
                employer_match.group(1)
            )

            consumed_indexes.add(index)

        # ----------------------------------------------
        # Explicit Role / Title / Position
        # ----------------------------------------------

        role_match = re.search(
            r'\b(?:role|title|position)\s*:\s*(.+)',
            line,
            re.IGNORECASE
        )

        if role_match and not job.role:

            job.role = clean(
                role_match.group(1)
            )

            consumed_indexes.add(index)

        # ----------------------------------------------
        # Duration
        #
        # Use existing duration detector.
        # Do not infer employment vs project here.
        # The splitter already selected this block.
        # ----------------------------------------------

        if (
            not job.duration
            and is_duration_line(line)
        ):

            job.duration = line

            consumed_indexes.add(index)

    # --------------------------------------------------
    # AI GAP REPAIR
    #
    # One call maximum for this employment.
    #
    # Existing Python values are protected inside
    # repair_header().
    # --------------------------------------------------

    job = repair_header(
        job,
        header_lines
    )

    # --------------------------------------------------
    # Determine which beginning lines belong to header.
    #
    # We cannot use old:
    #
    # consumed = len(header.raw_lines)
    #
    # because header may now be None.
    #
    # Instead, skip lines that correspond to values
    # already extracted as header metadata.
    # --------------------------------------------------

    i = 0

    while i < len(employment):

        block = employment[i]

        line = clean(block.text)

        if not line:

            i += 1
            continue

        lower = line.lower()

        # --------------------------------------------------
        # Skip lines already explicitly consumed by Python.
        # --------------------------------------------------

        if i in consumed_indexes:

            i += 1
            continue

        # --------------------------------------------------
        # Environment Section
        # --------------------------------------------------

        if is_environment(line):

            environment_mode = True

            i += 1
            continue

        if environment_mode:

            job.environment.append(line)

            i += 1
            continue

        # --------------------------------------------------
        # Ignore standalone labels
        # --------------------------------------------------

        if lower in {

            "client",
            "client:",

            "employer",
            "employer:",

            "company",
            "company:",

            "organization",
            "organization:",

            "project",
            "project:",

            "role",
            "role:",

            "title",
            "title:",

            "position",
            "position:",

            "responsibilities",
            "responsibilities:",

            "key responsibilities",
            "key responsibilities:",

            "environment",
            "environment:",

            "technical environment",
            "technical environment:",

            "technology",
            "technology:",

            "technology stack",
            "technology stack:",

            "tools",
            "tools:"

        }:

            i += 1
            continue

        # --------------------------------------------------
        # Ignore lines containing explicit header metadata
        # --------------------------------------------------

        if re.search(
            r'\bclient\s*:',
            line,
            re.IGNORECASE
        ):

            i += 1
            continue

        if re.search(
            r'\b(?:employer|company|organization)\s*:',
            line,
            re.IGNORECASE
        ):

            i += 1
            continue

        if re.search(
            r'\b(?:role|title|position)\s*:',
            line,
            re.IGNORECASE
        ):

            i += 1
            continue

        # --------------------------------------------------
        # Ignore duplicate extracted header values
        # --------------------------------------------------

        normalized_values = {

            clean(job.client),
            clean(job.employer),
            clean(job.role),
            clean(job.location),
            clean(job.duration)

        }

        normalized_values.discard("")

        if line in normalized_values:

            i += 1
            continue

        # --------------------------------------------------
        # Avoid adding the employment duration as a
        # responsibility.
        # --------------------------------------------------

        if (
            job.duration
            and (
                line == clean(job.duration)
                or clean(job.duration) in line
            )
        ):

            i += 1
            continue

        # --------------------------------------------------
        # Project line
        #
        # User preference:
        # We do NOT need perfect project parsing.
        # Keep project information safely with the job
        # instead of allowing it to become employer/client.
        # --------------------------------------------------

        if lower.startswith("project:"):

            project_text = clean(
                line.split(":", 1)[1]
            )

            if project_text:

                current_project.responsibilities.append(
                    "Project: " + project_text
                )

            i += 1
            continue

        # --------------------------------------------------
        # Responsibility
        # --------------------------------------------------

        current_project.responsibilities.append(
            line
        )

        i += 1

    # --------------------------------------------------
    # Cleanup
    # --------------------------------------------------

    current_project.responsibilities = [

        clean(item)

        for item in current_project.responsibilities

        if clean(item)

    ]

    job.environment = [

        clean(item)

        for item in job.environment

        if clean(item)

    ]

    return job


def parse_experience(experience_blocks, manager):

    jobs = []

    # --------------------------------------------------
    # Python-only employment splitting.
    #
    # No AI should be called inside this function.
    # --------------------------------------------------

    employment_blocks = split_employment_blocks(
        experience_blocks
    )

    print("\n===================================")
    print(
        f"Employment Blocks Found : "
        f"{len(employment_blocks)}"
    )
    print("===================================\n")

    # --------------------------------------------------
    # Parse each employment.
    # --------------------------------------------------

    for index, employment in enumerate(
        employment_blocks,
        start=1
    ):

        blocks = employment.get(
            "blocks",
            []
        )

        if not blocks:

            continue

        header = employment.get(
            "header"
        )

        print(
            f"\n===== PARSING EMPLOYMENT "
            f"{index} ====="
        )

        job = parse_employment(
            blocks,
            header
        )

        # --------------------------------------------------
        # Environment placeholder
        # --------------------------------------------------

        if not job.environment:

            job.environment.append(
                "ADD ENVIRONMENT"
            )

        # --------------------------------------------------
        # Remove empty projects
        # --------------------------------------------------

        valid_projects = []

        for project in job.projects:

            project.responsibilities = [

                clean(item)

                for item in project.responsibilities

                if clean(item)

            ]

            if (

                project.responsibilities

                or project.title

                or project.role

                or project.duration

            ):

                valid_projects.append(
                    project
                )

        if valid_projects:

            job.projects = valid_projects

        else:

            job.projects = []

        # --------------------------------------------------
        # Keep valid jobs
        #
        # Responsibilities alone should NOT create a fake
        # employment entry.
        # Require at least meaningful employment metadata.
        # --------------------------------------------------

        if (

            job.client

            or job.employer

            or job.role

            or job.duration

        ):

            jobs.append(job)

            print(
                f"KEPT EMPLOYMENT {index}"
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
                "Role     :",
                job.role
            )

            print(
                "Location :",
                job.location
            )

            print(
                "Duration :",
                job.duration
            )

        else:

            print(
                f"SKIPPED EMPLOYMENT {index} "
                f"- no employment metadata"
            )

    # --------------------------------------------------
    # Claim experience blocks
    # --------------------------------------------------

    claimed = []

    for index, block in enumerate(
        manager.blocks
    ):

        if block in experience_blocks:

            claimed.append(index)

    manager.claim(claimed)

    return jobs
