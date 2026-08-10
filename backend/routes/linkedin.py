import os
import traceback

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from models.linkedin import LinkedInRequest
from models.linkedin_verify import LinkedInVerifyRequest

from modules.RecruiterToolkit.linkedin_runner import run_linkedin

from automation.search_controller import request_stop

from automation.active_sessions import (
    get_session,
    remove_session,
)

from workflows.search_workflow import SearchWorkflow


router = APIRouter()

templates = Jinja2Templates(
    directory="templates"
)


# ============================================================
# LinkedIn Page
# ============================================================

@router.get("/tools/linkedin")
def linkedin_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="linkedin.html"
    )


# ============================================================
# Run LinkedIn Search
# ============================================================

@router.post("/linkedin")
def linkedin_search(
    data: LinkedInRequest
):

    print("=" * 70)
    print("LINKEDIN ENDPOINT HIT")
    print("=" * 70)

    print("Company :", data.company)
    print("Location:", data.location)
    print("Max     :", data.max_profiles)

    print("Starting LinkedIn automation...")

    try:

        result = run_linkedin(

            company=data.company,

            location=data.location,

            max_profiles=data.max_profiles,

            profile="temp",

            linkedin_email=data.linkedin_email,

            linkedin_password=data.linkedin_password

        )

        print("=" * 70)
        print("run_linkedin() RETURNED")
        print("=" * 70)

        print("TYPE   :", type(result))
        print("RESULT :", result)

        print("=" * 70)

        return result

    except Exception as ex:

        print("=" * 70)
        print("LINKEDIN EXCEPTION")
        print("=" * 70)

        traceback.print_exc()

        return {

            "success": False,

            "message": str(ex)

        }


# ============================================================
# LinkedIn Verification
# ============================================================

@router.post("/linkedin/verify")
def linkedin_verify(
    data: LinkedInVerifyRequest
):

    print("=" * 70)
    print("LINKEDIN VERIFICATION ENDPOINT HIT")
    print("=" * 70)

    print(
        "Session ID:",
        data.session_id
    )

    # --------------------------------------------------------
    # Retrieve existing browser session
    # --------------------------------------------------------

    session = get_session(
        data.session_id
    )

    if not session:

        print(
            "ERROR: LinkedIn session not found."
        )

        return {

            "success": False,

            "message":
                "LinkedIn browser session expired. Please start again."

        }

    browser = session["browser"]
    page = session["page"]

    company = session["company"]
    location = session["location"]
    max_profiles = session["max_profiles"]

    print("=" * 70)
    print("ACTIVE LINKEDIN SESSION FOUND")
    print("=" * 70)

    print("Company :", company)
    print("Location:", location)
    print("Max     :", max_profiles)

    try:

        # ----------------------------------------------------
        # Confirm browser/page still exists
        # ----------------------------------------------------

        print(
            "Current URL:",
            page.url
        )

        print(
            "Current Title:",
            page.title()
        )

        # ----------------------------------------------------
        # Find verification input
        # ----------------------------------------------------

        print("=" * 70)
        print("SEARCHING FOR VERIFICATION INPUT")
        print("=" * 70)

        verification_selectors = [

            "input[autocomplete='one-time-code']",

            "input[name='pin']",

            "input[name='verificationCode']",

            "input[name='code']",

            "input[type='number']",

            "input[inputmode='numeric']",

            "input[type='text']",

        ]

        verification_box = None

        for selector in verification_selectors:

            try:

                locator = page.locator(
                    selector
                ).first

                if locator.is_visible(
                    timeout=1000
                ):

                    verification_box = locator

                    print(
                        "Verification input found:",
                        selector
                    )

                    break

            except Exception:
                continue

        if verification_box is None:

            raise Exception(
                "LinkedIn verification input was not found."
            )

        # ----------------------------------------------------
        # Enter verification code
        # ----------------------------------------------------

        print(
            "Entering verification code..."
        )

        verification_box.fill(
            data.verification_code
        )

        print(
            "Verification code entered."
        )

        # ----------------------------------------------------
        # Submit verification
        # ----------------------------------------------------

        try:

            verification_box.press(
                "Enter"
            )

        except Exception:

            pass

        # Give LinkedIn time to process it.

        page.wait_for_timeout(
            3000
        )

        # ----------------------------------------------------
        # Wait for authentication result
        # ----------------------------------------------------

        print("=" * 70)
        print(
            "WAITING FOR LINKEDIN VERIFICATION RESULT"
        )
        print("=" * 70)

        authenticated = False

        for attempt in range(60):

            try:

                current_url = page.url.lower()

                print(
                    f"Verification check "
                    f"{attempt + 1}/60:",
                    current_url
                )

                # Successful authenticated pages

                if (
                    "linkedin.com/feed"
                    in current_url
                    or
                    "linkedin.com/search"
                    in current_url
                    or
                    "linkedin.com/company"
                    in current_url
                ):

                    authenticated = True

                    break

                # Still on login/checkpoint/challenge

                if (
                    "login" in current_url
                    or
                    "checkpoint" in current_url
                    or
                    "challenge" in current_url
                ):

                    page.wait_for_timeout(
                        1000
                    )

                    continue

                # Unknown LinkedIn page.
                # Give it some time before deciding.

                page.wait_for_timeout(
                    1000
                )

            except Exception as ex:

                print(
                    "Verification polling error:",
                    ex
                )

                page.wait_for_timeout(
                    1000
                )

        # ----------------------------------------------------
        # Authentication failed
        # ----------------------------------------------------

        if not authenticated:

            print("=" * 70)
            print(
                "LINKEDIN VERIFICATION NOT COMPLETED"
            )
            print("=" * 70)

            print(
                "Current URL:",
                page.url
            )

            print(
                "IMPORTANT: Browser session "
                "will remain alive."
            )

            # DO NOT close browser.
            #
            # DO NOT remove session.
            #
            # User can retry verification.

            return {

                "success": False,

                "verification_required": True,

                "session_id":
                    data.session_id,

                "message":
                    "LinkedIn verification was not completed. "
                    "The browser session remains active."

            }

        # ----------------------------------------------------
        # Authentication successful
        # ----------------------------------------------------

        print("=" * 70)
        print(
            "LINKEDIN VERIFICATION SUCCESSFUL"
        )
        print("=" * 70)

        print(
            "Authenticated URL:",
            page.url
        )

        print(
            "Authenticated Title:",
            page.title()
        )

        # ----------------------------------------------------
        # Run SearchWorkflow
        # ----------------------------------------------------

        print("=" * 70)
        print("STARTING SEARCH WORKFLOW")
        print("=" * 70)

        workflow = SearchWorkflow(
            page
        )

        result = workflow.run(

            company=company,

            location=location,

            max_profiles=max_profiles

        )

        print("=" * 70)
        print("SEARCH WORKFLOW COMPLETED")
        print("=" * 70)

        print(
            "Workflow result:",
            result
        )

        if not result:

            raise Exception(
                "SearchWorkflow returned no result."
            )

        # ----------------------------------------------------
        # Validate result
        # ----------------------------------------------------

        if not isinstance(
            result,
            dict
        ):

            raise Exception(
                "SearchWorkflow returned an invalid result."
            )

        csv_file = result.get(
            "csv"
        )

        count = result.get(
            "count",
            0
        )

        # ----------------------------------------------------
        # Successful completion
        # ----------------------------------------------------

        print("=" * 70)
        print("LINKEDIN AUTOMATION COMPLETED")
        print("=" * 70)

        print(
            "Profiles:",
            count
        )

        print(
            "CSV:",
            csv_file
        )

        # ----------------------------------------------------
        # NOW it is safe to close browser
        # ----------------------------------------------------

        print(
            "Closing LinkedIn browser..."
        )

        try:

            browser.close()

        except Exception as close_error:

            print(
                "Browser close warning:",
                close_error
            )

        remove_session(
            data.session_id
        )

        print(
            "LinkedIn session removed."
        )

        return {

            "success": True,

            "count": count,

            "filename":
                os.path.basename(
                    csv_file
                ) if csv_file else None

        }

    except Exception as ex:

        # ====================================================
        # IMPORTANT
        #
        # DO NOT CLOSE BROWSER HERE.
        #
        # The session may still be useful for:
        #
        # - retrying verification
        # - inspecting LinkedIn state
        # - recovering from a temporary timeout
        #
        # ====================================================

        print("=" * 70)
        print("LINKEDIN VERIFICATION/WORKFLOW ERROR")
        print("=" * 70)

        traceback.print_exc()

        print("=" * 70)
        print(
            "BROWSER SESSION KEPT ALIVE"
        )
        print("=" * 70)

        return {

            "success": False,

            "session_id":
                data.session_id,

            "verification_required": True,

            "message": str(ex)

        }


# ============================================================
# Stop LinkedIn Search
# ============================================================

@router.post("/linkedin/stop")
def stop_linkedin():

    print(
        "LinkedIn stop request received."
    )

    request_stop()

    return {

        "success": True,

        "message":
            "Stop request received."

    }


# ============================================================
# Download CSV
# ============================================================

@router.get(
    "/linkedin/download/{filename}"
)
def download_csv(
    filename: str
):

    print("=" * 70)
    print("DOWNLOAD REQUEST")
    print("=" * 70)

    print(
        "Filename:",
        filename
    )

    file_path = os.path.join(

        "modules",

        "RecruiterToolkit",

        "exports",

        filename

    )

    print(
        "Resolved:",
        file_path
    )

    print(
        "Exists:",
        os.path.exists(file_path)
    )

    if not os.path.exists(
        file_path
    ):

        return {

            "success": False,

            "message":
                "CSV file not found."

        }

    print(
        "Sending CSV..."
    )

    return FileResponse(

        path=file_path,

        filename=filename,

        media_type="text/csv"

    )
