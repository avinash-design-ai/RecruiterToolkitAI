import os

from engine.docx_reader import read_docx
from engine.pdf_reader import read_pdf


def read_document(file_path):

    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".docx":
        return read_docx(file_path)

    if extension == ".pdf":
        return read_pdf(file_path)

    raise Exception(
        f"Unsupported file type: {extension}"
    )
