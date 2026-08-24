import json
import os
import time
import traceback
from pathlib import Path

import requests

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from models.linkedin import LinkedInRequest
from models.linkedin_verify import LinkedInVerifyRequest

from services.github_actions import GitHubActionsService

from modules.RecruiterToolkit.linkedin_runner import run_linkedin

from automation.search_controller import request_stop

from automation.active_sessions import (
    get_session,
    remove_session,
)


router = APIRouter()

templates = Jinja2Templates(
    directory="templates"
)


# ============================================================
# Configuration
# ============================================================

GITHUB_API = "https://api.github.com"

GITHUB_OWNER = os.getenv(
    "GITHUB_OWNER",
    "avinash-design-ai",
)

GITHUB_REPO = os.getenv(
    "GITHUB_REPO",
    "RecruiterToolkitAI",
)

GITHUB_WORKFLOW = os.getenv(
    "GITHUB_WORKFLOW",
    "linkedin-v2-storage-search.yml",
)

GITHUB_BRANCH = os.getenv(
    "GITHUB_BRANCH",
    "main",
)

GITHUB_STORAGE_SECRET = "LINKEDIN_STORAGE_STATE"


# ============================================================
# GitHub helpers
# ============================================================

def github_headers():

    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable is not configured."
        )

    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


# ============================================================
# Update GitHub LinkedIn storage secret
# ============================================================

def update_github_storage_secret(storage_state):

    """
    Encrypt the Playwright storage state and update the
    GitHub repository Actions secret.

    Search is NOT performed here.
    """

    try:

        from nacl import encoding
        from nacl.public import PublicKey, SealedBox

    except ImportError:

        raise RuntimeError(
            "PyNaCl is required. Add 'PyNaCl' to requirements.txt."
        )

    headers = github_headers()

    key_url = (
        f"{GITHUB_API}/repos/"
        f"{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/"
        f"actions/secrets/public-key"
    )

    response = requests.get(
        key_url,
        headers=headers,
        timeout=30,
    )

    if response.status_code != 200:

        raise RuntimeError(
            "Unable to get GitHub Actions public key: "
            f"{response.status_code} "
            f"{response.text}"
        )

    key_data = response.json()

    key_id = key_data["key_id"]
    public_key = key_data["key"]

    public_key_obj = PublicKey(
        public_key.encode("utf-8"),
        encoding.Base64Encoder(),
    )

    sealed_box = SealedBox(
        public_key_obj
    )

    encrypted = sealed_box.encrypt(
        storage_state.encode("utf-8")
    )

    encrypted_value = (
        encoding.Base64Encoder()
        .encode(encrypted)
        .decode("utf-8")
    )

    secret_url = (
        f"{GITHUB_API}/repos/"
        f"{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/"
        f"actions/secrets/"
        f"{GITHUB_STORAGE_SECRET}"
    )

    response = requests.put(
        secret_url,
        headers=headers,
        json={
            "encrypted_value": encrypted_value,
            "key_id": key_id,
        },
        timeout=30,
    )

    if response.status_code not in (201, 204):

        raise RuntimeError(
            "Unable to update GitHub storage secret: "
            f"{response.status_code} "
            f"{response.text}"
        )

    print(
        "GitHub LINKEDIN_STORAGE_STATE secret updated successfully."
    )


# ============================================================
# Dispatch GitHub Actions workflow
# ============================================================

def dispatch_github_search(
    company,
    location,
    max_profiles,
):

    """
    Dispatch the GitHub Actions LinkedIn V2 workflow.

    IMPORTANT:
    This function does NOT run SearchWorkflowV2.

    SearchWorkflowV2 runs inside GitHub Actions.
    """

    return GitHubActionsService.dispatch_search(
        company=company,
        location=location,
        max_profiles=max_profiles,
    )


# ============================================================
# Find the GitHub run created by our dispatch
# ============================================================

def get_github_runs():

    headers = github_headers()

    url = (
        f"{GITHUB_API}/repos/"
        f"{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/"
        f"/actions/workflows/"
        f"{GITHUB_WORKFLOW}/runs"
    )

    response = requests.get(
        url,
        headers=headers,
        params={
            "branch": GITHUB_BRANCH,
            "event": "workflow_dispatch",
            "per_page": 20,
        },
        timeout=30,
    )

    if response.status_code != 200:

        raise RuntimeError(
            "Unable to get GitHub workflow runs: "
            f"{response.status_code} "
            f"{response.text}"
        )

    return response.json().get(
        "workflow_runs",
        [],
    )


def wait_for_dispatched_run(
    dispatch_started_at,
    timeout_seconds=30,
):

    """
    GitHub's workflow dispatch endpoint returns HTTP 204 and
    does not return the run_id.

    Therefore we poll the workflow runs API and locate the
    newly-created workflow run.
    """

    deadline = (
        time.time()
        + timeout_seconds
    )

    while time.time() < deadline:

        runs = get_github_runs()

        for run in runs:

            if run.get("event") != "workflow_dispatch":
                continue

            if run.get("head_branch") != GITHUB_BRANCH:
                continue

            created_at = run.get(
                "created_at"
            )

            if not created_at:
                continue

            try:

                created_timestamp = (
                    __import__("datetime")
                    .datetime
                    .fromisoformat(
                        created_at.replace(
                            "Z",
                            "+00:00",
                        )
                    )
                    .timestamp()
                )

            except Exception:

                continue

            if (
                created_timestamp
                >= dispatch_started_at - 5
            ):

                return run

        time.sleep(1)

    return None


# ============================================================
# Get specific GitHub run
# ============================================================

def get_github_run(run_id):

    headers = github_headers()

    url = (
        f"{GITHUB_API}/repos/"
        f"{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/"
        f"/actions/runs/"
        f"{run_id}"
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    if response.status_code != 200:

        raise RuntimeError(
            "Unable to get GitHub workflow status: "
            f"{response.status_code} "
            f"{response.text}"
        )

    return response.json()


# ============================================================
# Get GitHub artifacts for a run
# ============================================================

def get_github_artifacts(run_id):

    headers = github_headers()

    url = (
        f"{GITHUB_API}/repos/"
        f"{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/"
        f"/actions/runs/"
        f"{run_id}/artifacts"
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    if response.status_code != 200:

        raise RuntimeError(
            "Unable to get GitHub artifacts: "
            f"{response.status_code} "
            f"{response.text}"
        )

    return response.json().get(
        "artifacts",
        [],
    )


# ============================================================
# LinkedIn page
# ============================================================

@router.get("/tools/linkedin")
def linkedin_tools_page(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="linkedin.html",
    )


@router.get("/linkedin")
def linkedin_page(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="linkedin.html",
    )


# ============================================================
# Existing LOCAL LinkedIn search
#
# This endpoint is retained for the existing local
# automation functionality.
#
# The V2 GitHub workflow does NOT use this endpoint
# after authentication.
# ============================================================

@router.post("/linkedin")
def linkedin_search(
    data: LinkedInRequest,
):

    print("=" * 70)
    print("LINKEDIN LOCAL ENDPOINT")
    print("=" * 70)

    try:

        result = run_linkedin(
            company=data.company,
            location=data.location,
            max_profiles=data.max_profiles,
            profile="temp",
            linkedin_email=data.linkedin_email,
            linkedin_password=data.linkedin_password,
        )

        return result

    except Exception as ex:

        traceback.print_exc()

        return {
            "success": False,
            "message": str(ex),
        }


# ============================================================
# V2 START
#
# This endpoint starts the Render-side LinkedIn authentication.
#
# IMPORTANT:
# It does NOT run SearchWorkflowV2.
#
# SearchWorkflowV2 runs only after verification, inside
# GitHub Actions.
# ============================================================

@router.post("/linkedin/v2/search")
def linkedin_v2_search(
    data: LinkedInRequest,
):

    print("=" * 70)
    print("LINKEDIN V2 AUTHENTICATION START")
    print("=" * 70)

    print(
        "Company :",
        data.company,
    )

    print(
        "Location:",
        data.location,
    )

    print(
        "Max     :",
        data.max_profiles,
    )

    try:

        result = run_linkedin(
            company=data.company,
            location=data.location,
            max_profiles=data.max_profiles,
            profile="temp",
            linkedin_email=data.linkedin_email,
            linkedin_password=data.linkedin_password,
        )

        print("=" * 70)
        print("V2 AUTHENTICATION RESULT")
        print("=" * 70)

        print(result)

        return result

    except Exception as ex:

        traceback.print_exc()

        return {
            "success": False,
            "message": str(ex),
        }


# ============================================================
# Direct GitHub search endpoint
#
# This endpoint is intentionally retained.
#
# It should ONLY be called after authentication has already
# been completed.
#
# The verification flow below dispatches the workflow itself,
# so the webpage should NOT call this endpoint after /verify.
# ============================================================

@router.post("/linkedin/v2/github-search")
def linkedin_v2_github_search(
    data: LinkedInRequest,
):

    print("=" * 70)
    print("STARTING GITHUB ACTIONS - LINKEDIN V2")
    print("=" * 70)

    try:

        dispatch_started_at = time.time()

        dispatch_result = dispatch_github_search(
            company=data.company,
            location=data.location,
            max_profiles=data.max_profiles,
        )

        run = wait_for_dispatched_run(
            dispatch_started_at
        )

        if not run:

            return {
                "success": True,
                "github_started": True,
                "run_id": None,
                "workflow":
                    dispatch_result["workflow"],
                "branch":
                    dispatch_result["branch"],
                "message":
                    (
                        "GitHub Actions workflow was "
                        "dispatched, but the run ID has "
                        "not appeared yet."
                    ),
            }

        return {
            "success": True,
            "github_started": True,
            "run_id":
                run.get("id"),
            "workflow":
                dispatch_result["workflow"],
            "branch":
                dispatch_result["branch"],
            "html_url":
                run.get("html_url"),
            "message":
                "LinkedIn V2 GitHub Actions search started.",
        }

    except Exception as ex:

        traceback.print_exc()

        return {
            "success": False,
            "message": str(ex),
        }


# ============================================================
# LinkedIn verification
#
# Render:
#   1. receives verification code
#   2. verifies LinkedIn
#   3. saves storage state
#   4. updates GitHub secret
#   5. dispatches GitHub Actions
#
# GitHub:
#   SearchWorkflowV2
#   CSV creation
#   artifact upload
#
# Render DOES NOT run SearchWorkflowV2.
# ============================================================

@router.post("/linkedin/verify")
def linkedin_verify(
    data: LinkedInVerifyRequest,
):

    print("=" * 70)
    print("LINKEDIN VERIFICATION ENDPOINT HIT")
    print("=" * 70)

    print(
        "Session ID:",
        data.session_id,
    )

    session = get_session(
        data.session_id
    )

    if not session:

        return {
            "success": False,
            "message":
                (
                    "LinkedIn browser session expired. "
                    "Please start again."
                ),
        }

    browser = session["browser"]
    page = session["page"]

    company = session["company"]
    location = session["location"]
    max_profiles = session["max_profiles"]

    try:

        print(
            "Current URL:",
            page.url,
        )

        print(
            "Current Title:",
            page.title(),
        )

        # ----------------------------------------------------
        # Locate verification input
        # ----------------------------------------------------

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

                locator = (
                    page.locator(
                        selector
                    )
                    .first
                )

                if locator.is_visible(
                    timeout=1000
                ):

                    verification_box = locator

                    print(
                        "Verification input found:",
                        selector,
                    )

                    break

            except Exception:

                continue

        if verification_box is None:

            raise RuntimeError(
                "LinkedIn verification input was not found."
            )

        # ----------------------------------------------------
        # Enter verification code
        # ----------------------------------------------------

        verification_box.fill(
            data.verification_code
        )

        print(
            "Verification code entered."
        )

        try:

            verification_box.press(
                "Enter"
            )

        except Exception:

            pass

        page.wait_for_timeout(
            3000
        )

        # ----------------------------------------------------
        # Wait for authenticated LinkedIn page
        # ----------------------------------------------------

        authenticated = False

        for attempt in range(60):

            try:

                current_url = (
                    page.url.lower()
                )

                print(
                    f"Verification check "
                    f"{attempt + 1}/60:",
                    current_url,
                )

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

                if (
                    "/login"
                    in current_url
                    or
                    "checkpoint"
                    in current_url
                    or
                    "challenge"
                    in current_url
                ):

                    page.wait_for_timeout(
                        1000
                    )

                    continue

                page.wait_for_timeout(
                    1000
                )

            except Exception as ex:

                print(
                    "Verification polling error:",
                    ex,
                )

                page.wait_for_timeout(
                    1000
                )

        # ----------------------------------------------------
        # Verification failed
        # ----------------------------------------------------

        if not authenticated:

            return {
                "success": False,

                "verification_required": True,

                "session_id":
                    data.session_id,

                "message":
                    (
                        "LinkedIn verification was not "
                        "completed. The browser session "
                        "remains active."
                    ),
            }

        # ====================================================
        # AUTHENTICATED
        # ====================================================

        print("=" * 70)
        print(
            "LINKEDIN VERIFICATION SUCCESSFUL"
        )
        print("=" * 70)

        print(
            "Authenticated URL:",
            page.url,
        )

        # ----------------------------------------------------
        # Save authenticated storage state
        # ----------------------------------------------------

        storage_path = (
            Path.cwd()
            / "linkedin_storage_state_render.json"
        )

        print(
            "Saving authenticated storage state..."
        )

        page.context.storage_state(
            path=str(storage_path)
        )

        print(
            "Storage state saved:",
            storage_path,
        )

        with open(
            storage_path,
            "r",
            encoding="utf-8",
        ) as f:

            storage_state = f.read()

        # ----------------------------------------------------
        # Validate storage state before sending it
        # ----------------------------------------------------

        try:

            parsed_state = json.loads(
                storage_state
            )

            if not isinstance(
                parsed_state,
                dict,
            ):

                raise RuntimeError(
                    "Generated LinkedIn storage state is invalid."
                )

            cookies = parsed_state.get(
                "cookies",
                [],
            )

            print(
                "Storage state cookies:",
                len(cookies),
            )

            if not cookies:

                raise RuntimeError(
                    "Generated LinkedIn storage state contains no cookies."
                )

        except json.JSONDecodeError as ex:

            raise RuntimeError(
                "Generated LinkedIn storage state is not valid JSON."
            ) from ex

        # ----------------------------------------------------
        # Update GitHub secret
        # ----------------------------------------------------

        print(
            "Updating GitHub "
            "LINKEDIN_STORAGE_STATE secret..."
        )

        update_github_storage_secret(
            storage_state
        )

        print(
            "GitHub storage secret updated."
        )

        # ----------------------------------------------------
        # Dispatch GitHub Actions
        #
        # THIS is where the actual search begins.
        #
        # SearchWorkflowV2 does NOT run on Render.
        # ----------------------------------------------------

        print("=" * 70)
        print(
            "DISPATCHING GITHUB SEARCH WORKFLOW"
        )
        print("=" * 70)

        dispatch_started_at = time.time()

        dispatch_result = (
            dispatch_github_search(
                company=company,
                location=location,
                max_profiles=max_profiles,
            )
        )

        # ----------------------------------------------------
        # Find exact workflow run
        # ----------------------------------------------------

        run = wait_for_dispatched_run(
            dispatch_started_at
        )

        run_id = None
        run_url = None

        if run:

            run_id = run.get("id")
            run_url = run.get("html_url")

            print(
                "GitHub Actions run ID:",
                run_id,
            )

            print(
                "GitHub Actions URL:",
                run_url,
            )

        else:

            print(
                "WARNING: GitHub workflow was dispatched "
                "but run ID was not found yet."
            )

        # ----------------------------------------------------
        # Delete temporary Render storage file
        # ----------------------------------------------------

        try:

            storage_path.unlink(
                missing_ok=True
            )

        except Exception:

            pass

        # ----------------------------------------------------
        # Browser can now close.
        # GitHub already has the storage state.
        # ----------------------------------------------------

        try:

            browser.close()

        except Exception as ex:

            print(
                "Browser close warning:",
                ex,
            )

        remove_session(
            data.session_id
        )

        print(
            "Render LinkedIn session removed."
        )

        # ----------------------------------------------------
        # Return GitHub run information to webpage
        # ----------------------------------------------------

        return {

            "success": True,

            "verification_required":
                False,

            "github_started":
                True,

            "run_id":
                run_id,

            "html_url":
                run_url,

            "workflow":
                dispatch_result["workflow"],

            "branch":
                dispatch_result["branch"],

            "company":
                company,

            "location":
                location,

            "max_profiles":
                max_profiles,

            "message":
                (
                    "LinkedIn verified successfully. "
                    "GitHub Actions search has started."
                ),
        }

    except Exception as ex:

        traceback.print_exc()

        return {

            "success": False,

            "message":
                str(ex),

            "session_id":
                data.session_id,
        }


# ============================================================
# GitHub workflow status
#
# Legacy endpoint.
#
# The webpage should preferably use:
# /linkedin/v2/github-status/{run_id}
# ============================================================

@router.get(
    "/linkedin/v2/github-status"
)
def linkedin_github_status():

    try:

        runs = get_github_runs()

        if not runs:

            return {
                "success": True,
                "found": False,
                "status": "not_found",
            }

        run = runs[0]

        return {

            "success": True,

            "found": True,

            "run_id":
                run.get("id"),

            "status":
                run.get("status"),

            "conclusion":
                run.get("conclusion"),

            "html_url":
                run.get("html_url"),
        }

    except Exception as ex:

        traceback.print_exc()

        return {

            "success": False,

            "message":
                str(ex),
        }


# ============================================================
# GitHub workflow status by exact run ID
# ============================================================

@router.get(
    "/linkedin/v2/github-status/{run_id}"
)
def linkedin_github_status_by_id(
    run_id: int,
):

    try:

        run = get_github_run(
            run_id
        )

        artifacts = []

        if (
            run.get("status")
            == "completed"
            and
            run.get("conclusion")
            == "success"
        ):

            artifacts = (
                get_github_artifacts(
                    run_id
                )
            )

        csv_available = False

        for artifact in artifacts:

            if (
                artifact.get("name")
                ==
                "linkedin-v2-results"
                and
                not artifact.get("expired")
            ):

                csv_available = True

                break

        return {

            "success": True,

            "run_id":
                run.get("id"),

            "status":
                run.get("status"),

            "conclusion":
                run.get("conclusion"),

            "html_url":
                run.get("html_url"),

            "csv_available":
                csv_available,

            "artifacts": [

                {

                    "id":
                        artifact.get("id"),

                    "name":
                        artifact.get("name"),

                    "expired":
                        artifact.get("expired"),

                }

                for artifact in artifacts
            ],
        }

    except Exception as ex:

        traceback.print_exc()

        return {

            "success": False,

            "message":
                str(ex),
        }


# ============================================================
# Download CSV artifact
#
# Render downloads the GitHub artifact and returns the actual
# CSV file to the user's browser.
#
# Search itself still happens entirely on GitHub Actions.
# ============================================================

@router.get(
    "/linkedin/v2/github-csv/{run_id}"
)
def download_github_csv(
    run_id: int,
):

    try:

        # ----------------------------------------------------
        # Confirm workflow completed successfully
        # ----------------------------------------------------

        run = get_github_run(
            run_id
        )

        if run.get("status") != "completed":

            return {

                "success": False,

                "message":
                    "GitHub search is not completed yet.",
            }

        if run.get("conclusion") != "success":

            return {

                "success": False,

                "message":
                    (
                        "GitHub search did not complete "
                        "successfully."
                    ),
            }

        # ----------------------------------------------------
        # Find CSV artifact
        # ----------------------------------------------------

        artifacts = get_github_artifacts(
            run_id
        )

        artifact = None

        for item in artifacts:

            if (
                item.get("name")
                ==
                "linkedin-v2-results"
                and
                not item.get("expired")
            ):

                artifact = item

                break

        if not artifact:

            return {

                "success": False,

                "message":
                    "CSV artifact is not available yet.",
            }

        artifact_id = artifact["id"]

        # ----------------------------------------------------
        # Download GitHub artifact ZIP
        # ----------------------------------------------------

        headers = github_headers()

        url = (
            f"{GITHUB_API}/repos/"
            f"{GITHUB_OWNER}/"
            f"{GITHUB_REPO}/"
            f"/actions/artifacts/"
            f"{artifact_id}/zip"
        )

        response = requests.get(
            url,
            headers=headers,
            timeout=60,
        )

        if response.status_code != 200:

            raise RuntimeError(
                "Unable to download GitHub artifact: "
                f"{response.status_code}"
            )

        # ----------------------------------------------------
        # Temporary directory
        # ----------------------------------------------------

        temp_dir = Path(
            "/tmp/linkedin-v2-results"
        )

        temp_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        zip_path = (
            temp_dir
            / f"{artifact_id}.zip"
        )

        with open(
            zip_path,
            "wb",
        ) as f:

            f.write(
                response.content
            )

        # ----------------------------------------------------
        # Extract CSV
        # ----------------------------------------------------

        import zipfile

        with zipfile.ZipFile(
            zip_path,
            "r",
        ) as archive:

            csv_files = [

                name

                for name in archive.namelist()

                if name.lower().endswith(
                    ".csv"
                )
            ]

            if not csv_files:

                raise RuntimeError(
                    "No CSV file found inside GitHub artifact."
                )

            csv_name = csv_files[0]

            archive.extract(
                csv_name,
                temp_dir,
            )

        csv_path = (
            temp_dir
            / csv_name
        )

        # ----------------------------------------------------
        # Return CSV to browser
        # ----------------------------------------------------

        return FileResponse(

            path=str(csv_path),

            media_type="text/csv",

            filename=os.path.basename(
                csv_name
            ),
        )

    except Exception as ex:

        traceback.print_exc()

        return {

            "success": False,

            "message":
                str(ex),
        }


# ============================================================
# Stop search
#
# NOTE:
# This existing Render stop request does not automatically
# cancel a GitHub Actions workflow.
# ============================================================

@router.post(
    "/linkedin/stop"
)
def linkedin_stop():

    try:

        request_stop()

        return {

            "success": True,

            "message":
                "LinkedIn search stop requested.",
        }

    except Exception as ex:

        traceback.print_exc()

        return {

            "success": False,

            "message":
                str(ex),
        }