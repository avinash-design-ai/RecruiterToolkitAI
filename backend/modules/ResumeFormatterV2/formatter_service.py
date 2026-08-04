import sys
from pathlib import Path

# ---------------------------------------------------------
# Add ResumeFormatterV2 folder to Python path
# ---------------------------------------------------------

CURRENT_DIR = Path(__file__).resolve().parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# ---------------------------------------------------------
# Existing Formatter Imports
# (Leave ResumeFormatterV2 untouched)
# ---------------------------------------------------------

from resume_parser import parse_resume
from engine.word_generator import generate_resume


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

TEMPLATE = CURRENT_DIR / "Templates" / "SmartWorks_Template.docx"

OUTPUT_FOLDER = Path("uploads/output")


# ---------------------------------------------------------
# Main Formatter
# ---------------------------------------------------------

def format_resume(input_file: str):

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    input_path = Path(input_file)

    output_file = OUTPUT_FOLDER / (
        f"SmartWorks_{input_path.stem}.docx"
    )

    print("=" * 60)
    print("Resume Formatter Started")
    print("=" * 60)

    resume = parse_resume(str(input_path))

    generate_resume(
        resume,
        str(TEMPLATE),
        str(output_file)
    )

    print("=" * 60)
    print("Resume Formatter Completed")
    print("=" * 60)

    return str(output_file)
