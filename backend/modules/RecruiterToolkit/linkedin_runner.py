import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from pages.login_page import LoginPage

from automation.search_controller import reset

from automation.browser import BrowserManager

from workflows.search_workflow import SearchWorkflow

from automation.active_sessions import (
    create_session,
    remove_session,
)


def _is_linkedin_authenticated(page):
    """
    Confirm that LinkedIn has reached a real authenticated page.
    URL-only detection is intentionally supplemented with page checks.
    """

    try:
        url = page.url.lower()

        authenticated_urls = (
            "linkedin.com/feed",
            "linkedin.com/search",
            "linkedin.com/in/",
            "linkedin.com/company/",
            "linkedin.com/jobs/",
            "linkedin.com/mynetwork",
            "linkedin.com/messaging",
            "linkedin.com/notifications",
        )

        if not any(
            authenticated_url in url
            for authenticated_url in authenticated_urls
        ):
            return False

        # Never consider login/checkpoint/challenge pages authenticated.
        if _is_login_or_verification_page(page):
            return False

        # Give LinkedIn's client-side page a moment to settle.
        try:
            page.wait_for_timeout(1500)
        except Exception:
            pass

        # Look for authenticated LinkedIn UI.
        authenticated_selectors = [
            "nav.global-nav",
            "header.global-nav",
            "[data-test-global-nav-primary-link='feed']",
            "a[href*='/feed/']",
            "a[href*='/mynetwork/']",
            "a[href*='/messaging/']",
            "button[aria-label*='Me']",
            "button[aria-label*='Account']",
        ]

        for selector in authenticated_selectors:
            try:
                locator = page.locator(selector).first

                if locator.is_visible(timeout=1000):
                    return True

            except Exception:
                continue

        return False

    except Exception:
        return False

def _validate_exported_storage_state(page, storage_path):
    """
    Validate that the exported Playwright storage state can
    authenticate a completely fresh browser context.

    This is the critical test before sending the state to
    GitHub Actions.
    """

    print("=" * 60)
    print("VALIDATING EXPORTED LINKEDIN STORAGE STATE")
    print("=" * 60)

    test_context = None
    test_page = None

    try:

        browser = page.context.browser

        test_context = browser.new_context(
            storage_state=str(storage_path),
            viewport={
                "width": 1440,
                "height": 900,
            },
            accept_downloads=True,
        )

        test_page = test_context.new_page()

        print("Fresh validation context created.")

        test_page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        test_page.wait_for_timeout(5000)

        print(
            "Storage validation URL:",
            test_page.url,
        )

        print(
            "Storage validation title:",
            test_page.title(),
        )

        if _is_linkedin_authenticated(test_page):

            print("=" * 60)
            print("EXPORTED STORAGE STATE VALIDATED")
            print("=" * 60)

            return True

        print("=" * 60)
        print("EXPORTED STORAGE STATE FAILED VALIDATION")
        print("=" * 60)

        return False

    except Exception as ex:

        print(
            "Storage state validation error:",
            ex,
        )

        return False

    finally:

        try:

            if test_context:
                test_context.close()

        except Exception:
            pass

def _is_login_or_verification_page(page):
    """
    Determine whether LinkedIn is still requesting authentication,
    verification, challenge, or checkpoint.
    """

    try:
        url = page.url.lower()

    except Exception:
        return True

    authentication_urls = (
        "linkedin.com/login",
        "linkedin.com/checkpoint",
        "linkedin.com/challenge",
        "linkedin.com/uas/login",
        "linkedin.com/uas/signin",
    )

    for authentication_url in authentication_urls:

        if authentication_url in url:

            return True

    return False


def _wait_for_login_result(
    page,
    timeout_seconds=120
):
    """
    Wait for LinkedIn to either:

    1. Reach an authenticated page
    2. Remain on a verification/checkpoint page
    3. Remain on the login page
    """

    print("=" * 60)
    print("WAITING FOR LINKEDIN LOGIN RESULT")
    print("=" * 60)

    start_time = time.time()

    last_url = ""

    while True:

        elapsed = int(
            time.time() - start_time
        )

        if elapsed >= timeout_seconds:

            print(
                "Login wait timeout reached:",
                timeout_seconds,
                "seconds"
            )

            return {
                "authenticated": False,
                "verification_required": True,
                "timeout": True,
            }

        try:

            current_url = page.url

        except Exception:

            current_url = ""

        current_url_lower = current_url.lower()

        if current_url != last_url:

            print(
                "LinkedIn URL:",
                current_url
            )

            last_url = current_url

        # -------------------------------------------------
        # Successful authentication
        # -------------------------------------------------

        if _is_linkedin_authenticated(page):

            print(
                "LinkedIn authenticated page detected."
            )

            return {
                "authenticated": True,
                "verification_required": False,
                "timeout": False,
            }

        # -------------------------------------------------
        # Login / checkpoint / challenge
        # -------------------------------------------------

        if _is_login_or_verification_page(page):

            if (
                "checkpoint" in current_url_lower
                or "challenge" in current_url_lower
            ):

                print(
                    "LinkedIn verification/challenge detected."
                )

                return {
                    "authenticated": False,
                    "verification_required": True,
                    "timeout": False,
                }

            if (
                "login" in current_url_lower
                or "signin" in current_url_lower
            ):

                # Give LinkedIn time to finish navigation
                # before declaring verification required.

                if elapsed >= 15:

                    print(
                        "LinkedIn is still requesting authentication."
                    )

                    return {
                        "authenticated": False,
                        "verification_required": True,
                        "timeout": False,
                    }

        page.wait_for_timeout(1000)


def _print_browser_state(browser):
    """
    Diagnostic information for all currently open pages.
    """

    print("=" * 60)
    print("OPEN PAGES")
    print("=" * 60)

    try:

        pages = browser.pages()

    except Exception as ex:

        print(
            "Unable to retrieve browser pages:",
            ex
        )

        return

    for i, p in enumerate(pages):

        try:

            print(
                f"PAGE {i}"
            )

            print(
                "TITLE :",
                p.title()
            )

            print(
                "URL   :",
                p.url
            )

            print(
                "-" * 60
            )

        except Exception as ex:

            print(ex)


def run_linkedin(
    company,
    location,
    max_profiles=250,
    profile="temp",
    linkedin_email=None,
    linkedin_password=None,
    authentication_only=False
):

    print("=" * 60)
    print("1 - run_linkedin() started")
    print("=" * 60)

    # -------------------------------------------------
    # Reset previous search controller state
    # -------------------------------------------------

    reset()

    print("2 - Stop controller reset")

    # -------------------------------------------------
    # Browser lifecycle
    # -------------------------------------------------

    keep_browser_alive = False

    browser = BrowserManager(
        profile=profile
    )

    print("3 - BrowserManager created")

    try:

        # -------------------------------------------------
        # Open browser
        # -------------------------------------------------

        page = browser.new_page()

        print(
            "4 - Browser page created"
        )

        page.goto(
            "https://www.linkedin.com/feed/",
            wait_until="domcontentloaded",
            timeout=60000
        )

        print(
            "5 - LinkedIn page opened"
        )

        page.wait_for_timeout(3000)

        current = page.url.lower()

        print(
            "Current URL:",
            current
        )

        print("=" * 60)
        print(
            "TITLE :",
            page.title()
        )
        print(
            "URL   :",
            page.url
        )
        print("=" * 60)

        # =================================================
        # LOGIN
        # =================================================

        if not _is_linkedin_authenticated(page):

            print(
                "6 - Login required"
            )

            # -------------------------------------------------
            # Authentication-only mode
            # -------------------------------------------------

            if authentication_only:

                print("=" * 60)
                print("6 - AUTHENTICATION-ONLY MODE")
                print("=" * 60)

                print(
                    "Manual LinkedIn authentication is required."
                )

                print(
                    "Waiting for LinkedIn authentication..."
                )

                login_result = _wait_for_login_result(
                    page,
                    timeout_seconds=300
                )

            else:

                # -------------------------------------------------
                # Credentials check
                # -------------------------------------------------

                if (
                    not linkedin_email
                    or not linkedin_password
                ):

                    print(
                        "LinkedIn credentials missing"
                    )

                    return {

                        "success": False,

                        "login_required": True,

                        "message":
                            "LinkedIn credentials required."

                    }

                # -------------------------------------------------
                # Login
                # -------------------------------------------------

                print(
                    "Logging into LinkedIn..."
                )

                login = LoginPage(page)

                login.login(
                    linkedin_email,
                    linkedin_password
                )

                print(
                    "Login form submitted."
                )

                # -------------------------------------------------
                # Wait for actual login result
                # -------------------------------------------------

                login_result = _wait_for_login_result(
                    page,
                    timeout_seconds=120
                )

            print("=" * 60)
            print("LOGIN RESULT")
            print("=" * 60)

            print(
                login_result
            )

            # -------------------------------------------------
            # Verification required
            # -------------------------------------------------

            if not login_result.get(
                "authenticated",
                False
            ):

                print(
                    "6A - LinkedIn verification required."
                )

                session_id = create_session(
                    browser,
                    page,
                    company,
                    location,
                    max_profiles,
                )

                keep_browser_alive = True

                return {

                    "success": False,

                    "verification_required": True,

                    "session_id": session_id,

                    "message":
                        "LinkedIn verification code required."

                }

            print(
                "LinkedIn login completed successfully."
            )

        else:

            print(
                "Existing LinkedIn session detected."
            )

        # =================================================
        # AUTHENTICATED SESSION CONFIRMATION
        # =================================================

        current = page.url.lower()

        print("=" * 60)
        print("AUTHENTICATED LINKEDIN SESSION")
        print("=" * 60)

        print(
            "Current URL:",
            page.url
        )

        print(
            "Page Title:",
            page.title()
        )

        # -------------------------------------------------
        # Final authentication safety check
        # -------------------------------------------------

        if not _is_linkedin_authenticated(page):

            if _is_login_or_verification_page(page):

                print(
                    "LinkedIn authentication is not complete."
                )

                session_id = create_session(
                    browser,
                    page,
                    company,
                    location,
                    max_profiles,
                )

                keep_browser_alive = True

                return {

                    "success": False,

                    "verification_required": True,

                    "session_id": session_id,

                    "message":
                        "LinkedIn authentication requires verification."

                }

            raise Exception(
                "LinkedIn authentication could not be confirmed."
            )

        # -------------------------------------------------
        # Diagnostic browser state
        # -------------------------------------------------

        _print_browser_state(
            browser
        )

        # =================================================
        # V2 AUTHENTICATION-ONLY MODE
        #
        # Render must NOT run the LinkedIn search.
        # The authenticated storage state is consumed
        # by GitHub Actions.
        # =================================================

        if authentication_only:

            print("=" * 60)
            print("V2 AUTHENTICATION COMPLETE")
            print("=" * 60)

            print(
                "Authenticated URL:",
                page.url
            )

            print(
                "Authenticated Title:",
                page.title()
            )

            print(
                "V2 authentication-only mode enabled."
            )

            return {
                "success": True,
                "authenticated": True,
                "authentication_only": True,
                "message":
                    "LinkedIn authentication completed."
            }

        # =================================================
        # SEARCH WORKFLOW
        # =================================================

        print("=" * 60)
        print("8 - Creating SearchWorkflow")
        print("=" * 60)

        workflow = SearchWorkflow(
            page
        )

        print("=" * 60)
        print("9 - Running workflow")
        print("=" * 60)

        result = workflow.run(

            company=company,

            location=location,

            max_profiles=max_profiles

        )

        # =================================================
        # WORKFLOW RESULT
        # =================================================

        print("=" * 60)
        print("10 - Workflow completed")
        print("=" * 60)

        print(
            result
        )

        # -------------------------------------------------
        # No result
        # -------------------------------------------------

        if not result:

            return {

                "success": False,

                "message":
                    "Workflow returned no data."

            }

        # -------------------------------------------------
        # Unexpected result
        # -------------------------------------------------

        if isinstance(
            result,
            list
        ):

            return {

                "success": False,

                "message":
                    "Workflow returned an unexpected list."

            }

        # -------------------------------------------------
        # Successful workflow
        # -------------------------------------------------

        csv_file = result.get(
            "csv",
            ""
        )

        return {

            "success": True,

            "count":
                result.get(
                    "count",
                    0
                ),

            "filename":
                os.path.basename(
                    csv_file
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

            "message":
                str(ex)

        }

    finally:

        # -------------------------------------------------
        # Browser lifecycle
        # -------------------------------------------------

        if not keep_browser_alive:

            print(
                "11 - Closing browser"
            )

            try:

                browser.close()

            except Exception as ex:

                print(
                    "Browser close error:",
                    ex
                )

            print(
                "12 - Browser closed"
            )

        else:

            print(
                "Browser kept alive for verification."
            )
