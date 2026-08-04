import os

from docling.document_converter import DocumentConverter

converter = DocumentConverter()

folder = r"D:\Avinash\avi itech\myresumes\test resumes"

files = [
    f for f in os.listdir(folder)
    if f.lower().endswith((".pdf", ".docx"))
]

if not files:
    raise Exception("No resumes found.")

resume = os.path.join(folder, files[0])

print("Reading:", resume)

result = converter.convert(resume)

print("=" * 80)
print(result.document.export_to_markdown())
print("=" * 80)
