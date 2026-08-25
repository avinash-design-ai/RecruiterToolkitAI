import os

from automation.browser import BrowserManager
from workflows.search_workflow_v2 import SearchWorkflowV2


COMPANY = os.environ["COMPANY"]
LOCATION = os.environ["LOCATION"]
MAX_PROFILES = int(os.environ["MAX_PROFILES"])
STORAGE_STATE = os.environ["LINKEDIN_STORAGE_STATE"]


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