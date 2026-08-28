from pages.company_page import CompanyPage
from pages.linkedin_profile_page_v2 import LinkedInProfilePageV2

from automation.exporter import Exporter
from automation.search_controller import should_stop


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

        # Separate page for individual profile navigation.
        # This preserves the existing V2 profile/email extractor.
        self.profile_page = self.page.context.new_page()

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

        self.company_page.apply_location(
            location
        )

        print(
            "Location applied."
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
            # Process employees from CompanyPage
            # -------------------------------------------------

            for row in page_results:

                if should_stop():

                    print(
                        "STOP requested."
                    )

                    break

                # -------------------------------------------------
                # COMPANY VALIDATION BEFORE PROFILE NAVIGATION
                #
                # LinkedIn's people-search results can occasionally
                # contain profiles whose current company does not
                # match the requested company.
                #
                # IMPORTANT:
                # Validate the employee search-result company BEFORE
                # opening the individual LinkedIn profile.
                #
                # If the company does not match:
                #
                #   - DO NOT open the profile
                #   - DO NOT run LinkedInProfilePageV2
                #   - DO NOT create a fallback record
                #   - DO NOT add it to the CSV
                #
                # This prevents unrelated profiles such as:
                #
                #   Quantix, Inc.
                #   NTT DATA Services
                #
                # from being collected during a SmartWorks, LLC search.
                # -------------------------------------------------

                row_company = (
                    row.get(
                        "company",
                        ""
                    )
                )

                requested_company_normalized = (
                    normalize_company(
                        company
                    )
                )

                row_company_normalized = (
                    normalize_company(
                        row_company
                    )
                )

                print(
                    "Company validation:",
                    repr(row_company),
                    "vs requested:",
                    repr(company)
                )

                if (
                    not row_company_normalized
                    or
                    row_company_normalized
                    != requested_company_normalized
                ):

                    print("=" * 60)
                    print(
                        "SKIPPING PROFILE - COMPANY MISMATCH"
                    )
                    print("=" * 60)

                    print(
                        "Profile:",
                        row.get(
                            "full_name",
                            ""
                        )
                    )

                    print(
                        "Profile company:",
                        row_company
                    )

                    print(
                        "Requested company:",
                        company
                    )

                    print(
                        "Profile will NOT be opened."
                    )

                    continue

                print(
                    "Company validation PASSED:",
                    row_company
                )

                profile_url = (
                    row.get(
                        "profile_url",
                        ""
                    )
                )

                if not profile_url:

                    continue

                if profile_url in seen_urls:

                    continue

                seen_urls.add(
                    profile_url
                )

                print("=" * 60)
                print(
                    "PROCESSING PROFILE"
                )
                print("=" * 60)

                print(
                    "Profile URL:",
                    profile_url
                )

                profile_opened = False

                try:

                    # -------------------------------------------------
                    # Existing V2 profile/email extraction.
                    #
                    # Do not replace LinkedInProfilePageV2.
                    # -------------------------------------------------

                    profile = (
                        LinkedInProfilePageV2(
                            self.profile_page
                        )
                    )

                    profile_opened = (
                        profile.open_profile(
                            profile_url
                        )
                    )

                    if profile_opened:

                        data = (
                            profile.get_profile()
                        )

                        # Safety check: do not write an empty profile
                        # if LinkedIn returned an unexpected page.
                        if not data.get("full_name"):

                            print(
                                "Profile opened but no profile name "
                                "was extracted."
                            )

                            profile_opened = False

                        else:

                            data["search_company"] = (
                                company
                            )

                            data["search_location"] = (
                                location
                            )

                            results.append(
                                data
                            )

                            print("=" * 60)
                            print(
                                "PROFILE COLLECTED"
                            )
                            print("=" * 60)

                            for key, value in data.items():

                                print(
                                    f"{key}: {value}"
                                )

                except Exception as ex:

                    print(
                        "Profile processing failed:",
                        repr(ex)
                    )

                    profile_opened = False

                # -------------------------------------------------
                # AUTHWALL / profile access fallback
                #
                # IMPORTANT:
                # The employee already came from the correctly
                # filtered CompanyPage people-search result.
                #
                # Therefore we must NOT discard the employee merely
                # because direct profile navigation is blocked.
                # -------------------------------------------------

                if not profile_opened:

                    print("=" * 60)
                    print(
                        "PROFILE PAGE NOT ACCESSIBLE"
                    )
                    print("=" * 60)

                    print(
                        "Keeping employee from search result."
                    )

                    fallback = (
                        self._search_result_fallback(
                            row,
                            company,
                            location
                        )
                    )

                    results.append(
                        fallback
                    )

                    print("=" * 60)
                    print(
                        "SEARCH RESULT PROFILE RETAINED"
                    )
                    print("=" * 60)

                    for key, value in fallback.items():

                        print(
                            f"{key}: {value}"
                        )

                    print(
                        "Email unavailable because "
                        "LinkedIn profile navigation was blocked."
                    )

                # -------------------------------------------------
                # Autosave after every retained employee
                # -------------------------------------------------

                if results:

                    try:

                        autosave = (
                            Exporter.export_csv(
                                results,
                                f"{company}_{location}_v2_autosave.csv"
                            )
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

                # -------------------------------------------------
                # Maximum reached
                # -------------------------------------------------

                if len(results) >= max_profiles:

                    break

            # -------------------------------------------------
            # Maximum reached
            # -------------------------------------------------

            if len(results) >= max_profiles:

                break

            # -------------------------------------------------
            # Next employee page
            # -------------------------------------------------

            print(
                "Trying next employee page..."
            )

            has_next = (
                self.company_page
                .next_page()
            )

            print(
                "Next page:",
                has_next
            )

            if not has_next:

                print(
                    "No more employee pages."
                )

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
