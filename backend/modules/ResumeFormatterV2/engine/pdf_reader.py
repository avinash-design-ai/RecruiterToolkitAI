import pdfplumber

from engine.docx_reader import (
    ResumeDocument,
    ParagraphBlock
)


def read_pdf(file_path):

    resume = ResumeDocument()

    with pdfplumber.open(file_path) as pdf:

        for page in pdf.pages:

            text = page.extract_text()

            if not text:
                continue

            for line in text.splitlines():

                line = line.strip()

                if not line:
                    continue

                bullet = False

                if line.startswith((
                    "•",
                    "-",
                    "*",
                    "▪",
                    "◦"
                )):

                    bullet = True

                    line = line.lstrip(
                        "•-*▪◦ "
                    ).strip()

                resume.add(

                    ParagraphBlock(

                        text=line,

                        style="Paragraph",

                        bullet=bullet,

                        bold=False,

                        italic=False,

                        table=False

                    )

                )

    return resume
