from pages.company_page import CompanyPage
from pages.linkedin_profile_page_v2 import LinkedInProfilePageV2

from automation.exporter import Exporter
from automation.search_controller import should_stop


class SearchWorkflowV2:

    def __init__(self, page):

        self.page = page

        # Existing logged-in LinkedIn page.
        # DO NOT create another search page.
        self.company_page = CompanyPage(
            self.page
        )

        # Separate page for individual profiles.
        self.profile_page = self.page.context.new_page()

    # =====================================================
    # NORMALIZATION HELPERS
    # =====================================================

    @staticmethod
    def _normalize_company(value):

        if not value:
            return ""

        value = str(value).lower().strip()

        # Normalize common punctuation / spacing differences.
        value = value.replace("&", "and")
        value = value.replace(",", " ")
        value = value.replace(".", " ")
        value = value.replace("-", " ")
        value = value.replace("_", " ")

        value = " ".join(
            value.split()
        )

        return value

    @classmethod
    def _company_matches(
        cls,
        actual_company,
        requested_company
    ):

        actual = cls._normalize_company(
            actual_company
        )

        requested = cls._normalize_company(
            requested_company
        )

        if not actual or not requested:
            return False

        # Exact normalized match.
        if actual == requested:
            return True

        # Handle common LinkedIn/company-name variations.
        #
        # Example:
        # SmartWorks, LLC
        # SmartWorks LLC
        #
        if actual.rstrip(".") == requested.rstrip("."):
            return True

        # Do not use loose substring matching here.
        #
        # This is intentional.
        #
        # We do NOT want:
        # SmartWorks
        # SmartWorks International
        # SmartWorks Technologies
        #
        # to accidentally pass as the requested company.
        #
        actual_tokens = set(
            actual.split()
        )

        requested_tokens = set(
            requested.split()
        )

        return actual_tokens == requested_tokens

    # =====================================================
    # V2 PROFILE EXTRACTION
    # =====================================================

    def get_search_result_profiles(
        self,
        retry_count=3
    ):

        print("=" * 60)
        print("V2 - Extracting actual employee search results")
        print("=" * 60)

        profiles = []
        seen_urls = set()

        links = None
        count = 0

        # -------------------------------------------------
        # LinkedIn can temporarily render the search page
        # before the profile links become available.
        #
        # Retry a few times rather than immediately
        # declaring that there are zero profiles.
        # -------------------------------------------------

        for attempt in range(1, retry_count + 1):

            try:

                print(
                    f"Profile-link extraction attempt "
                    f"{attempt}/{retry_count}"
                )

                self.page.wait_for_timeout(
                    2000
                )

                links = self.page.locator(
                    "a[href*='/in/']:visible"
                )

                count = links.count()

                print(
                    "Visible /in/ links:",
                    count
                )

                if count > 0:
                    break

            except Exception as ex:

                print(
                    "Profile-link wait failed:",
                    repr(ex)
                )

            if attempt < retry_count:

                try:

                    self.page.wait_for_timeout(
                        3000
                    )

                except Exception:
                    pass

        # -------------------------------------------------
        # If LinkedIn still has no visible /in/ links,
        # return an empty page result.
        #
        # IMPORTANT:
        # We do NOT switch to company_page.get_profiles()
        # because that method is intentionally avoided in
        # V2.
        # -------------------------------------------------

        if not links or count == 0:

            print(
                "WARNING: No visible employee profile links detected."
            )

            print("=" * 60)

            print(
                "Actual employee profiles extracted:",
                0
            )

            print("=" * 60)

            return profiles

        # -------------------------------------------------
        # Preserve the original broad visible /in/
        # extraction behavior.
        #
        # IMPORTANT:
        #
        # We intentionally do NOT require:
        #   - 1st / 2nd / 3rd
        #   - multiline text
        #   - specific result-card selectors
        #
        # LinkedIn changes its DOM frequently and valid
        # employee result links can be rendered in different
        # formats.
        #
        # Company correctness is enforced later after the
        # actual profile is opened.
        # -------------------------------------------------

        for i in range(count):

            try:

                link = links.nth(i)

                href = link.get_attribute(
                    "href"
                )

                if not href:
                    continue

                href = href.strip()

                clean_url = (
                    href
                    .split("?")[0]
                    .split("#")[0]
                    .strip()
                )

                if "/in/" not in clean_url:
                    continue

                if not clean_url.startswith(
                    "http"
                ):

                    clean_url = (
                        "https://www.linkedin.com"
                        + clean_url
                    )

                # -------------------------------------------------
                # Normalize trailing slash.
                # -------------------------------------------------

                clean_url = clean_url.rstrip(
                    "/"
                ) + "/"

                # -------------------------------------------------
                # Deduplicate profile URLs.
                # -------------------------------------------------

                if clean_url in seen_urls:
                    continue

                text = ""

                try:

                    text = (
                        link.inner_text()
                        .strip()
                    )

                except Exception:
                    text = ""

                if not text:
                    continue

                # -------------------------------------------------
                # Extract first meaningful line as name.
                # -------------------------------------------------

                lines = [
                    line.strip()
                    for line in text.splitlines()
                    if line.strip()
                ]

                if not lines:
                    continue

                name = lines[0]

                # -------------------------------------------------
                # Remove connection-degree markers if LinkedIn
                # places them on the same line.
                #
                # Handle both correctly encoded and mojibake
                # versions because CI/browser environments can
                # expose either representation.
                # -------------------------------------------------

                degree_markers = (
                    "• 1st",
                    "• 2nd",
                    "• 3rd",
                    "â€¢ 1st",
                    "â€¢ 2nd",
                    "â€¢ 3rd",
                )

                for marker in degree_markers:

                    name = name.replace(
                        marker,
                        ""
                    )

                name = name.strip()

                if not name:
                    continue

                # -------------------------------------------------
                # Preserve original safeguards.
                # -------------------------------------------------

                if len(name) > 100:
                    continue

                if len(name.split()) > 12:
                    continue

                # -------------------------------------------------
                # Reject obvious non-profile link text.
                # -------------------------------------------------

                if name.lower() in (
                    "view profile",
                    "see profile",
                    "linkedin member",
                    "linkedin",
                ):
                    continue

                seen_urls.add(
                    clean_url
                )

                profiles.append(
                    {
                        "full_name": name,
                        "profile_url": clean_url
                    }
                )

                print(
                    f"{len(profiles)}. "
                    f"{name}"
                )

            except Exception as ex:

                print(
                    "Profile extraction failed:",
                    repr(ex)
                )

        print("=" * 60)

        print(
            "Actual employee profiles extracted:",
            len(profiles)
        )

        print("=" * 60)

        return profiles

    # =====================================================
    # PROFILE COMPANY VALIDATION
    # =====================================================

    def _validate_profile_company(
        self,
        data,
        requested_company
    ):

        actual_company = (
            data.get(
                "company",
                ""
            )
            if isinstance(data, dict)
            else ""
        )

        print(
            "Requested company:",
            requested_company
        )

        print(
            "Profile company:",
            actual_company
        )

        # -------------------------------------------------
        # HARD REJECTION:
        #
        # If LinkedIn profile extraction gives us a company
        # and it does not match the requested company, reject
        # the profile.
        #
        # This is the critical protection against contacts
        # from other companies appearing in the CSV.
        # -------------------------------------------------

        if not actual_company:

            print(
                "REJECTED PROFILE:"
            )

            print(
                "Profile company could not be verified."
            )

            print(
                "The profile will NOT be added to results."
            )

            return False

        if not self._company_matches(
            actual_company,
            requested_company
        ):

            print(
                "REJECTED PROFILE:"
            )

            print(
                "Profile belongs to a different company."
            )

            print(
                "Requested:",
                requested_company
            )

            print(
                "Actual:",
                actual_company
            )

            return False

        print(
            "COMPANY VALIDATION PASSED"
        )

        return True

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
        # E - Collect Profiles
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
                self.get_search_result_profiles()
            )

            print(
                "V2 profiles extracted:",
                len(page_results)
            )

            # -------------------------------------------------
            # If no profiles were rendered, try next page
            # only through CompanyPage's existing pagination.
            # -------------------------------------------------

            if not page_results:

                print(
                    "No profile links available on this page."
                )

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

                continue

            # -------------------------------------------------
            # Process profiles
            # -------------------------------------------------

            for row in page_results:

                if should_stop():

                    print(
                        "STOP requested."
                    )

                    break

                profile_url = (
                    row.get(
                        "profile_url",
                        ""
                    )
                )

                if not profile_url:
                    continue

                if profile_url in seen_urls:

                    print(
                        "Skipping duplicate profile:",
                        profile_url
                    )

                    continue

                # Mark as attempted so the same profile is not
                # repeatedly processed across pages.
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

                try:

                    profile = (
                        LinkedInProfilePageV2(
                            self.profile_page
                        )
                    )

                    opened = (
                        profile.open_profile(
                            profile_url
                        )
                    )

                    if not opened:

                        print(
                            "Unable to open profile."
                        )

                        continue

                    data = (
                        profile.get_profile()
                    )

                    if not isinstance(
                        data,
                        dict
                    ):

                        print(
                            "Profile extraction did not return a dictionary."
                        )

                        continue

                    # -------------------------------------------------
                    # CRITICAL COMPANY VALIDATION
                    #
                    # Never trust the search result link alone.
                    #
                    # The actual opened LinkedIn profile must belong
                    # to the requested company.
                    # -------------------------------------------------

                    if not self._validate_profile_company(
                        data,
                        company
                    ):

                        continue

                    # -------------------------------------------------
                    # Add search context
                    # -------------------------------------------------

                    data["search_company"] = (
                        company
                    )

                    data["search_location"] = (
                        location
                    )

                    # -------------------------------------------------
                    # Add result
                    # -------------------------------------------------

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

                # -------------------------------------------------
                # Autosave
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
            # Next page
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
        # Final
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

        else:

            print(
                "No valid profiles collected."
            )

        return {

            "results": results,

            "count": len(results),

            "csv": output_file

        }