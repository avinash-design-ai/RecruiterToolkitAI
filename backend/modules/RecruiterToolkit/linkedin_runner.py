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

        page = browser.new_page()

        page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded"
        )

        page.wait_for_timeout(5000)

        print("Current URL:", page.url)

        workflow = SearchWorkflow(browser)

        results = workflow.run(
            company=company,
            location=location,
            max_profiles=max_profiles
        )

        filename = f"{company}_{location}.csv".replace(" ", "_")

        return {
            "success": True,
            "count": len(results),
            "filename": filename
        }

    finally:

        browser.close()
