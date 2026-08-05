from playwright.sync_api import sync_playwright

from automation.config import (
    HEADLESS,
    SLOW_MO,
    TIMEOUT,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
)

from automation.logger import log
from automation.session import SessionManager


class BrowserManager:

    def __init__(self, profile="default"):

        log.info("Starting Playwright...")

        self.playwright = sync_playwright().start()

        # Session/Profile Manager
        self.session = SessionManager(profile)

        # Persistent Browser Context
        self.browser = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.session.get_profile_path(),
            headless=HEADLESS,
            slow_mo=SLOW_MO,
            viewport={
                "width": WINDOW_WIDTH,
                "height": WINDOW_HEIGHT,
            },
            accept_downloads=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        # Default timeout
        self.browser.set_default_timeout(TIMEOUT)

        log.success(f"Browser started successfully (Profile: {profile})")

    def new_page(self):
        """
        Returns the first available page.
        Creates one if none exist.
        """
        if self.browser.pages:
            return self.browser.pages[0]

        return self.browser.new_page()

    def pages(self):
        """
        Returns all open pages.
        """
        return self.browser.pages

    def new_tab(self):
        """
        Opens a new browser tab.
        """
        return self.browser.new_page()

    def close(self):

        try:

            log.info("Closing browser...")

            self.browser.close()

        except Exception:
            pass

        try:

            self.playwright.stop()

        except Exception:
            pass

        log.success("Browser closed.")

    def context(self):
        """
        Returns Playwright BrowserContext.
        """
        return self.browser

    def cookies(self):
        """
        Returns current cookies.
        """
        return self.browser.cookies()

    def clear_cookies(self):
        """
        Clears all cookies.
        """
        self.browser.clear_cookies()
        log.info("Cookies cleared.")

    def storage_state(self, path="storage_state.json"):
        """
        Saves storage state.
        """
        self.browser.storage_state(path=path)
        log.success(f"Storage state saved -> {path}")
