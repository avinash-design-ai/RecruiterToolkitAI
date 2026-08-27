from pages.company_page import CompanyPage
from pages.linkedin_profile_page_v2 import LinkedInProfilePageV2

from automation.exporter import Exporter
from automation.search_controller import should_stop


class SearchWorkflowV2:

    def __init__(self, page):

        self.page = page

        # Existing authenticated LinkedIn page.
        self.company_page = CompanyPage(
            self.page
        )

        # Separate page for individual profiles.
        self.profile_page = self.page.context.new_page()

    # =====================================================
    # V2 SEARCH RESULT PROFILE EXTRACTION
    # =====================================================

    def get_search_result_profiles(self):

        print("=" * 60)
        print("V2 - Extracting actual employee search results")
        print("=" * 60)

        profiles = []
        seen_urls = set()

        # -------------------------------------------------
        # IMPORTANT
        #
        # DO NOT scan the whole page for:
        #
        #     a[href*='/in/']
        #
        # That also captures:
        # - mutual connections
        # - recommendations
        # - people from other LinkedIn sections
        # - unrelated profile links
        #
        # We first restrict the search to LinkedIn's
        # search-result containers.
        # -------------------------------------------------

        result_containers = self.page.locator(
            "li.reusable-search__result-container"
        )

        container_count = result_containers.count()

        print(
            "Search result containers found:",
            container_count
        )

        # -------------------------------------------------
        # Fallback selectors
        #
        # LinkedIn occasionally changes the outer result
        # container class. Try known result-card structures
        # before giving up.
        # -------------------------------------------------

        if container_count == 0:

            result_containers = self.page.locator(
                "li"
            )

            all_li_count = result_containers.count()

            print(
                "Fallback <li> containers:",
                all_li_count
            )

        # -------------------------------------------------
        # Process each result container
        # -------------------------------------------------

        for i in range(
            result_containers.count()
        ):

            try:

                container = (
                    result_containers.nth(i)
                )

                # -------------------------------------------------
                # Only links inside THIS result card.
                # -------------------------------------------------

                links = container.locator(
                    "a[href*='/in/']"
                )

                link_count = links.count()

                if link_count == 0:
                    continue

                selected_link = None
                selected_href = None

                # -------------------------------------------------
                # Find the profile link belonging to this card.
                # -------------------------------------------------

                for j in range(link_count):

                    link = links.nth(j)

                    href = (
                        link.get_attribute(
                            "href"
                        )
                    )

                    if not href:
                        continue

                    clean_url = (
                        href
                        .split("?")[0]
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

                    selected_link = link
                    selected_href = clean_url

                    break

                if not selected_link:
                    continue

                if selected_href in seen_urls:
                    continue

                # -------------------------------------------------
                # Get the complete result-card text.
                # -------------------------------------------------

                card_text = (
                    container.inner_text()
                    .strip()
                )

                if not card_text:
                    continue

                # -------------------------------------------------
                # A real LinkedIn people result normally contains
                # the profile name plus result-card metadata.
                #
                # We deliberately do NOT require a connection
                # degree because LinkedIn can omit it.
                # -------------------------------------------------

                lines = [
                    line.strip()
                    for line in card_text.splitlines()
                    if line.strip()
                ]

                if not lines:
                    continue

                # -------------------------------------------------
                # Determine the name from the profile link itself.
                #
                # This avoids taking random text from the card.
                # -------------------------------------------------

                link_text = (
                    selected_link.inner_text()
                    .strip()
                )

                link_lines = [
                    line.strip()
                    for line in link_text.splitlines()
                    if line.strip()
                ]

                if link_lines:

                    name = link_lines[0]

                else:

                    name = lines[0]

                # -------------------------------------------------
                # Clean LinkedIn connection markers.
                # -------------------------------------------------

                for marker in (
                    "• 1st",
                    "• 2nd",
                    "• 3rd",
                    "â€¢ 1st",
                    "â€¢ 2nd",
                    "â€¢ 3rd",
                    "Verified Profile",
                    "Verified profile"
                ):

                    name = (
                        name.replace(
                            marker,
                            ""
                        )
                        .strip()
                    )

                # -------------------------------------------------
                # Reject obviously invalid names.
                # -------------------------------------------------

                if not name:
                    continue

                if len(name) > 100:
                    continue

                if len(name.split()) > 12:
                    continue

                # -------------------------------------------------
                # IMPORTANT:
                #
                # We now have a profile URL that came from a
                # search-result card, NOT from an arbitrary /in/
                # link elsewhere on LinkedIn.
                # -------------------------------------------------

                seen_urls.add(
                    selected_href
                )

                profiles.append(
                    {
                        "full_name": name,
                        "profile_url": selected_href
                    }
                )

                print(
                    f"{len(profiles)}. {name}"
                )

            except Exception as ex:

                print(
                    "Result-card extraction failed:",
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
    # COMPANY VALIDATION
    # =====================================================

    @staticmethod
    def _normalize_company(value):

        if value is None:
            return ""

        value = str(value)

        value = (
            value
            .replace("\u00a0", " ")
            .strip()
            .lower()
        )

        # Normalize common punctuation.
        for char in (
            ",",
            ".",
            "-",
            "_",
            "/",
            "\\"
        ):

            value = value.replace(
                char,
                " "
            )

        value = " ".join(
            value.split()
        )

        return value

    def _company_matches(
        self,
        requested_company,
        profile
    ):

        requested = (
            self._normalize_company(
                requested_company
            )
        )

        actual = (
            self._normalize_company(
                profile.get(
                    "company",
                    ""
                )
            )
        )

        headline = (
            self._normalize_company(
                profile.get(
                    "headline",
                    ""
                )
            )
        )

        if not requested:
            return False

        if not actual:
            return False

        # -------------------------------------------------
        # PRIMARY RULE
        #
        # Exact normalized company match.
        # -------------------------------------------------

        if actual == requested:
            return True

        # -------------------------------------------------
        # Controlled SmartWorks compatibility.
        #
        # Some existing SmartWorks profiles identify
        # SmartWorks in their headline while LinkedIn's
        # extracted current-company field can show the
        # related iTech US Inc entity.
        #
        # This is deliberately NOT a generic substring
        # match for arbitrary companies.
        # -------------------------------------------------

        if requested == "smartworks llc":

            if (
                "smartworks llc" in headline
                or "smartworks" in headline
            ):

                return True

        return False

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

        # =================================================
        # A - SEARCH COMPANY
        # =================================================

        print("=" * 60)
        print("A - Searching company")
        print("=" * 60)

        self.company_page.search_company(
            company
        )

        print(
            "Company search completed."
        )

        # =================================================
        # B - OPEN COMPANY
        # =================================================

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

        # =================================================
        # C - OPEN EMPLOYEES
        # =================================================

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

        # =================================================
        # D - APPLY LOCATION
        # =================================================

        print("=" * 60)
        print("D - Applying location")
        print("=" * 60)

        self.company_page.apply_location(
            location
        )

        print(
            "Location applied."
        )

        # =================================================
        # E - COLLECT PROFILES
        # =================================================

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

            # -------------------------------------------------
            # IMPORTANT:
            #
            # Use the V2 card-aware extractor.
            #
            # DO NOT call:
            #
            #     company_page.get_profiles()
            #
            # because that method rejects multiline LinkedIn
            # result cards.
            # -------------------------------------------------

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

                if len(results) >= max_profiles:
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
                print("PROCESSING PROFILE")
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

                    # =================================================
                    # STRICT COMPANY VALIDATION
                    # =================================================

                    print(
                        "Requested company:",
                        company
                    )

                    print(
                        "Profile company:",
                        data.get(
                            "company",
                            ""
                        )
                    )

                    company_match = (
                        self._company_matches(
                            company,
                            data
                        )
                    )

                    if not company_match:

                        print(
                            "REJECTED PROFILE:"
                        )

                        print(
                            "Profile belongs to a different company."
                        )

                        print(
                            "Requested:",
                            company
                        )

                        print(
                            "Actual:",
                            data.get(
                                "company",
                                ""
                            )
                        )

                        continue

                    print(
                        "COMPANY VALIDATION PASSED"
                    )

                    # =================================================
                    # ADD SEARCH CONTEXT
                    # =================================================

                    data["search_company"] = (
                        company
                    )

                    data["search_location"] = (
                        location
                    )

                    # =================================================
                    # COLLECT ONLY AFTER VALIDATION
                    # =================================================

                    results.append(
                        data
                    )

                    print("=" * 60)
                    print("PROFILE COLLECTED")
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

                # =================================================
                # AUTOSAVE
                # =================================================

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

                if len(results) >= max_profiles:
                    break

            # =================================================
            # MAXIMUM REACHED
            # =================================================

            if len(results) >= max_profiles:
                break

            # =================================================
            # NEXT PAGE
            # =================================================

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

        # =================================================
        # FINISH
        # =================================================

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
        print("V2 WORKFLOW FINISHED")
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