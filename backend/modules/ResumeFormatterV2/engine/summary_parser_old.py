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

def parse_summary(
    blocks,
    sections
):

    summary = []

    if not sections.summary:

        return summary

    for block in sections.summary:

        text = block.text.strip()

        if text:

            summary.append(text)

    return summary
