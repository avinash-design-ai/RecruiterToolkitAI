import re


class ResumeSections:

    def __init__(self):

        self.header = []
        self.summary = []
        self.skills = []
        self.experience = []
        self.education = []
        self.certifications = []


SUMMARY = [
    "summary",
    "professional summary",
    "career summary",
    "executive summary",
    "profile",
    "professional profile",
    "summary of qualifications",
    "professional overview",
    "career profile",
    "objective"
]

SKILLS = [
    "technical skills",
    "skills",
    "technical expertise",
    "technology",
    "skill set",
    "core competencies",
    "technical proficiencies",
    "core skills",
    "areas of expertise",
    "technical proficiency",
    "technical competencies",
    "professional skills"
]

EXPERIENCE = [
    "professional experience",
    "experience",
    "employment history",
    "work experience",
    "career history",
    "professional background"
]

EDUCATION = [
    "education",
    "academic",
    "qualification",
    "academics"
]

CERTIFICATIONS = [
    "certification",
    "certifications",
    "licenses",
    "license"
]


def clean(text):

    return re.sub(
        r'[^a-z ]',
        '',
        text.lower()
    ).strip()


def is_heading(text, headings):

    value = clean(text)

    # Exact match
    for heading in headings:

        if value == heading:

            return True

    # Ends with heading
    for heading in headings:

        if value.endswith(heading):

            return True

    return False


def contains(text, words):

    value = clean(text)

    for word in words:

        if word in value:

            return True

    return False


def map_sections(document):

    sections = ResumeSections()

    # -----------------------------------
    # Pass 1 - Detect section starts
    # -----------------------------------

    section_start = {

        "summary": None,
        "skills": None,
        "experience": None,
        "education": None,
        "certifications": None

    }

    for index, block in enumerate(document.blocks):

        text = block.text.strip()

        if not text:

            continue

        if is_heading(text, SUMMARY):

            if section_start["summary"] is None:

                section_start["summary"] = index

            continue

        if is_heading(text, SKILLS):

            if section_start["skills"] is None:

                section_start["skills"] = index

            continue

        if is_heading(text, EXPERIENCE):

            if section_start["experience"] is None:

                section_start["experience"] = index

            continue

        # -----------------------------------
        # Education / Certification
        # -----------------------------------

        # Combined Heading
        if contains(text, EDUCATION) and contains(text, CERTIFICATIONS):

            if section_start["education"] is None:

                section_start["education"] = index

            continue

        # Education only
        if is_heading(text, EDUCATION):

            if section_start["education"] is None:

                section_start["education"] = index

        # Certifications only
        if is_heading(text, CERTIFICATIONS):

            if section_start["certifications"] is None:

                section_start["certifications"] = index

        
    print("\n===== SECTION STARTS =====")
    print(section_start)
    print("==========================\n")

    # -----------------------------------
    # Pass 2 - Assign blocks
    # -----------------------------------

    total = len(document.blocks)

    positions = []

    for name, pos in section_start.items():

        if pos is not None:

            positions.append((pos, name))

    positions.sort()

    print("\n===== DETECTED HEADINGS =====")

    for pos, name in positions:

        print(
            f"{name:<15} Block {pos:<3} -> {document.blocks[pos].text}"
        )

    print("=============================\n")

    # Header = everything before first section
    first_section = positions[0][0] if positions else total

    sections.header = document.blocks[:first_section]

    # No headings found
    if not positions:

        return sections

    # Slice each section
    for i, (start, name) in enumerate(positions):

        end = total

        if i + 1 < len(positions):

            end = positions[i + 1][0]

        setattr(

            sections,

            name,

            document.blocks[start + 1:end]   # Skip heading itself

        )

    return sections
