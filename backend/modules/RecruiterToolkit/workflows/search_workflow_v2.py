from pages.company_page import CompanyPage
from pages.linkedin_profile_page_v2 import LinkedInProfilePageV2

from automation.exporter import Exporter
from automation.search_controller import should_stop


def normalize_company(value):
    """
    Normalize company names only for comparison.
    Does not alter the original company value used elsewhere.
    """
    if not value:
        return ""

    import re

    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())


def normalize_location(value):
    """
    Normalize location text only for comparison.

    The profile page may return locations such as:

        Edison, New Jersey
        Edison, New Jersey, United States
        New Jersey, United States

    The workflow compares the requested location as a normalized
    component of the actual profile location.
    """
    if not value:
        return ""

    import re

    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())


class SearchWorkflowV2:

    def __init__(self, page):

        self.page = page

        # -------------------------------------------------
        # IMPORTANT:
        # Keep CompanyPage as the owner of the LinkedIn
        # company search, employee search, location filter,
        # result extraction, and pagination.
        #
        # DO NOT replace this with a raw /in/ DOM scan.
        # -------------------------------------------------
        self.company_page = CompanyPage(
            self.page
        )

        # LinkedInProfilePageV2 creates a fresh temporary
        # profile tab for each candidate.
        #
        # Do not keep a reusable profile Page here.
    # =====================================================
    # FALLBACK RECORD
    # =====================================================

    @staticmethod
    def _search_result_fallback(row, company, location):
        """
        LinkedIn may allow the authenticated people-search page
        while redirecting direct profile navigation to /authwall.

        The employee was already obtained from CompanyPage.get_profiles()
        on the company + location filtered people-search page.

        In that situation, preserve the employee in the CSV instead
        of silently dropping the profile.

        Profile-specific fields that were not available because of the
        authwall remain blank.
        """

        return {
            "full_name": row.get("full_name", ""),
            "headline": row.get("headline", ""),
            "location": row.get("location", ""),
            "company": row.get("company", ""),
            "email": "",
            "email_source": "",
            "profile_url": row.get("profile_url", ""),
            "linked_email_id": "",
            "search_company": company,
            "search_location": location,
        }

    # =====================================================
    # MAIN WORKFLOW
    # =====================================================

    def run(
        self,
        company,
        location,
        max_profiles=1
    ):

        print("=" * 70)
        print("LINKEDIN SEARCH WORKFLOW V2")
        print("=" * 70)

        print(
            "Company:",
            company
        )

        print(
            "Location:",
            location
        )

        print(
            "Maximum profiles:",
            max_profiles
        )

        results = []
        seen_urls = set()
        page_no = 1

        # -------------------------------------------------
        # A - Search Company
        # -------------------------------------------------

        print("=" * 60)
        print("A - Searching company")
        print("=" * 60)

        self.company_page.search_company(
            company
        )

        print(
            "Company search completed."
        )

        # -------------------------------------------------
        # B - Open Company
        # -------------------------------------------------

        print("=" * 60)
        print("B - Opening company")
        print("=" * 60)

        found = (
            self.company_page
            .open_company_result(
                company
            )
        )

        print(
            "Company found:",
            found
        )

        if not found:

            print(
                "Company not found."
            )

            return self._finish(
                results,
                company,
                location
            )

        # -------------------------------------------------
        # C - Open Employees
        # -------------------------------------------------

        print("=" * 60)
        print("C - Opening employees")
        print("=" * 60)

        opened = (
            self.company_page
            .open_employees_page()
        )

        print(
            "Employees page:",
            opened
        )

        # -------------------------------------------------
        # V2 EMPLOYEE SEARCH RECOVERY
        #
        # LinkedIn may redirect the currentCompany people
        # search through /ssr-login/remember-me-auto-login
        # even though the authenticated feed session works.
        #
        # Do not immediately terminate the workflow.
        # Re-establish the authenticated company page and
        # retry the existing CompanyPage employee navigation.
        # -------------------------------------------------

        if not opened:

            current_url = self.page.url.lower()

            if (
                "/ssr-login/" in current_url
                or "remember-me-auto-login" in current_url
                or "/login" in current_url
            ):

                print("=" * 60)
                print(
                    "EMPLOYEE SEARCH REDIRECT RECOVERY"
                )
                print("=" * 60)

                print(
                    "Redirected employee URL:",
                    self.page.url
                )

                try:

                    # -------------------------------------------------
                    # Return to the authenticated LinkedIn feed.
                    # -------------------------------------------------

                    self.page.goto(
                        "https://www.linkedin.com/feed/",
                        wait_until="domcontentloaded",
                        timeout=60000
                    )

                    self.page.wait_for_timeout(
                        3000
                    )

                    print(
                        "Recovery feed URL:",
                        self.page.url
                    )

                    if (
                        "/feed" in self.page.url.lower()
                        and "/login" not in self.page.url.lower()
                    ):

                        print(
                            "Authenticated feed recovered."
                        )

                        # -------------------------------------------------
                        # Repeat the existing V2 company-search flow.
                        #
                        # We are NOT replacing CompanyPage.
                        # -------------------------------------------------

                        self.company_page.search_company(
                            company
                        )

                        found_again = (
                            self.company_page
                            .open_company_result(
                                company
                            )
                        )

                        print(
                            "Company recovery result:",
                            found_again
                        )

                        if found_again:

                            opened = (
                                self.company_page
                                .open_employees_page()
                            )

                            print(
                                "Employee recovery result:",
                                opened
                            )

                except Exception as ex:

                    print(
                        "Employee search recovery failed:",
                        repr(ex)
                    )

        # -------------------------------------------------
        # Final employee-search failure
        # -------------------------------------------------

        if not opened:

            print(
                "Employees page not found."
            )

            return self._finish(
                results,
                company,
                location
            )

        # -------------------------------------------------
        # D - Apply Location
        # -------------------------------------------------

        print("=" * 60)
        print("D - Applying location")
        print("=" * 60)

        location_applied = (
            self.company_page.apply_location(
                location
            )
        )

        print(
            "Location filter result:",
            location_applied
        )

        if not location_applied:

            print(
                "ERROR: Location filter was not successfully applied."
            )

            print(
                "SAFE STOP: Refusing to process an "
                "unfiltered employee search."
            )

            return self._finish(
                results,
                company,
                location
            )

        print(
            "Location applied successfully."
        )


        # -------------------------------------------------
        # E - Collect Employees
        #
        # CompanyPage.get_profiles() is intentionally retained.
        #
        # This is the working extraction logic that produced:
        #
        #   Vamshi Krishna Kota
        #   Veena D. Gangadhariah
        #   David Cooper
        #
        # on the SmartWorks, LLC + New Jersey search page.
        # -------------------------------------------------

        while len(results) < max_profiles:

            if should_stop():

                print(
                    "STOP requested."
                )

                break

            print("=" * 60)
            print(
                f"E - Reading employee page {page_no}"
            )
            print("=" * 60)

            page_results = (
                self.company_page
                .get_profiles(
                    company,
                    location
                )
            )

            print(
                "Profiles extracted:",
                len(page_results)
            )

            if not page_results:

                print(
                    "No employee profiles found on this page."
                )

            # -------------------------------------------------
            # Process ALL employees returned from CompanyPage
            # -------------------------------------------------

            print("Candidates returned by CompanyPage:", len(page_results))

            for candidate_index, row in enumerate(
                page_results,
                start=1
            ):

                if should_stop():
                    print("STOP requested.")
                    break

                print("=" * 60)
                print(
                    f"PROCESSING CANDIDATE "
                    f"{candidate_index} "
                    f"OF {len(page_results)}"
                )
                print("=" * 60)

                # -------------------------------------------------
                # FREEZE THIS CANDIDATE'S URL.
                #
                # This must become a plain string before any
                # profile navigation occurs.
                # -------------------------------------------------

                candidate_url = str(
                    row.get(
                        "profile_url",
                        ""
                    )
                ).strip()

                if not candidate_url:
                    print(
                        "SKIP - candidate has no profile URL."
                    )
                    continue

                if candidate_url in seen_urls:
                    print(
                        "SKIP - duplicate profile URL:",
                        candidate_url
                    )
                    continue

                seen_urls.add(
                    candidate_url
                )

                print(
                    "Candidate profile URL:",
                    candidate_url
                )

                # -------------------------------------------------
                # Immutable handoff value.
                # -------------------------------------------------

                requested_profile_url = (
                    candidate_url
                )

                print(
                    "Profile URL handed to "
                    "LinkedInProfilePageV2:",
                    requested_profile_url
                )

                try:

                    # -------------------------------------------------
                    # IMPORTANT:
                    #
                    # self.page belongs to the employee-search page.
                    #
                    # self.profile_page is the dedicated controller page
                    # created in SearchWorkflowV2.__init__().
                    # -------------------------------------------------

                    # Keep self.page as the authoritative
                    # company + location employee-search page.
                    #
                    # LinkedInProfilePageV2 creates a fresh
                    # temporary profile tab for this candidate.
                    profile = LinkedInProfilePageV2(
                        self.page
                    )

                    print(
                        "OPEN_PROFILE ARGUMENT:",
                        requested_profile_url
                    )

                    profile_opened = (
                        profile.open_profile(
                            requested_profile_url
                        )
                    )

                    if not profile_opened:

                        print(
                            "PROFILE PAGE COULD NOT BE OPENED"
                        )

                        print(
                            "REJECT - profile could not "
                            "be safely verified."
                        )

                        continue

                    # -------------------------------------------------
                    # Verify that the actual browser page is the SAME
                    # profile requested for this candidate.
                    # -------------------------------------------------

                    actual_browser_url = ""

                    try:
                        actual_browser_url = (
                            profile.page.url
                        )
                    except Exception as ex:
                        print(
                            "Could not read actual profile URL:",
                            repr(ex)
                        )

                    print(
                        "REQUESTED PROFILE URL:",
                        requested_profile_url
                    )

                    print(
                        "ACTUAL PROFILE PAGE URL:",
                        actual_browser_url
                    )

                    def canonical_profile_url(value):

                        if not value:
                            return ""

                        value = str(
                            value
                        ).strip()

                        if value.startswith("/"):
                            value = (
                                "https://www.linkedin.com"
                                + value
                            )

                        return (
                            value
                            .split("?")[0]
                            .split("#")[0]
                            .rstrip("/")
                            .lower()
                        )

                    requested_canonical = (
                        canonical_profile_url(
                            requested_profile_url
                        )
                    )

                    actual_canonical = (
                        canonical_profile_url(
                            actual_browser_url
                        )
                    )

                    if (
                        not actual_canonical
                        or actual_canonical
                        != requested_canonical
                    ):

                        print(
                            "REJECT - opened profile URL "
                            "does not match requested "
                            "candidate URL."
                        )

                        print(
                            "Requested canonical URL:",
                            requested_canonical
                        )

                        print(
                            "Actual canonical URL:",
                            actual_canonical
                        )

                        continue

                    # -------------------------------------------------
                    # Extract actual profile data.
                    # -------------------------------------------------

                    data = profile.get_profile()

                    if not data.get(
                        "full_name"
                    ):

                        print(
                            "REJECT - profile opened but "
                            "no profile name was extracted."
                        )

                        continue

                    actual_company = (
                        data.get(
                            "company",
                            ""
                        )
                    )

                    actual_location = (
                        data.get(
                            "location",
                            ""
                        )
                    )

                    requested_company_normalized = (
                        normalize_company(
                            company
                        )
                    )

                    actual_company_normalized = (
                        normalize_company(
                            actual_company
                        )
                    )

                    requested_location_normalized = (
                        normalize_location(
                            location
                        )
                    )

                    actual_location_normalized = (
                        normalize_location(
                            actual_location
                        )
                    )

                    company_matches = (
                        bool(
                            actual_company_normalized
                        )
                        and
                        actual_company_normalized
                        ==
                        requested_company_normalized
                    )

                    location_matches = (
                        bool(
                            actual_location_normalized
                        )
                        and
                        bool(
                            requested_location_normalized
                        )
                        and
                        requested_location_normalized
                        in
                        actual_location_normalized
                    )

                    print(
                        "PROFILE COMPANY:",
                        repr(actual_company)
                    )

                    print(
                        "REQUESTED COMPANY:",
                        repr(company)
                    )

                    print(
                        "COMPANY MATCH:",
                        company_matches
                    )

                    print(
                        "PROFILE LOCATION:",
                        repr(actual_location)
                    )

                    print(
                        "REQUESTED LOCATION:",
                        repr(location)
                    )

                    print(
                        "LOCATION MATCH:",
                        location_matches
                    )

                    # -------------------------------------------------
                    # STRICT ACCEPTANCE
                    # -------------------------------------------------

                    if not company_matches:

                        print(
                            "REJECTED - PROFILE COMPANY MISMATCH"
                        )

                        print(
                            "Continuing to next candidate..."
                        )

                        continue

                    if not location_matches:

                        print(
                            "REJECTED - PROFILE LOCATION MISMATCH"
                        )

                        print(
                            "Continuing to next candidate..."
                        )

                        continue

                    data["search_company"] = (
                        company
                    )

                    data["search_location"] = (
                        location
                    )

                    # Always preserve the exact candidate URL.
                    data["profile_url"] = (
                        requested_profile_url
                    )

                    results.append(
                        data
                    )

                    print(
                        "PROFILE VALIDATION PASSED"
                    )

                    print(
                        "VALID PROFILE COLLECTED"
                    )

                    print(
                        "Profiles collected so far:",
                        len(results)
                    )

                    try:

                        autosave = Exporter.export_csv(
                            results,
                            f"{company}_{location}"
                            f"_v2_autosave.csv"
                        )

                        print(
                            "Autosave:",
                            autosave
                        )

                    except Exception as ex:

                        print(
                            "Autosave failed:",
                            repr(ex)
                        )

                    if (
                        len(results)
                        >= max_profiles
                    ):

                        print(
                            "Maximum profile limit reached."
                        )

                        break

                except Exception as ex:

                    print(
                        "Profile processing failed:",
                        repr(ex)
                    )

                    print(
                        "REJECT - profile could not "
                        "be verified safely."
                    )

                    print(
                        "Continuing to next candidate..."
                    )

                    continue

            # -------------------------------------------------
            # Maximum reached after exhausting candidates
            # -------------------------------------------------

            if len(results) >= max_profiles:
                break

            # -------------------------------------------------
            # Only move to the next LinkedIn employee page after
            # every candidate on the current page has been processed.
            # -------------------------------------------------

            print("=" * 60)
            print("CURRENT EMPLOYEE PAGE EXHAUSTED")
            print("Profiles collected so far:", len(results))
            print("Trying next employee page...")
            print("=" * 60)

            has_next = self.company_page.next_page()

            print("Next page:", has_next)

            if not has_next:
                print("No more employee pages.")
                break

            page_no += 1

        # -------------------------------------------------
        # Final export
        # -------------------------------------------------

        return self._finish(
            results,
            company,
            location
        )

    # =====================================================
    # FINAL EXPORT
    # =====================================================

    def _finish(
        self,
        results,
        company,
        location
    ):

        print("=" * 70)
        print(
            "V2 WORKFLOW FINISHED"
        )
        print("=" * 70)

        print(
            "Profiles collected:",
            len(results)
        )

        output_file = None

        if results:

            try:

                output_file = (
                    Exporter.export_csv(
                        results,
                        f"{company}_{location}_v2.csv"
                    )
                )

                print(
                    "Final CSV:",
                    output_file
                )

            except Exception as ex:

                print(
                    "Final export failed:",
                    repr(ex)
                )

        return {
            "results": results,
            "count": len(results),
            "csv": output_file
        }
