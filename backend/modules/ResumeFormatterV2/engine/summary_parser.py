from engine.section_mapper import (
    contains,
    clean,
    SKILLS,
    EXPERIENCE,
    EDUCATION,
    CERTIFICATIONS,
)


SUMMARY_HEADINGS = {

    "summary",
    "professional summary",
    "career summary",
    "profile",
    "professional profile",
    "career objective",
    "objective",
    "about",
    "about me",
    "executive summary",
    "professional overview",
    "summary of qualifications",
    "qualifications summary",
    "career highlights"

}


def is_major_section(text):

    value = clean(text)

    return (

        contains(value, SKILLS)

        or contains(value, EXPERIENCE)

        or contains(value, EDUCATION)

        or contains(value, CERTIFICATIONS)

    )


def is_contact_line(
    text,
    resume
):

    if not text:

        return True

    if resume.name and text == resume.name:

        return True

    if resume.email and resume.email in text:

        return True

    if resume.phone and resume.phone in text:

        return True

    if resume.linkedin and resume.linkedin in text:

        return True

    return False


def parse_summary(
    resume,
    blocks,
    sections
):

    summary = []

    # ======================================================
    # LEVEL 1
    #
    # Explicit summary section detected by section_mapper.
    #
    # This is the preferred and safest path.
    # No AI is needed here.
    # ======================================================

    if sections.summary:

        for block in sections.summary:

            text = block.text.strip()

            if not text:

                continue

            if is_major_section(text):

                break

            summary.append(text)

        if summary:

            return summary

    # ======================================================
    # LEVEL 2
    #
    # No explicit summary section was detected.
    #
    # Infer a conservative summary only from content before
    # the first known major resume section.
    #
    # IMPORTANT:
    # Do NOT call AI header detection here.
    # Do NOT scan the entire resume with sliding windows.
    # ======================================================

    first_major_section_index = None

    for i, block in enumerate(blocks):

        text = block.text.strip()

        if not text:

            continue

        if is_major_section(text):

            first_major_section_index = i

            break

    if first_major_section_index is None:

        candidate_blocks = blocks

    else:

        candidate_blocks = blocks[
            :first_major_section_index
        ]

    for block in candidate_blocks:

        text = block.text.strip()

        if not text:

            continue

        if is_contact_line(
            text,
            resume
        ):

            continue

        value = clean(text)

        # ----------------------------------------------
        # Skip summary heading itself if mapper failed
        # to create sections.summary.
        # ----------------------------------------------

        if value in SUMMARY_HEADINGS:

            continue

        # ----------------------------------------------
        # Do not allow another major section heading.
        # ----------------------------------------------

        if is_major_section(text):

            break

        summary.append(text)

    if summary:

        return summary

    # ======================================================
    # LEVEL 3
    #
    # Nothing reliable was found.
    #
    # Return empty instead of accidentally copying skills,
    # education, certifications or experience into summary.
    #
    # AI summary generation can later handle this case with
    # ONE intentional call using already parsed resume data.
    # ======================================================

    return []
