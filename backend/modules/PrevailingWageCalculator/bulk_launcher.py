import os
import sys

BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from modules.PrevailingWageCalculator.bulk_app import main


if __name__ == "__main__":
    main()