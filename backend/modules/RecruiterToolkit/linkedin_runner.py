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
    profile="temp",
    linkedin_email=None,
    linkedin_password=None
):

    print("=" * 60)
    print("1 - run_linkedin() started")
    print("=" * 60)

    reset()

    print("2 - Stop controller reset")

    browser = BrowserManager(profile=profile)

    print("3 - BrowserManager created")

    try:

        # -------------------------------------------------
        # Open browser
        # -------------------------------------------------

        page = browser.new_page()

        print("4 - Browser page created")

        page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded"
        )

        print("5 - LinkedIn page opened")

        page.wait_for_timeout(3000)

        current = page.url.lower()

        print("Current URL:", current)

        print("=" * 60)
        print("TITLE :", page.title())
        print("URL   :", page.url)
        print("=" * 60)

        # -------------------------------------------------
        # Login
        # -------------------------------------------------

        if "login" in current:

            print("6 - Login required")

            if not linkedin_email or not linkedin_password:

                print("LinkedIn credentials missing")

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

            page.wait_for_timeout(3000)

            print("7 - Login successful")

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

        # -------------------------------------------------
        # Search Workflow
        # -------------------------------------------------

        print("=" * 60)
        print("8 - Creating SearchWorkflow")
        print("=" * 60)

        workflow = SearchWorkflow(browser)

        print("9 - Running workflow")

        result = workflow.run(

            company=company,

            location=location,

            max_profiles=max_profiles

        )

        print("=" * 60)
        print("10 - Workflow completed")
        print(result)
        print("=" * 60)

        if not result:

            return {

                "success": False,

                "message": "Workflow returned no data."

            }

        if isinstance(result, list):

            return {

                "success": False,

                "message": "Workflow returned an unexpected list."

            }

        return {

            "success": True,

            "count": result.get("count", 0),

            "filename": os.path.basename(

                result.get("csv", "")

            )

        }

    except Exception as ex:

        import traceback

        print("=" * 60)
        print("LINKEDIN RUNNER EXCEPTION")
        print("=" * 60)

        traceback.print_exc()

        return {

            "success": False,

            "message": str(ex)

        }

    finally:

        print("11 - Closing browser")

        browser.close()

        print("12 - Browser closed")
