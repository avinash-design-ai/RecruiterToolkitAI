import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

with open(ROOT_DIR / "config.json", "r") as f:
    settings = json.load(f)

HEADLESS = settings["headless"]
SLOW_MO = settings["slow_mo"]
TIMEOUT = settings["timeout"]
DEFAULT_PROFILE = settings["profile"]

WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900

EXPORT_DIR = ROOT_DIR / "exports"
SCREENSHOT_DIR = ROOT_DIR / "screenshots"
LOG_DIR = ROOT_DIR / "logs"
PROFILE_DIR = ROOT_DIR / "profile"

for folder in [
    EXPORT_DIR,
    SCREENSHOT_DIR,
    LOG_DIR,
    PROFILE_DIR,
]:
    folder.mkdir(exist_ok=True)
