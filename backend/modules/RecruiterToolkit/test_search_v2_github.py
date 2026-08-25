import os

from automation.browser import BrowserManager
from workflows.search_workflow_v2 import SearchWorkflowV2


COMPANY = os.environ["COMPANY"]
LOCATION = os.environ["LOCATION"]
MAX_PROFILES = int(os.environ["MAX_PROFILES"])
STORAGE_STATE = os.environ["LINKEDIN_STORAGE_STATE"]


print("=" * 70)
print("STORAGE STATE INPUT VALIDATION")
print("=" * 70)

print("Storage state path:", STORAGE_STATE)

if not os.path.isfile(STORAGE_STATE):
    raise RuntimeError(
        f"LinkedIn storage state file not found: {STORAGE_STATE}"
    )

storage_size = os.path.getsize(STORAGE_STATE)

print("Storage state size:", storage_size, "bytes")

if storage_size <= 0:
    raise RuntimeError(
        "LinkedIn storage state file is empty."
    )

import json
import hashlib

with open(
    STORAGE_STATE,
    "r",
    encoding="utf-8"
) as f:
    storage_raw = f.read()

print(
    "Storage state SHA256:",
    hashlib.sha256(
        storage_raw.encode("utf-8")
    ).hexdigest()
)

try:
    storage_data = json.loads(storage_raw)
except Exception as ex:
    raise RuntimeError(
        f"Invalid LinkedIn storage state JSON: {ex}"
    )

if not isinstance(storage_data, dict):
    raise RuntimeError(
        "LinkedIn storage state is not a JSON object."
    )

storage_cookies = storage_data.get(
    "cookies",
    []
)

if not storage_cookies:
    raise RuntimeError(
        "LinkedIn storage state contains no cookies."
    )

linkedin_storage_cookies = [
    cookie
    for cookie in storage_cookies
    if "linkedin.com"
    in cookie.get("domain", "").lower()
]

print(
    "Total storage cookies:",
    len(storage_cookies)
)

print(
    "LinkedIn storage cookies:",
    len(linkedin_storage_cookies)
)

storage_cookie_names = {
    cookie.get("name")
    for cookie in linkedin_storage_cookies
}

print(
    "LinkedIn storage cookie names:",
    ", ".join(
        sorted(
            name
            for name in storage_cookie_names
            if name
        )
    )
)

required_storage_cookies = {
    "li_at",
    "JSESSIONID",
}

missing_storage_cookies = (
    required_storage_cookies
    - storage_cookie_names
)

if missing_storage_cookies:
    raise RuntimeError(
        "Required LinkedIn authentication cookies "
        "missing from storage state: "
        + ", ".join(
            sorted(missing_storage_cookies)
        )
    )

print(
    "Required LinkedIn authentication cookies confirmed."
)

print("=" * 70)


print("=" * 70)
print("GITHUB ACTIONS - LINKEDIN V2")
print("=" * 70)

print("Company:", COMPANY)
print("Location:", LOCATION)
print("Max profiles:", MAX_PROFILES)


browser = BrowserManager(
    profile="github-v2",
    storage_state=STORAGE_STATE,
)

try:

    page = browser.new_page()

    print("=" * 70)
    print("LOADED STORAGE STATE DIAGNOSTICS")
    print("=" * 70)

    cookies = page.context.cookies("https://www.linkedin.com")

    print("Total context cookies:", len(cookies))

    linkedin_cookies = [
        c for c in cookies
        if "linkedin.com" in c.get("domain", "")
    ]

    print("LinkedIn context cookies:", len(linkedin_cookies))

    for c in linkedin_cookies:
        if c["name"] in ["li_at", "JSESSIONID", "bcookie", "bscookie"]:
            print(
                "name=", c["name"],
                "domain=", c.get("domain"),
                "path=", c.get("path"),
                "secure=", c.get("secure"),
                "expires=", c.get("expires"),
            )

    print("=" * 70)


    print("=" * 70)
    print("OPENING LINKEDIN")
    print("=" * 70)

    page.goto(
        "https://www.linkedin.com/feed/",
        wait_until="domcontentloaded",
        timeout=60000,
    )

    page.wait_for_timeout(5000)

    print("URL:", page.url)
    print("Title:", page.title())

    print("=" * 70)
    print("POST-NAVIGATION LINKEDIN COOKIE DIAGNOSTICS")
    print("=" * 70)

    post_cookies = page.context.cookies(
        "https://www.linkedin.com"
    )

    print(
        "Post-navigation LinkedIn cookies:",
        len(post_cookies)
    )

    for c in post_cookies:
        if c["name"] in [
            "li_at",
            "JSESSIONID",
            "bcookie",
            "bscookie",
        ]:
            print(
                "name=", c["name"],
                "domain=", c.get("domain"),
                "path=", c.get("path"),
                "secure=", c.get("secure"),
                "expires=", c.get("expires"),
            )

    print(
        "Final URL:",
        page.url
    )

    print(
        "Final title:",
        page.title()
    )


    url = page.url.lower()

    if "/login" in url:
        raise RuntimeError("LinkedIn login page reached.")

    if "checkpoint" in url:
        raise RuntimeError("LinkedIn checkpoint reached.")

    if "challenge" in url:
        raise RuntimeError("LinkedIn challenge reached.")

    if "/feed" not in url:
        raise RuntimeError(
            f"Unexpected LinkedIn URL: {page.url}"
        )

    print("=" * 70)
    print("AUTHENTICATED LINKEDIN SESSION CONFIRMED")
    print("=" * 70)

    workflow = SearchWorkflowV2(page)

    result = workflow.run(
        company=COMPANY,
        location=LOCATION,
        max_profiles=MAX_PROFILES,
    )

    print("=" * 70)
    print("V2 WORKFLOW FINISHED")
    print("=" * 70)

    print(result)

finally:

    print("=" * 70)
    print("CLOSING BROWSER")
    print("=" * 70)

    browser.close()
