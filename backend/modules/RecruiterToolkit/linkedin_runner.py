import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from automation.search_controller import reset
from automation.browser import BrowserManager
from workflows.search_workflow import SearchWorkflow


def run_linkedin(
    company,
    location,
    max_profiles=250,
    profile="default"
):

    reset()

    browser = BrowserManager(profile=profile)

    try:

        # -------------------------------------
        # Open browser
        # -------------------------------------

        page = browser.new_page()

        page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded"
        )

        page.wait_for_timeout(3000)

        current = page.url.lower()

        print("Current URL:", current)

        # -------------------------------------
        # Login required?
        # -------------------------------------

        if (
            "login" in current
            or "checkpoint" in current
            or "logout" in current
        ):

            print("=" * 50)
            print("LOGIN REQUIRED")
            print("Please login to LinkedIn...")
            print("=" * 50)

            page.wait_for_url(
                "**/feed/**",
                timeout=300000      # 5 minutes
            )

            print("LinkedIn login completed.")

            # Give LinkedIn a moment to finish loading
            page.wait_for_timeout(3000)

            # Always return to feed after login
            page.goto(
                "https://www.linkedin.com/feed/",
                wait_until="domcontentloaded"
            )

            page.wait_for_timeout(3000)

            print("Continuing search...")

        # -------------------------------------
        # Final authentication check
        # -------------------------------------

        current = page.url.lower()

        print("Current URL:", current)

        if (
            "login" in current
            or "checkpoint" in current
            or "logout" in current
        ):
            raise Exception(
                "LinkedIn authentication failed."
            )

        # -------------------------------------
        # Run LinkedIn search
        # -------------------------------------

        workflow = SearchWorkflow(browser)

        result = workflow.run(
            company=company,
            location=location,
            max_profiles=max_profiles
        )

        return {

            "success": True,

            "count": result["count"],

            "filename": os.path.basename(
                result["csv"]
            )

        }

    finally:

        browser.close()
