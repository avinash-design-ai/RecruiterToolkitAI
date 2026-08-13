from engine.header_detector import detect_header


def build_job_blocks(blocks):
    """
    Build Employment Blocks.

    One employment may contain:
        - Multiple projects
        - Multiple project durations
        - Multiple project roles

    Returns

    [
        employment1_blocks,
        employment2_blocks,
        ...
    ]
    """

    employment_blocks = []

    current = []

    inside_employment = False

    found_responsibility = False

    i = 0

    while i < len(blocks):

        block = blocks[i]

        current.append(block)

        # -----------------------------
        # Detect header using next lines
        # -----------------------------

        window = []

        for j in range(i, min(i + 5, len(blocks))):

            window.append(blocks[j].text)

        header = detect_header(
            window,
            inside_employment=inside_employment
        )

        # -----------------------------
        # Employment starts
        # -----------------------------

        if (
            header.header_type == "EMPLOYMENT"
            and inside_employment
            and found_responsibility
        ):

            current.pop()

            employment_blocks.append(current)

            current = [block]

            found_responsibility = False

        if header.header_type == "EMPLOYMENT":

            inside_employment = True

        # -----------------------------
        # Responsibility Detection
        # -----------------------------

        text = block.text.strip()

        if (
            text.startswith(("•", "-", "*", "▪", "◦"))
            or getattr(block, "bullet", False)
        ):

            found_responsibility = True

        i += 1

    if current:

        employment_blocks.append(current)

    return employment_blocks
