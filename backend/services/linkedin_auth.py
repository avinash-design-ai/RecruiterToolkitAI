import json
from pathlib import Path


CONFIG_DIR = Path("config")
CONFIG_DIR.mkdir(exist_ok=True)

CREDENTIAL_FILE = CONFIG_DIR / "linkedin_credentials.json"


class LinkedInAuth:

    @staticmethod
    def is_configured():

        return CREDENTIAL_FILE.exists()

    @staticmethod
    def save(username, password):

        data = {
            "username": username,
            "password": password
        }

        with open(CREDENTIAL_FILE, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def load():

        if not CREDENTIAL_FILE.exists():
            return None

        with open(CREDENTIAL_FILE, "r") as f:
            return json.load(f)

    @staticmethod
    def delete():

        if CREDENTIAL_FILE.exists():
            CREDENTIAL_FILE.unlink()
