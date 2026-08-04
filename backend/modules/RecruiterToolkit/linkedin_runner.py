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

        page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded"
        )

        page.wait_for_timeout(5000)

        print("Current URL:", page.url)

        # -----------------------------
        # Check login
        # -----------------------------
        if "login" in page.url or "checkpoint" in page.url:

            return {
                "success": False,
                "login_required": True,
                "message": "Authentication required before LinkedIn search."
            }

        workflow = SearchWorkflow(browser)

        result = workflow.run(
            company=company,
            location=location,
            max_profiles=max_profiles
        )

        return {
            "success": True,
            "count": result["count"],
            "filename": os.path.basename(result["csv"])
        }
        
    finally:

        browser.close()
