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

            print("=" * 60)
            print("WAITING AFTER LOGIN")
            print("=" * 60)

            print("Waiting for LinkedIn homepage...")

            page.wait_for_url(
                lambda url:
                    "linkedin.com/feed" in url
                    or "linkedin.com/search" in url
                    or "linkedin.com/company" in url,
                timeout=180000
            )

            print("LinkedIn login completed.")
            print("=" * 60)
            print("OPEN PAGES")
            print("=" * 60)

            for i, p in enumerate(browser.pages()):

                try:

                    print(f"PAGE {i}")
                    print("TITLE :", p.title())
                    print("URL   :", p.url)
                    print("-" * 50)

                except Exception as ex:

                    print(ex)

            print("=" * 60)
            print("CURRENT PAGE")
            print("=" * 60)

            print(page.title())
            print(page.url)

            page.wait_for_timeout(30000)

            print("=" * 60)
            print("AFTER 30 SECONDS")
            print("=" * 60)

            for i, p in enumerate(browser.pages()):

                try:

                    print(f"PAGE {i}")
                    print("TITLE :", p.title())
                    print("URL   :", p.url)
                    print("-" * 60)

                    print("BUTTONS")

                    buttons = p.locator("button")

                    print("Button Count:", buttons.count())

                    for j in range(buttons.count()):

                        try:

                            btn = buttons.nth(j)

                            print(
                                j,
                                btn.inner_text(),
                                btn.is_visible()
                            )

                        except Exception:
                            pass

                    print("-" * 60)

                    print("INPUTS")

                    inputs = p.locator("input")

                    print("Input Count:", inputs.count())

                    for j in range(inputs.count()):

                        try:

                            inp = inputs.nth(j)

                            print(
                                j,
                                inp.get_attribute("type"),
                                inp.get_attribute("name"),
                                inp.get_attribute("value"),
                                inp.is_visible()
                            )

                        except Exception:
                            pass

                    print("-" * 60)

                    print("LINKS")

                    links = p.locator("a")

                    print("Link Count:", links.count())

                    for j in range(min(10, links.count())):

                        try:

                            a = links.nth(j)

                            print(
                                j,
                                a.inner_text(),
                                a.get_attribute("href")
                            )

                        except Exception:
                            pass

                except Exception as ex:

                    print(ex)

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

        workflow = SearchWorkflow(page)

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
