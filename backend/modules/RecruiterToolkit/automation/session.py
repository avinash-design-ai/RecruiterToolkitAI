from pathlib import Path
from automation.config import PROFILE_DIR
from automation.logger import log


class SessionManager:

    def __init__(self, profile="default"):
        self.profile = profile
        self.profile_path = PROFILE_DIR / profile

    def get_profile_path(self):
        self.profile_path.mkdir(parents=True, exist_ok=True)
        return str(self.profile_path)

    def exists(self):
        return self.profile_path.exists()

    def clear(self):
        import shutil

        if self.profile_path.exists():
            shutil.rmtree(self.profile_path)
            log.warning(f"Profile '{self.profile}' cleared.")
