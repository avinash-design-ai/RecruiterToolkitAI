from knowledge_base import (
    SECTION_HEADERS,
    normalize,
    is_heading
)


class SectionParser:

    def __init__(self):

        pass

    # -------------------------------------------------------
    # Extract Resume Sections
    # -------------------------------------------------------

    def extract(self, text):

        sections = {}

        current_section = None

        buffer = []

        lines = text.splitlines()

        for line in lines:

            value = line.strip()

            if not value:

                continue

            heading = is_heading(value)

            # ----------------------------------------
            # Heading on separate line
            # ----------------------------------------

            if heading:

                if current_section:

                    sections[current_section] = "\n".join(buffer).strip()

                current_section = heading

                buffer = []

                continue

            # ----------------------------------------
            # Heading + content on same line
            # Example:
            # Summary: Experienced Developer...
            # ----------------------------------------

            found_inline = False

            for section, headings in SECTION_HEADERS.items():

                for h in headings:

                    if normalize(value).startswith(h):

                        current_section = section

                        content = value[len(h):]

                        content = content.lstrip(":").strip()

                        buffer = []

                        if content:

                            buffer.append(content)

                        found_inline = True

                        break

                if found_inline:

                    break

            if found_inline:

                continue

            # ----------------------------------------

            if current_section:

                buffer.append(value)

        if current_section:

            sections[current_section] = "\n".join(buffer).strip()

        return sections

    # -------------------------------------------------------
    # Debug
    # -------------------------------------------------------

    def print_sections(self, sections):

        print("\n==============================")

        print("SECTIONS FOUND")

        print("==============================\n")

        for key, value in sections.items():

            print(f"{key.upper()}")

            print("-" * 40)

            print(value[:400])

            print()

        print("==============================")
