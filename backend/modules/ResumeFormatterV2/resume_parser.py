from engine.document_reader import read_document
from engine.ai_structure_parser import analyze_resume_structure
from engine.resume_builder import build_resume


def parse_resume(file_path):

    print("========== PARSE RESUME ==========")

    # ----------------------------------------
    # Read Resume
    # ----------------------------------------

    print("Reading document...")

    document = read_document(file_path)

    print(
        f"Done reading "
        f"({len(document.blocks)} blocks)"
    )

    # ----------------------------------------
    # ONE AI CALL
    #
    # Analyze complete resume structure.
    # This replaces:
    #
    # map_sections()
    # detect_header()
    # per-job AI repair
    # ----------------------------------------

    print("Analyzing resume structure...")

    structure = analyze_resume_structure(
        document
    )

    print("Done analyzing resume structure")

    # ----------------------------------------
    # Build Resume
    #
    # structure is a DICTIONARY returned
    # by ai_structure_parser.py
    # ----------------------------------------

    print("Building resume...")

    resume = build_resume(
        document,
        structure
    )

    print("Resume built successfully")

    print("========== END PARSE ==========")

    return resume
