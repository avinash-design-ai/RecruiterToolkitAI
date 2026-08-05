import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
    
from pages.login_page import LoginPage
from automation.search_controller import reset
from automation.browser import BrowserManager
from workflows.search_workflow import SearchWorkflow


def run_linkedin(
    company,
    location,
    max_profiles=250,
    profile="default",
    linkedin_email=None,
    linkedin_password=None
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

        if "login" in current:

            print("=" * 50)
            print("LINKEDIN LOGIN REQUIRED")
            print("=" * 50)

            if not linkedin_email or not linkedin_password:

                return {

                    "success": False,

                    "login_required": True,

                    "message": "LinkedIn credentials required."

                }

            print("Logging into LinkedIn...")

            login = LoginPage(page)

            login.login(

                linkedin_email,

                linkedin_password

            )

            page.wait_for_url(

                "**/feed/**",

                timeout=60000

            )

            print("LinkedIn login successful.")

            page.wait_for_timeout(3000)

            print("Continuing search...")

            # Immediately remove password from memory

            linkedin_password = None

            del linkedin_password

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
