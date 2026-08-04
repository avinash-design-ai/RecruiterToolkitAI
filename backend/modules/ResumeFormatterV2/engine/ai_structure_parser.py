import json
import re
import time

from ollama import chat


MODEL = "phi4-mini:latest"


# ==========================================================
# JSON SCHEMA
# ==========================================================

SCHEMA = {

    "type": "object",

    "properties": {

        "summary_blocks": {
            "type": "array",
            "items": {
                "type": "integer"
            }
        },

        "skills_blocks": {
            "type": "array",
            "items": {
                "type": "integer"
            }
        },

        "education_blocks": {
            "type": "array",
            "items": {
                "type": "integer"
            }
        },

        "certification_blocks": {
            "type": "array",
            "items": {
                "type": "integer"
            }
        },

        "experience": {

            "type": "array",

            "items": {

                "type": "object",

                "properties": {

                    "start_block": {
                        "type": "integer"
                    },

                    "end_block": {
                        "type": "integer"
                    },

                    "employer": {
                        "type": "string"
                    },

                    "client": {
                        "type": "string"
                    },

                    "role": {
                        "type": "string"
                    },

                    "location": {
                        "type": "string"
                    },

                    "duration": {
                        "type": "string"
                    }

                },

                "required": [
                    "start_block",
                    "end_block",
                    "employer",
                    "client",
                    "role",
                    "location",
                    "duration"
                ]
            }
        }
    },

    "required": [
        "summary_blocks",
        "skills_blocks",
        "education_blocks",
        "certification_blocks",
        "experience"
    ]
}


# ==========================================================
# SYSTEM PROMPT
# ==========================================================

PROMPT = """
You are analyzing the structure of a professional resume.

The resume is provided as numbered document blocks.

Your task is NOT to rewrite the resume.

Your task is to identify the structure of the resume.

Identify:

1. Professional summary blocks
2. Technical skills blocks
3. Education blocks
4. Certification blocks
5. Employment entries

For each employment entry determine:

- start_block
- end_block
- employer
- client
- role
- location
- duration

IMPORTANT:

Resume layouts vary significantly.

Information may appear:

- on one line
- across several lines
- separated by commas
- separated by pipes
- separated by dashes
- inside tables
- with labels
- without labels
- in different orders

Do NOT assume:

- the first company-like name is always the employer
- text before a comma is always the employer
- text after a comma is always the location
- every employment has a client
- every employment has an employer
- every employment has a role
- every employment has a location
- every employment has a duration

Employer and client are different concepts.

A resume may contain:

- employer only
- client only
- employer and client
- implementation partner and client
- multiple projects under one employment

Project names are NOT employers unless the source text clearly indicates
that they are the employing organization.

Use surrounding context to determine relationships.

Employment boundaries are especially important.

A company/location line may belong with a role/date line immediately
following it.

A role/date line may belong with a company line immediately preceding it.

Do not split these into separate employments when they clearly describe
one employment.

Responsibilities belong to the employment entry above them until the
next employment begins.

Do not treat responsibility sentences as:

- employer
- client
- role
- location
- duration

Do not invent information.

If a field cannot be determined, return an empty string.

start_block and end_block must reference the numbered source blocks.

end_block is inclusive.

Return ONLY valid JSON matching the required schema.
"""


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


def build_indexed_document(document):

    lines = []

    for index, block in enumerate(
        document.blocks
    ):

        text = clean_text(
            block.text
        )

        if not text:

            continue

        lines.append(
            f"[{index}] {text}"
        )

    return "\n".join(lines)


def valid_index(
    value,
    total
):

    return (
        isinstance(value, int)
        and 0 <= value < total
    )


# ==========================================================
# VALIDATION
# ==========================================================

def validate_structure(
    data,
    document
):

    total = len(
        document.blocks
    )

    result = {

        "summary_blocks": [],

        "skills_blocks": [],

        "education_blocks": [],

        "certification_blocks": [],

        "experience": []

    }

    # ------------------------------------------------------
    # Validate section block indexes
    # ------------------------------------------------------

    for key in [

        "summary_blocks",

        "skills_blocks",

        "education_blocks",

        "certification_blocks"

    ]:

        values = data.get(
            key,
            []
        )

        seen = set()

        for value in values:

            if not valid_index(
                value,
                total
            ):

                continue

            if value in seen:

                continue

            seen.add(value)

            result[key].append(
                value
            )

        result[key].sort()

    # ------------------------------------------------------
    # Validate employment entries
    # ------------------------------------------------------

    for item in data.get(
        "experience",
        []
    ):

        start = item.get(
            "start_block"
        )

        end = item.get(
            "end_block"
        )

        if not valid_index(
            start,
            total
        ):

            continue

        if not valid_index(
            end,
            total
        ):

            continue

        if end < start:

            start, end = end, start

        employer = clean_text(
            item.get(
                "employer",
                ""
            )
        )

        client = clean_text(
            item.get(
                "client",
                ""
            )
        )

        role = clean_text(
            item.get(
                "role",
                ""
            )
        )

        location = clean_text(
            item.get(
                "location",
                ""
            )
        )

        duration = clean_text(
            item.get(
                "duration",
                ""
            )
        )

        result["experience"].append({

            "start_block": start,

            "end_block": end,

            "employer": employer,

            "client": client,

            "role": role,

            "location": location,

            "duration": duration

        })

    result["experience"].sort(
        key=lambda item:
        item["start_block"]
    )

    return result


# ==========================================================
# MAIN AI CALL
# ==========================================================

def analyze_resume_structure(
    document
):

    indexed_document = (
        build_indexed_document(
            document
        )
    )

    print(
        "\n========== AI STRUCTURE INPUT =========="
    )

    print(
        f"Blocks sent: "
        f"{len(document.blocks)}"
    )

    print(
        "========================================\n"
    )

    start = time.perf_counter()

    response = chat(

        model=MODEL,

        think=False,

        format=SCHEMA,

        messages=[

            {

                "role": "system",

                "content": PROMPT

            },

            {

                "role": "user",

                "content":
                "Analyze this resume:\n\n"
                + indexed_document

            }

        ],

        options={

            "temperature": 0

        }

    )

    elapsed = (
        time.perf_counter()
        - start
    )

    print(
        f"AI structure call took "
        f"{elapsed:.2f} seconds"
    )

    try:

        data = json.loads(
            response.message.content
        )

    except Exception as ex:

        print(
            "AI STRUCTURE JSON ERROR:",
            ex
        )

        raise RuntimeError(
            "AI returned invalid resume "
            "structure JSON."
        )

    structure = validate_structure(
        data,
        document
    )

    print(
        "\n========== AI STRUCTURE RESULT =========="
    )

    print(
        json.dumps(
            structure,
            indent=2
        )
    )

    print(
        "=========================================\n"
    )

    return structure
