from engine.document_reader import read_document
from engine.rule_structure_parser import analyze_resume_structure
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
    # RULE-BASED STRUCTURE ANALYSIS
    #
    # No Ollama / AI dependency.
    # ----------------------------------------

    print(
        "Analyzing resume structure "
        "using rule-based parser..."
    )

    structure = analyze_resume_structure(
        document
    )

    print(
        "Done analyzing resume structure"
    )

    # ----------------------------------------
    # Build Resume
    # ----------------------------------------

    print("Building resume...")

    resume = build_resume(
        document,
        structure
    )

    print(
        "Resume built successfully"
    )

    print(
        "========== END PARSE =========="
    )

    return resume