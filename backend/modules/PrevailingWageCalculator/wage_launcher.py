import os
import sys

# Find the backend directory
BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

# Add backend to Python path
sys.path.insert(0, BACKEND_DIR)

from modules.PrevailingWageCalculator.app import main


if __name__ == "__main__":
    main()