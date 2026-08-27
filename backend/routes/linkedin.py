import json
import os
import time
import traceback
import hashlib
import zipfile
import tempfile
import shutil
from pathlib import Path

import requests

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

from models.linkedin import LinkedInRequest
from models.linkedin_verify import LinkedInVerifyRequest

from services.github_actions import GitHubActionsService

from modules.RecruiterToolkit.linkedin_runner import (
    run_linkedin,
    _is_login_or_verification_page,
)

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
    """
    Build authenticated GitHub API headers.
    """

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
# Validate Playwright LinkedIn storage state
# ============================================================

def validate_linkedin_storage_state(
    storage_state,
):
    """
    Validate the Playwright storage state before it is
    uploaded to GitHub Actions.

    Required authentication cookies:

        li_at
        JSESSIONID

    Returns a compact diagnostic dictionary.

    The actual storage state is NOT returned by this helper.
    """

    if not isinstance(
        storage_state,
        dict,
    ):
        raise RuntimeError(
            "LinkedIn storage state is not a JSON object."
        )

    cookies = storage_state.get(
        "cookies",
        []
    )

    if not isinstance(
        cookies,
        list,
    ):
        raise RuntimeError(
            "LinkedIn storage state cookies are invalid."
        )

    if not cookies:
        raise RuntimeError(
            "LinkedIn storage state contains no cookies."
        )

    linkedin_cookies = [
        cookie
        for cookie in cookies
        if "linkedin.com"
        in cookie.get(
            "domain",
            ""
        ).lower()
    ]

    if not linkedin_cookies:
        raise RuntimeError(
            "LinkedIn storage state contains "
            "no LinkedIn cookies."
        )

    linkedin_cookie_names = {
        cookie.get("name")
        for cookie in linkedin_cookies
        if cookie.get("name")
    }

    required_cookie_names = {
        "li_at",
        "JSESSIONID",
    }

    missing_cookie_names = (
        required_cookie_names
        - linkedin_cookie_names
    )

    if missing_cookie_names:
        raise RuntimeError(
            "LinkedIn storage state is missing "
            "required authentication cookies: "
            + ", ".join(
                sorted(
                    missing_cookie_names
                )
            )
        )

    return {
        "total_cookies": len(cookies),
        "linkedin_cookies": len(linkedin_cookies),
        "linkedin_cookie_names": sorted(
            linkedin_cookie_names
        ),
    }


# ============================================================
# Update GitHub LinkedIn storage secret
# ============================================================

def update_github_storage_secret(
    storage_state,
):
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
            "PyNaCl is required. Add 'PyNaCl' "
            "to requirements.txt."
        )

    # --------------------------------------------------------
    # Validate state
    # --------------------------------------------------------

    validation = validate_linkedin_storage_state(
        storage_state
    )

    print(
        "GitHub secret storage validation:",
        validation
    )

    # --------------------------------------------------------
    # Serialize state
    # --------------------------------------------------------

    storage_json = json.dumps(
        storage_state,
        separators=(
            ",",
            ":",
        ),
    )

    if not storage_json.strip():
        raise RuntimeError(
            "Serialized LinkedIn storage state is empty."
        )

    # --------------------------------------------------------
    # GitHub headers
    # --------------------------------------------------------

    headers = github_headers()

    # --------------------------------------------------------
    # Get GitHub Actions repository public key
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Encrypt using GitHub's public key
    # --------------------------------------------------------

    public_key_obj = PublicKey(
        public_key.encode("utf-8"),
        encoding.Base64Encoder(),
    )

    sealed_box = SealedBox(
        public_key_obj
    )

    encrypted = sealed_box.encrypt(
        storage_json.encode("utf-8")
    )

    encrypted_value = (
        encoding.Base64Encoder()
        .encode(encrypted)
        .decode("utf-8")
    )

    # --------------------------------------------------------
    # Update repository Actions secret
    # --------------------------------------------------------

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

    if response.status_code not in (
        201,
        204,
    ):
        raise RuntimeError(
            "Unable to update GitHub storage secret: "
            f"{response.status_code} "
            f"{response.text}"
        )

    print(
        "GitHub LINKEDIN_STORAGE_STATE secret "
        "updated successfully."
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
# Find GitHub workflow runs
# ============================================================

def get_github_runs():

    headers = github_headers()

    url = (
        f"{GITHUB_API}/repos/"
        f"{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/"
        f"actions/workflows/"
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


# ============================================================
# Wait for dispatched workflow run
# ============================================================

def wait_for_dispatched_run(
    dispatch_started_at,
    timeout_seconds=30,
):
    """
    GitHub workflow dispatch returns HTTP 204 and does not
    return the run_id.

    Poll the workflow runs API and locate the newly-created
    workflow run.
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

def get_github_run(
    run_id,
):

    headers = github_headers()

    url = (
        f"{GITHUB_API}/repos/"
        f"{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/"
        f"actions/runs/"
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

def get_github_artifacts(
    run_id,
):

    headers = github_headers()

    url = (
        f"{GITHUB_API}/repos/"
        f"{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/"
        f"actions/runs/"
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
# Find CSV inside extracted artifact
# ============================================================

def find_csv_file(
    extraction_dir: Path,
):
    """
    Recursively locate CSV files inside the extracted
    GitHub artifact.

    Returns:
        Path

    Raises:
        RuntimeError
    """

    csv_files = sorted(
        [
            path
            for path in extraction_dir.rglob("*")
            if path.is_file()
            and path.suffix.lower() == ".csv"
        ]
    )

    if not csv_files:

        raise RuntimeError(
            "No CSV file was found inside the GitHub artifact."
        )

    print(
        "CSV files found inside artifact:"
    )

    for csv_file in csv_files:

        print(
            " -",
            csv_file,
        )

    # --------------------------------------------------------
    # Prefer the most likely LinkedIn result file if there
    # are multiple CSVs.
    # --------------------------------------------------------

    preferred_names = [
        "linkedin-v2-results.csv",
        "linkedin_results.csv",
        "linkedin-results.csv",
        "results.csv",
    ]

    for preferred_name in preferred_names:

        for csv_file in csv_files:

            if (
                csv_file.name.lower()
                == preferred_name.lower()
            ):

                print(
                    "Selected preferred CSV:",
                    csv_file,
                )

                return csv_file

    # --------------------------------------------------------
    # If only one CSV exists, use it.
    # --------------------------------------------------------

    if len(csv_files) == 1:

        print(
            "Selected only CSV:",
            csv_files[0],
        )

        return csv_files[0]

    # --------------------------------------------------------
    # Multiple CSVs and no preferred filename.
    # Select the largest CSV because result CSVs are normally
    # the largest artifact file.
    # --------------------------------------------------------

    csv_files.sort(
        key=lambda path: path.stat().st_size,
        reverse=True,
    )

    selected = csv_files[0]

    print(
        "Multiple CSV files found."
    )

    print(
        "Selected largest CSV:",
        selected,
    )

    return selected


# ============================================================
# Safe ZIP extraction
# ============================================================

def extract_artifact_zip(
    zip_path: Path,
    extraction_dir: Path,
):
    """
    Safely extract a GitHub artifact ZIP.

    Protects against ZIP path traversal.
    """

    if not zip_path.exists():

        raise RuntimeError(
            "GitHub artifact ZIP file does not exist."
        )

    if zip_path.stat().st_size <= 0:

        raise RuntimeError(
            "GitHub artifact ZIP file is empty."
        )

    if not zipfile.is_zipfile(
        zip_path
    ):

        raise RuntimeError(
            "Downloaded GitHub artifact is not a valid ZIP file."
        )

    extraction_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    extraction_root = (
        extraction_dir.resolve()
    )

    with zipfile.ZipFile(
        zip_path,
        "r",
    ) as archive:

        members = archive.infolist()

        if not members:

            raise RuntimeError(
                "GitHub artifact ZIP contains no files."
            )

        for member in members:

            member_path = (
                extraction_dir
                / member.filename
            ).resolve()

            try:

                member_path.relative_to(
                    extraction_root
                )

            except ValueError:

                raise RuntimeError(
                    "Unsafe path detected inside GitHub artifact ZIP: "
                    f"{member.filename}"
                )

        archive.extractall(
            extraction_dir
        )

    print(
        "GitHub artifact extracted successfully:",
        extraction_dir,
    )


# ============================================================
# Cleanup downloaded artifact files
# ============================================================

def cleanup_download_directory(
    directory: str,
):
    """
    Delete temporary artifact directory after the CSV
    response has completed.
    """

    try:

        directory_path = Path(
            directory
        )

        if directory_path.exists():

            shutil.rmtree(
                directory_path,
                ignore_errors=True,
            )

            print(
                "Temporary GitHub artifact directory "
                "cleaned up:",
                directory_path,
            )

    except Exception as ex:

        print(
            "Artifact cleanup warning:",
            ex,
        )


# ============================================================
# LinkedIn pages
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
            authentication_only=True,
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
# Render-side LinkedIn authentication.
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
            authentication_only=True,
        )

        print("=" * 70)
        print("V2 AUTHENTICATION RESULT")
        print("=" * 70)

        print(result)

        if (
            result.get("success")
            and result.get("authentication_only")
        ):

            storage_state = result.pop(
                "storage_state",
                None,
            )

            if not storage_state:

                raise RuntimeError(
                    "LinkedIn authentication succeeded, "
                    "but no storage state was returned."
                )

            print("=" * 70)
            print("VALIDATING LINKEDIN STORAGE STATE")
            print("=" * 70)

            validation = (
                validate_linkedin_storage_state(
                    storage_state
                )
            )

            print(
                "Storage validation:",
                validation,
            )

            storage_json = json.dumps(
                storage_state,
                separators=(
                    ",",
                    ":",
                ),
            )

            if not storage_json.strip():

                raise RuntimeError(
                    "Serialized LinkedIn storage state is empty."
                )

            print("=" * 70)
            print(
                "UPDATING GITHUB LINKEDIN STORAGE SECRET"
            )
            print("=" * 70)

            update_github_storage_secret(
                storage_state
            )

            print(
                "GitHub storage secret updated."
            )

            print("=" * 70)
            print(
                "DISPATCHING GITHUB SEARCH WORKFLOW"
            )
            print("=" * 70)

            dispatch_started_at = time.time()

            dispatch_result = (
                dispatch_github_search(
                    company=data.company,
                    location=data.location,
                    max_profiles=data.max_profiles,
                )
            )

            if not isinstance(
                dispatch_result,
                dict,
            ):

                raise RuntimeError(
                    "GitHub workflow dispatch returned "
                    "an invalid response."
                )

            print(
                "GitHub dispatch response:",
                dispatch_result,
            )

            run = wait_for_dispatched_run(
                dispatch_started_at
            )

            if run:

                run_id = run.get(
                    "id"
                )

                run_url = run.get(
                    "html_url"
                )

                print("=" * 70)
                print(
                    "GITHUB ACTIONS WORKFLOW STARTED"
                )
                print("=" * 70)

                print(
                    "Run ID:",
                    run_id,
                )

                print(
                    "Run URL:",
                    run_url,
                )

                result.update({

                    "github_started":
                        True,

                    "run_id":
                        run_id,

                    "workflow":
                        dispatch_result.get(
                            "workflow"
                        ),

                    "branch":
                        dispatch_result.get(
                            "branch"
                        ),

                    "html_url":
                        run_url,

                    "message":
                        (
                            "LinkedIn authentication completed "
                            "and the GitHub Actions search "
                            "has started."
                        ),
                })

            else:

                print("=" * 70)
                print(
                    "GITHUB WORKFLOW DISPATCHED"
                )
                print("=" * 70)

                result.update({

                    "github_started":
                        True,

                    "run_id":
                        None,

                    "workflow":
                        dispatch_result.get(
                            "workflow"
                        ),

                    "branch":
                        dispatch_result.get(
                            "branch"
                        ),

                    "html_url":
                        None,

                    "message":
                        (
                            "LinkedIn authentication completed "
                            "and GitHub Actions was dispatched. "
                            "The workflow run ID is not available yet."
                        ),
                })

            result.pop(
                "storage_state",
                None,
            )

            result.pop(
                "storage_json",
                None,
            )

            result.pop(
                "linkedin_storage_state",
                None,
            )

        if isinstance(
            result,
            dict,
        ):

            result.pop(
                "storage_state",
                None,
            )

            result.pop(
                "storage_json",
                None,
            )

            result.pop(
                "linkedin_storage_state",
                None,
            )

        return result

    except Exception as ex:

        traceback.print_exc()

        return {
            "success": False,
            "message": str(ex),
        }


# ============================================================
# Direct GitHub search endpoint
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

        # ====================================================
        # Locate verification input
        # ====================================================

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

        # ====================================================
        # Enter verification code
        # ====================================================

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

        # ====================================================
        # Wait for authenticated LinkedIn page
        # ====================================================

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
        print("LINKEDIN VERIFICATION SUCCESSFUL")
        print("=" * 70)

        print(
            "Authenticated URL before Feed navigation:",
            page.url,
        )

        # ====================================================
        # Move same authenticated page to Feed
        # ====================================================

        print("=" * 70)
        print(
            "MOVING AUTHENTICATED PLAYWRIGHT PAGE "
            "TO LINKEDIN FEED"
        )
        print("=" * 70)

        try:

            page.goto(
                "https://www.linkedin.com/feed/",
                wait_until="domcontentloaded",
                timeout=60000,
            )

        except Exception as ex:

            print(
                "Feed navigation warning:",
                ex,
            )

        page.wait_for_timeout(
            5000
        )

        print(
            "Post-verification URL:",
            page.url,
        )

        print(
            "Post-verification title:",
            page.title(),
        )

        # ====================================================
        # Confirm Feed
        # ====================================================

        feed_loaded = False

        for attempt in range(30):

            try:

                current_url = (
                    page.url.lower()
                )

                print(
                    f"Feed check {attempt + 1}/30:",
                    current_url,
                )

                if (
                    "linkedin.com/feed"
                    in current_url
                ):

                    feed_loaded = True

                    break

                if _is_login_or_verification_page(
                    page
                ):

                    print(
                        "LinkedIn returned to "
                        "login/verification during "
                        "Feed navigation."
                    )

                    break

            except Exception as ex:

                print(
                    "Feed verification polling error:",
                    ex,
                )

            page.wait_for_timeout(
                1000
            )

        if not feed_loaded:

            return {
                "success": False,
                "verification_required": True,
                "session_id":
                    data.session_id,
                "message":
                    (
                        "LinkedIn verification succeeded, "
                        "but the authenticated Playwright "
                        "page did not reach the LinkedIn Feed."
                    ),
            }

        print("=" * 70)
        print("LINKEDIN FEED CONFIRMED")
        print("=" * 70)

        print(
            "Authenticated Feed URL:",
            page.url,
        )

        print(
            "Authenticated Feed Title:",
            page.title(),
        )

        # ====================================================
        # Save authenticated storage state
        # ====================================================

        storage_path = (
            Path.cwd()
            / "linkedin_storage_state_render.json"
        )

        print("=" * 70)
        print(
            "SAVING AUTHENTICATED LINKEDIN STORAGE STATE"
        )
        print("=" * 70)

        page.context.storage_state(
            path=str(storage_path)
        )

        print(
            "Storage state saved:",
            storage_path,
        )

        if not storage_path.exists():

            raise RuntimeError(
                "LinkedIn storage state file "
                "was not created."
            )

        storage_size = (
            storage_path.stat().st_size
        )

        if storage_size <= 0:

            raise RuntimeError(
                "LinkedIn storage state file is empty."
            )

        with open(
            storage_path,
            "r",
            encoding="utf-8",
        ) as f:

            storage_state = f.read()

        if not storage_state.strip():

            raise RuntimeError(
                "LinkedIn storage state JSON is empty."
            )

        # ====================================================
        # Parse storage state
        # ====================================================

        try:

            parsed_state = json.loads(
                storage_state
            )

        except json.JSONDecodeError as ex:

            raise RuntimeError(
                "Generated LinkedIn storage state "
                "is not valid JSON."
            ) from ex

        # ====================================================
        # Validate storage state
        # ====================================================

        print("=" * 70)
        print(
            "VALIDATING GENERATED LINKEDIN STORAGE STATE"
        )
        print("=" * 70)

        validation = (
            validate_linkedin_storage_state(
                parsed_state
            )
        )

        storage_sha256 = hashlib.sha256(
            storage_state.encode("utf-8")
        ).hexdigest()

        print(
            "Storage state file:",
            storage_path,
        )

        print(
            "Storage state size:",
            storage_size,
            "bytes",
        )

        print(
            "Total cookies:",
            validation["total_cookies"],
        )

        print(
            "LinkedIn cookies:",
            validation["linkedin_cookies"],
        )

        print(
            "LinkedIn cookie names:",
            ", ".join(
                validation[
                    "linkedin_cookie_names"
                ]
            ),
        )

        print(
            "Storage state SHA256:",
            storage_sha256,
        )

        print(
            "Generated LinkedIn storage state "
            "validated successfully."
        )

        # ====================================================
        # Update GitHub secret
        # ====================================================

        print("=" * 70)
        print(
            "UPDATING GITHUB LINKEDIN STORAGE SECRET"
        )
        print("=" * 70)

        update_github_storage_secret(
            parsed_state
        )

        print(
            "GitHub LINKEDIN_STORAGE_STATE secret "
            "updated successfully."
        )

        # ====================================================
        # Dispatch GitHub Actions
        # ====================================================

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

        if not isinstance(
            dispatch_result,
            dict,
        ):

            raise RuntimeError(
                "GitHub workflow dispatch returned "
                "an invalid response."
            )

        print(
            "GitHub dispatch response:",
            dispatch_result,
        )

        # ====================================================
        # Find exact workflow run
        # ====================================================

        run = wait_for_dispatched_run(
            dispatch_started_at
        )

        run_id = None
        run_url = None

        if run:

            run_id = run.get(
                "id"
            )

            run_url = run.get(
                "html_url"
            )

            print("=" * 70)
            print(
                "GITHUB ACTIONS WORKFLOW STARTED"
            )
            print("=" * 70)

            print(
                "Run ID:",
                run_id,
            )

            print(
                "Run URL:",
                run_url,
            )

        else:

            print("=" * 70)
            print(
                "GITHUB WORKFLOW DISPATCHED"
            )
            print("=" * 70)

            print(
                "WARNING: GitHub workflow was dispatched "
                "but run ID was not found yet."
            )

        # ====================================================
        # Delete temporary Render storage file
        # ====================================================

        try:

            storage_path.unlink(
                missing_ok=True
            )

            print(
                "Temporary Render storage state deleted."
            )

        except Exception as ex:

            print(
                "Storage state cleanup warning:",
                ex,
            )

        # ====================================================
        # Close Render browser
        # ====================================================

        try:

            browser.close()

            print(
                "Render LinkedIn browser closed."
            )

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

        # ====================================================
        # Return ONLY safe workflow information
        # ====================================================

        return {

            "success":
                True,

            "verification_required":
                False,

            "github_started":
                True,

            "run_id":
                run_id,

            "html_url":
                run_url,

            "workflow":
                dispatch_result.get(
                    "workflow"
                ),

            "branch":
                dispatch_result.get(
                    "branch"
                ),

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

            "success":
                False,

            "message":
                str(ex),

            "session_id":
                data.session_id,
        }


# ============================================================
# GitHub workflow status
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

            "success":
                True,

            "found":
                True,

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

            "success":
                False,

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

            "success":
                True,

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

            "success":
                False,

            "message":
                str(ex),
        }


# ============================================================
# Download CSV artifact
#
# FIXED VERSION
#
# Render downloads the GitHub artifact ZIP, safely extracts
# it into a unique temporary directory, recursively locates
# the CSV, and returns the CSV to the browser.
#
# Search itself still happens entirely on GitHub Actions.
# ============================================================

@router.get(
    "/linkedin/v2/github-csv/{run_id}"
)
def download_github_csv(
    run_id: int,
):

    temp_dir = None

    try:

        print("=" * 70)
        print(
            "GITHUB CSV DOWNLOAD REQUEST"
        )
        print("=" * 70)

        print(
            "Run ID:",
            run_id,
        )

        # ----------------------------------------------------
        # Confirm workflow completed successfully
        # ----------------------------------------------------

        run = get_github_run(
            run_id
        )

        status = run.get(
            "status"
        )

        conclusion = run.get(
            "conclusion"
        )

        print(
            "GitHub workflow status:",
            status,
        )

        print(
            "GitHub workflow conclusion:",
            conclusion,
        )

        if status != "completed":

            return {
                "success": False,
                "csv_available": False,
                "message":
                    (
                        "GitHub search is not completed yet."
                    ),
            }

        if conclusion != "success":

            return {
                "success": False,
                "csv_available": False,
                "message":
                    (
                        "GitHub search did not complete "
                        "successfully."
                    ),
            }

        # ----------------------------------------------------
        # Find artifacts
        # ----------------------------------------------------

        artifacts = get_github_artifacts(
            run_id
        )

        print(
            "Number of GitHub artifacts:",
            len(artifacts),
        )

        artifact = None

        for item in artifacts:

            print(
                "Artifact:",
                item.get("name"),
                "ID:",
                item.get("id"),
                "Expired:",
                item.get("expired"),
            )

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
                "csv_available": False,
                "message":
                    (
                        "The linkedin-v2-results GitHub "
                        "artifact was not found or has expired."
                    ),
            }

        artifact_id = artifact.get(
            "id"
        )

        if not artifact_id:

            raise RuntimeError(
                "GitHub artifact does not contain an artifact ID."
            )

        print(
            "Selected artifact ID:",
            artifact_id,
        )

        # ----------------------------------------------------
        # Create unique temporary directory
        # ----------------------------------------------------

        temp_dir = Path(
            tempfile.mkdtemp(
                prefix=f"linkedin-v2-{run_id}-"
            )
        )

        print(
            "Temporary artifact directory:",
            temp_dir,
        )

        zip_path = (
            temp_dir
            / "github-artifact.zip"
        )

        extraction_dir = (
            temp_dir
            / "extracted"
        )

        # ----------------------------------------------------
        # Download GitHub artifact ZIP
        # ----------------------------------------------------

        headers = github_headers()

        artifact_url = (
            f"{GITHUB_API}/repos/"
            f"{GITHUB_OWNER}/"
            f"{GITHUB_REPO}/"
            f"actions/artifacts/"
            f"{artifact_id}/zip"
        )

        print(
            "Downloading GitHub artifact..."
        )

        response = requests.get(
            artifact_url,
            headers=headers,
            timeout=120,
            allow_redirects=True,
        )

        print(
            "GitHub artifact download status:",
            response.status_code,
        )

        print(
            "GitHub artifact response size:",
            len(response.content),
            "bytes",
        )

        if response.status_code != 200:

            raise RuntimeError(
                "Unable to download GitHub artifact: "
                f"{response.status_code} "
                f"{response.text[:1000]}"
            )

        if not response.content:

            raise RuntimeError(
                "GitHub returned an empty artifact response."
            )

        # ----------------------------------------------------
        # Save ZIP
        # ----------------------------------------------------

        with open(
            zip_path,
            "wb",
        ) as f:

            f.write(
                response.content
            )

        print(
            "Artifact ZIP saved:",
            zip_path,
        )

        print(
            "Artifact ZIP size:",
            zip_path.stat().st_size,
            "bytes",
        )

        # ----------------------------------------------------
        # Validate and extract ZIP
        # ----------------------------------------------------

        extract_artifact_zip(
            zip_path=zip_path,
            extraction_dir=extraction_dir,
        )

        # ----------------------------------------------------
        # Find CSV recursively
        # ----------------------------------------------------

        csv_path = find_csv_file(
            extraction_dir
        )

        if not csv_path.exists():

            raise RuntimeError(
                "CSV file was located but does not exist."
            )

        csv_size = (
            csv_path.stat().st_size
        )

        if csv_size <= 0:

            raise RuntimeError(
                "CSV file exists but is empty."
            )

        print(
            "=" * 70
        )

        print(
            "CSV READY FOR DOWNLOAD"
        )

        print(
            "CSV path:",
            csv_path,
        )

        print(
            "CSV size:",
            csv_size,
            "bytes",
        )

        print(
            "CSV filename:",
            csv_path.name,
        )

        print(
            "=" * 70
        )

        # ----------------------------------------------------
        # Create a deterministic download filename
        # ----------------------------------------------------

        download_filename = (
            f"linkedin-results-{run_id}.csv"
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # FileResponse sends the actual CSV file.
        #
        # BackgroundTask cleans the complete temporary
        # directory AFTER the response has finished.
        # ----------------------------------------------------

        cleanup_task = BackgroundTask(
            cleanup_download_directory,
            str(temp_dir),
        )

        return FileResponse(

            path=str(csv_path),

            media_type="text/csv",

            filename=download_filename,

            background=cleanup_task,
        )

    except zipfile.BadZipFile:

        if temp_dir:

            cleanup_download_directory(
                str(temp_dir)
            )

        traceback.print_exc()

        return {
            "success": False,
            "csv_available": False,
            "message":
                (
                    "GitHub artifact download was not "
                    "a valid ZIP file."
                ),
        }

    except Exception as ex:

        if temp_dir:

            cleanup_download_directory(
                str(temp_dir)
            )

        traceback.print_exc()

        return {
            "success": False,
            "csv_available": False,
            "message": str(ex),
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

            "success":
                True,

            "message":
                "LinkedIn search stop requested.",
        }

    except Exception as ex:

        traceback.print_exc()

        return {

            "success":
                False,

            "message":
                str(ex),
        }