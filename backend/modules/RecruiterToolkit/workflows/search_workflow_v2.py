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
    # V2 PROFILE EXTRACTION
    # =====================================================

    def get_search_result_profiles(self):

        print("=" * 60)
        print("V2 - Extracting actual employee search results")
        print("=" * 60)

        profiles = []
        seen_urls = set()

        # -------------------------------------------------
        # Keep the original broad visible /in/ extraction.
        #
        # Do NOT require:
        #   - 1st / 2nd / 3rd
        #   - multiline text
        #
        # LinkedIn can render valid profile links in
        # different formats.
        # -------------------------------------------------

        links = self.page.locator(
            "a[href*='/in/']:visible"
        )

        count = links.count()

        print(
            "Visible /in/ links:",
            count
        )

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

                if not clean_url.startswith("http"):

                    clean_url = (
                        "https://www.linkedin.com"
                        + clean_url
                    )

                # -------------------------------------------------
                # Deduplicate profile URLs.
                # -------------------------------------------------

                if clean_url in seen_urls:
                    continue

                text = (
                    link.inner_text()
                    .strip()
                )

                if not text:
                    continue

                # -------------------------------------------------
                # Original behavior:
                #
                # Use the visible link text as the profile name,
                # while rejecting obvious non-name / oversized
                # link text.
                #
                # We intentionally do NOT require a connection
                # degree marker or multiline result card.
                # -------------------------------------------------

                lines = [
                    line.strip()
                    for line in text.splitlines()
                    if line.strip()
                ]

                if not lines:
                    continue

                # First non-empty line is normally the person's
                # name when LinkedIn renders a multiline card.
                name = lines[0]

                # -------------------------------------------------
                # Clean connection-degree markers if LinkedIn
                # places them on the same line.
                # -------------------------------------------------

                name = (
                    name
                    .replace("• 1st", "")
                    .replace("• 2nd", "")
                    .replace("• 3rd", "")
                    .strip()
                )

                if not name:
                    continue

                # -------------------------------------------------
                # Preserve the original safeguards.
                # -------------------------------------------------

                if len(name) > 40:
                    continue

                if name.count(" ") > 4:
                    continue

                # -------------------------------------------------
                # Reject obvious non-profile link text.
                # -------------------------------------------------

                if name.lower() in (
                    "view profile",
                    "see profile",
                    "linkedin member",
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

        return {

            "results": results,

            "count": len(results),

            "csv": output_file

        }