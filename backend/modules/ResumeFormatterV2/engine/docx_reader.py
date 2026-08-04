from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


class ParagraphBlock:

    def __init__(
        self,
        text="",
        style="",
        bold=False,
        italic=False,
        bullet=False,
        table=False
    ):

        self.text = text.strip()

        self.style = style

        self.bold = bold

        self.italic = italic

        self.bullet = bullet

        self.table = table

    def __repr__(self):

        return self.text


class ResumeDocument:

    def __init__(self):

        self.blocks = []

    def add(self, block):

        if block.text:

            self.blocks.append(block)

    def get_text(self):

        return "\n".join(
            block.text
            for block in self.blocks
        )

    def __len__(self):

        return len(self.blocks)

    def __getitem__(self, index):

        return self.blocks[index]


# ----------------------------------------------------------
# Iterate document in actual reading order
# ----------------------------------------------------------

def iter_block_items(parent):

    parent_elm = parent.element.body

    for child in parent_elm.iterchildren():

        if child.tag.endswith("}p"):

            yield Paragraph(child, parent)

        elif child.tag.endswith("}tbl"):

            yield Table(child, parent)


# ----------------------------------------------------------
# Paragraph Reader
# ----------------------------------------------------------

def read_paragraph(para, resume):

    text = para.text.strip()

    if not text:

        return

    bold = False

    italic = False

    for run in para.runs:

        if run.bold:

            bold = True

        if run.italic:

            italic = True

    style = ""

    try:

        style = para.style.name

    except:

        pass

    bullet = False

    if style.lower().startswith("list"):

        bullet = True

    resume.add(

        ParagraphBlock(

            text=text,

            style=style,

            bold=bold,

            italic=italic,

            bullet=bullet,

            table=False

        )

    )


# ----------------------------------------------------------
# Table Reader
# ----------------------------------------------------------

def read_table(table, resume):

    for row in table.rows:

        values = []

        for cell in row.cells:

            txt = cell.text.strip()

            if txt:

                values.append(txt)

        if values:

            resume.add(

                ParagraphBlock(

                    text=" | ".join(values),

                    style="Table",

                    table=True

                )

            )


# ----------------------------------------------------------
# Main
# ----------------------------------------------------------

def read_docx(file_path):

    doc = Document(file_path)

    resume = ResumeDocument()

    for block in iter_block_items(doc):

        if isinstance(block, Paragraph):

            read_paragraph(

                block,

                resume

            )

        elif isinstance(block, Table):

            read_table(

                block,

                resume

            )

    return resume
