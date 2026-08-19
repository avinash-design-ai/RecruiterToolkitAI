from automation.browser import BrowserManager
from workflows.search_workflow_v2 import SearchWorkflowV2


COMPANY = "SmartWorks, LLC"
LOCATION = "New Jersey"

MAX_PROFILES = 5


browser = BrowserManager(
    profile="default"
)

try:

    # -------------------------------------------------
    # Open LinkedIn using the existing persistent session
    # -------------------------------------------------

    page = browser.new_page()

    print("=" * 70)
    print("OPENING LINKEDIN")
    print("=" * 70)

    page.goto(
        "https://www.linkedin.com/feed/",
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(3000)

    print(
        "Current URL:",
        page.url
    )

    # -------------------------------------------------
    # Check login
    # -------------------------------------------------

    if "linkedin.com/feed" not in page.url.lower():

        print(
            "LinkedIn login is required."
        )

        print(
            "Please complete login in the browser."
        )

        while True:

            page.wait_for_timeout(2000)

            if "linkedin.com/feed" in page.url.lower():

                print(
                    "LinkedIn login successful."
                )

                break

    else:

        print(
            "Existing LinkedIn session detected."
        )

    # -------------------------------------------------
    # V2 Workflow
    # -------------------------------------------------

    workflow = SearchWorkflowV2(
        page
    )

    result = workflow.run(
        company=COMPANY,
        location=LOCATION,
        max_profiles=MAX_PROFILES
    )

    # -------------------------------------------------
    # Result
    # -------------------------------------------------

    print("=" * 70)
    print("FINAL V2 SEARCH RESULT")
    print("=" * 70)

    print(
        "Count:",
        result.get("count")
    )

    print(
        "CSV:",
        result.get("csv")
    )

    for i, profile in enumerate(
        result.get("results", []),
        start=1
    ):

        print("-" * 60)
        print(
            f"PROFILE {i}"
        )
        print("-" * 60)

        for key, value in profile.items():

            print(
                f"{key}: {value}"
            )

finally:

    browser.close()