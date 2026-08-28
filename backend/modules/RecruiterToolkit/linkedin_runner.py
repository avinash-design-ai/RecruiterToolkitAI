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
    Determine whether LinkedIn has reached an authenticated page.

    URL and title are treated as the primary authentication signals.
    DOM selectors are used only as additional confirmation.

    IMPORTANT:
    Do not reject an authenticated /feed/ page merely because
    LinkedIn changed its DOM selectors.
    """

    try:
        url = page.url.lower()

        # -------------------------------------------------
        # Never treat authentication / challenge pages as
        # authenticated.
        # -------------------------------------------------

        if _is_login_or_verification_page(page):
            return False

        # -------------------------------------------------
        # Strong authenticated URL signals
        # -------------------------------------------------

        authenticated_url_patterns = (
            "linkedin.com/feed",
            "linkedin.com/search",
            "linkedin.com/in/",
            "linkedin.com/company/",
            "linkedin.com/jobs/",
            "linkedin.com/mynetwork",
            "linkedin.com/messaging",
            "linkedin.com/notifications",
        )

        if any(
            pattern in url
            for pattern in authenticated_url_patterns
        ):
            print(
                "Authenticated LinkedIn URL detected:",
                page.url,
            )

            return True

        # -------------------------------------------------
        # Additional DOM confirmation for pages where the
        # URL alone is not enough.
        # -------------------------------------------------

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

                    print(
                        "Authenticated LinkedIn UI detected:",
                        selector,
                    )

                    return True

            except Exception:
                continue

        return False

    except Exception as ex:

        print(
            "LinkedIn authentication detection error:",
            repr(ex),
        )

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
    Wait for LinkedIn authentication to complete.

    Returns immediately once an authenticated LinkedIn URL
    is detected.
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

        # -------------------------------------------------
        # AUTHENTICATION STATE DIAGNOSTIC
        # -------------------------------------------------

        if current_url != last_url:

            try:
                print("=" * 60)
                print("AUTHENTICATION STATE DIAGNOSTIC")
                print("=" * 60)
                print("URL:", current_url)
                print("TITLE:", page.title())

                print(
                    "LOGIN PAGE:",
                    "linkedin.com/login" in current_url_lower
                )

                print(
                    "CHECKPOINT:",
                    "checkpoint" in current_url_lower
                )

                print(
                    "CHALLENGE:",
                    "challenge" in current_url_lower
                )

                try:
                    body_text = page.locator("body").inner_text(
                        timeout=3000
                    )

                    diagnostic_text = (
                        body_text
                        .replace("\\n", " ")
                        .strip()
                    )

                    print(
                        "PAGE TEXT:",
                        diagnostic_text[:1000]
                    )

                except Exception as ex:
                    print(
                        "PAGE TEXT ERROR:",
                        repr(ex)
                    )

                print("=" * 60)

            except Exception as ex:
                print(
                    "AUTHENTICATION DIAGNOSTIC ERROR:",
                    repr(ex)
                )

        if current_url != last_url:

            print(
                "LinkedIn URL:",
                current_url
            )

            print(
                "LinkedIn title:",
                page.title()
            )

            last_url = current_url

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if _is_linkedin_authenticated(page):

            print(
                "=" * 60
            )

            print(
                "LINKEDIN AUTHENTICATION CONFIRMED"
            )

            print(
                "Authenticated URL:",
                page.url
            )

            print(
                "Authenticated title:",
                page.title()
            )

            print(
                "=" * 60
            )

            return {
                "authenticated": True,
                "verification_required": False,
                "timeout": False,
            }

        # -------------------------------------------------
        # CHECKPOINT / CHALLENGE
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Still on login page
        #
        # IMPORTANT:
        # Remaining on /login/ does NOT prove that LinkedIn
        # requires verification.
        #
        # It may simply mean:
        #   - login failed
        #   - credentials were rejected
        #   - LinkedIn has not completed processing
        #   - the page is still loading
        #
        # Do NOT classify this as verification here.
        # Continue waiting until timeout.
        # -------------------------------------------------

        if (
            "linkedin.com/login" in current_url_lower
            or "linkedin.com/uas/login" in current_url_lower
            or "linkedin.com/uas/signin" in current_url_lower
        ):

            if elapsed % 10 == 0:

                print(
                    "LinkedIn still on login page; "
                    "verification has NOT been confirmed."
                )

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
            # Credentials are supplied by the webpage.
            #
            # IMPORTANT:
            # Do NOT wait for manual authentication here.
            # The browser must first receive the credentials.
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
            # Submit credentials through Playwright
            # -------------------------------------------------

            print(
                "Logging into LinkedIn with supplied credentials..."
            )

            login = LoginPage(page)

            login.login(
                linkedin_email,
                linkedin_password
            )

            print(
                "LinkedIn login form submitted."
            )

            # -------------------------------------------------
            # Wait for LinkedIn authentication result
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
            # Verification / challenge required
            #
            # Keep the SAME browser and SAME page alive.
            # The webpage will submit the verification code
            # through /linkedin/verify.
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

                print("=" * 60)
                print("LINKEDIN VERIFICATION SESSION ACTIVE")
                print("=" * 60)
                print(
                    "Session ID:",
                    session_id
                )

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
        # Render must NOT run SearchWorkflow.
        #
        # For V2, export the authenticated Playwright storage
        # state and return it to the FastAPI route.
        #
        # The FastAPI route is responsible for:
        #
        #   1. validating storage state
        #   2. updating GitHub secret
        #   3. dispatching GitHub Actions
        #
        # The storage state is NEVER returned to the browser UI.
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
                "Exporting authenticated LinkedIn storage state..."
            )

            print(
                "BEFORE storage_state()..."
            )

            try:

                storage_state = (
                    page.context.storage_state()
                )

                print(
                    "AFTER storage_state()..."
                )

            except Exception as ex:

                print(
                    "STORAGE_STATE ERROR:",
                    repr(ex)
                )

                traceback.print_exc()

                raise

            if not isinstance(
                storage_state,
                dict
            ):

                raise RuntimeError(
                    "Playwright returned an invalid "
                    "LinkedIn storage state."
                )

            cookies = storage_state.get(
                "cookies",
                []
            )

            if not isinstance(
                cookies,
                list
            ):

                raise RuntimeError(
                    "LinkedIn storage state cookies "
                    "are invalid."
                )

            if not cookies:

                raise RuntimeError(
                    "LinkedIn storage state contains "
                    "no cookies."
                )

            print(
                "V2 storage state exported successfully."
            )

            print(
                "V2 storage cookies:",
                len(cookies)
            )

            return {
                "success": True,
                "authenticated": True,
                "authentication_only": True,
                "storage_state": storage_state,
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
