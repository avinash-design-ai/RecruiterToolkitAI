from pathlib import Path

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

    def __init__(
        self,
        profile="default",
        storage_state=None,
    ):

        log.info("Starting Playwright...")

        self.playwright = sync_playwright().start()

        # Session/Profile Manager
        self.session = SessionManager(profile)

        # -------------------------------------------------
        # Storage State Mode
        # -------------------------------------------------

        if storage_state:

            storage_path = Path(storage_state)

            if not storage_path.exists():
                raise FileNotFoundError(
                    f"Storage state file not found: {storage_path}"
                )

            log.info(
                f"Loading Playwright storage state: {storage_path}"
            )

            self.browser = (
                self.playwright.chromium.launch(
                    headless=HEADLESS,
                    slow_mo=SLOW_MO,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-software-rasterizer",
                        "--disable-extensions",
                        "--disable-background-networking",
                        "--disable-background-timer-throttling",
                        "--disable-renderer-backgrounding",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-features=Translate,BackForwardCache",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ],
                )
                .new_context(
                    storage_state=str(storage_path),
                    viewport={
                        "width": WINDOW_WIDTH,
                        "height": WINDOW_HEIGHT,
                    },
                    accept_downloads=True,
                )
            )

            log.success(
                "Browser started successfully (Storage State Mode)"
            )

        # -------------------------------------------------
        # Existing Persistent Profile Mode
        # -------------------------------------------------

        else:

            self.browser = (
                self.playwright.chromium.launch_persistent_context(
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
                        "--disable-software-rasterizer",
                        "--disable-extensions",
                        "--disable-background-networking",
                        "--disable-background-timer-throttling",
                        "--disable-renderer-backgrounding",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-features=Translate,BackForwardCache",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ],
                )
            )

            log.success(
                f"Browser started successfully (Profile: {profile})"
            )

        # -------------------------------------------------
        # Browser crash diagnostics
        # -------------------------------------------------

        self.browser.on(
            "close",
            lambda: log.error(
                "PLAYWRIGHT BROWSER CONTEXT CLOSED"
            )
        )

        # Default timeout
        self.browser.set_default_timeout(TIMEOUT)

    def new_page(self):

        page = self.browser.new_page()

        page.on(
            "crash",
            lambda crashed_page: log.error(
                f"PLAYWRIGHT PAGE CRASHED: {crashed_page.url}"
            )
        )

        page.on(
            "close",
            lambda closed_page: log.error(
                f"PLAYWRIGHT PAGE CLOSED: {closed_page.url}"
            )
        )

        log.info(
            f"New Playwright page created: {page.url}"
        )

        return page

    def pages(self):
        """
        Returns all open pages.
        """
        return self.browser.pages

    def new_tab(self):

        page = self.browser.new_page()

        page.on(
            "crash",
            lambda crashed_page: log.error(
                f"PLAYWRIGHT TAB CRASHED: {crashed_page.url}"
            )
        )

        page.on(
            "close",
            lambda closed_page: log.error(
                f"PLAYWRIGHT TAB CLOSED: {closed_page.url}"
            )
        )

        return page

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

        self.browser.clear_cookies()

        log.info("Cookies cleared.")

    def storage_state(self, path="storage_state.json"):

        self.browser.storage_state(
            path=path
        )

        log.success(
            f"Storage state saved -> {path}"
        )