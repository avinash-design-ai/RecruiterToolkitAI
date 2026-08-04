"""
Recruiter's Toolkit Configuration
"""

# --------------------------------------------------
# FLAG Configuration
# --------------------------------------------------

WAGE_YEAR = "7/2026 - 6/2027"

HEADLESS = False

SLOW_MO = 300

SHORT_WAIT = 1000

MEDIUM_WAIT = 2000

LONG_WAIT = 3000

# --------------------------------------------------
# Folder Configuration
# --------------------------------------------------

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_FOLDER = os.path.join(BASE_DIR, "input")

OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")

LOG_FOLDER = os.path.join(BASE_DIR, "logs")

# --------------------------------------------------
# Output
# --------------------------------------------------

OUTPUT_SUFFIX = "_Updated"

# --------------------------------------------------
# Retry
# --------------------------------------------------

MAX_RETRIES = 3
