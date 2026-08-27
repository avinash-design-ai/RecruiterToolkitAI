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
        # This is part of the original working V2 design.
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
        # IMPORTANT
        #
        # Do NOT depend on LinkedIn's connection-degree text.
        #
        # The old version depended on:
        #
        #     â€¢ 1st
        #     â€¢ 2nd
        #     â€¢ 3rd
        #
        # That is encoding-dependent and is the reason the
        # workflow can see /in/ links but extract ZERO profiles.
        #
        # Instead, identify actual /in/ links and inspect their
        # surrounding result-card/list-item structure.
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

                href = link.get_attribute("href")

                if not href:
                    continue

                # -------------------------------------------------
                # Normalize profile URL
                # -------------------------------------------------

                clean_url = (
                    href
                    .split("?")[0]
                    .strip()
                )

                if "/in/" not in clean_url:
                    continue

                if not clean_url.startswith("http"):

                    clean_url = (
                        "https://www.linkedin.com"
                        + clean_url
                    )

                if clean_url in seen_urls:
                    continue

                # -------------------------------------------------
                # First attempt:
                #
                # The link itself frequently contains the person's
                # name.
                # -------------------------------------------------

                link_text = ""

                try:
                    link_text = (
                        link.inner_text()
                        .strip()
                    )
                except Exception:
                    link_text = ""

                # -------------------------------------------------
                # Collect possible text from surrounding result card.
                #
                # LinkedIn DOM changes frequently, so use several
                # levels of ancestors rather than one brittle selector.
                # -------------------------------------------------

                candidate_texts = []

                if link_text:
                    candidate_texts.append(
                        link_text
                    )

                # -------------------------------------------------
                # Try closest LI.
                # -------------------------------------------------

                try:

                    li = link.locator(
                        "xpath=ancestor::li[1]"
                    )

                    if li.count():

                        li_text = (
                            li.first.inner_text()
                            .strip()
                        )

                        if li_text:
                            candidate_texts.append(
                                li_text
                            )

                except Exception:
                    pass

                # -------------------------------------------------
                # Try common LinkedIn result-card ancestors.
                # -------------------------------------------------

                ancestor_selectors = [
                    "xpath=ancestor::div[contains(@class,'entity-result')][1]",
                    "xpath=ancestor::div[contains(@class,'search-result')][1]",
                    "xpath=ancestor::div[contains(@class,'reusable-search__result-container')][1]",
                ]

                for selector in ancestor_selectors:

                    try:

                        ancestor = link.locator(
                            selector
                        )

                        if ancestor.count():

                            text = (
                                ancestor.first
                                .inner_text()
                                .strip()
                            )

                            if text:
                                candidate_texts.append(
                                    text
                                )

                    except Exception:
                        continue

                # -------------------------------------------------
                # Determine employee name.
                #
                # Prefer aria-label/title because LinkedIn often
                # exposes the actual profile name there even when
                # rendered text contains extra information.
                # -------------------------------------------------

                name_candidates = []

                try:

                    aria_label = (
                        link.get_attribute(
                            "aria-label"
                        )
                        or ""
                    ).strip()

                    if aria_label:
                        name_candidates.append(
                            aria_label
                        )

                except Exception:
                    pass

                try:

                    title = (
                        link.get_attribute(
                            "title"
                        )
                        or ""
                    ).strip()

                    if title:
                        name_candidates.append(
                            title
                        )

                except Exception:
                    pass

                # -------------------------------------------------
                # Parse surrounding text.
                # -------------------------------------------------

                for candidate in candidate_texts:

                    if not candidate:
                        continue

                    lines = [
                        line.strip()
                        for line in candidate.splitlines()
                        if line.strip()
                    ]

                    for line in lines:

                        cleaned = (
                            self._clean_profile_name(
                                line
                            )
                        )

                        if cleaned:
                            name_candidates.append(
                                cleaned
                            )

                # -------------------------------------------------
                # Select best name candidate.
                # -------------------------------------------------

                name = ""

                for candidate in name_candidates:

                    cleaned = (
                        self._clean_profile_name(
                            candidate
                        )
                    )

                    if not cleaned:
                        continue

                    # Reject obvious UI/result metadata.
                    if self._looks_like_ui_text(
                        cleaned
                    ):
                        continue

                    # Reject excessively long text.
                    if len(cleaned) > 100:
                        continue

                    if len(cleaned.split()) > 12:
                        continue

                    name = cleaned
                    break

                # -------------------------------------------------
                # Last-resort fallback.
                #
                # If LinkedIn renders the name as the anchor's
                # complete text, use the first meaningful line.
                # -------------------------------------------------

                if not name and link_text:

                    lines = [
                        line.strip()
                        for line in link_text.splitlines()
                        if line.strip()
                    ]

                    for line in lines:

                        cleaned = (
                            self._clean_profile_name(
                                line
                            )
                        )

                        if not cleaned:
                            continue

                        if self._looks_like_ui_text(
                            cleaned
                        ):
                            continue

                        if len(cleaned) > 100:
                            continue

                        if len(cleaned.split()) > 12:
                            continue

                        name = cleaned
                        break

                # -------------------------------------------------
                # If we still cannot determine a name, don't add
                # a garbage profile.
                # -------------------------------------------------

                if not name:
                    print(
                        "Skipping /in/ link - "
                        "could not determine profile name:",
                        clean_url
                    )
                    continue

                # -------------------------------------------------
                # Deduplicate
                # -------------------------------------------------

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
    # PROFILE NAME CLEANING
    # =====================================================

    @staticmethod
    def _clean_profile_name(value):

        if not value:
            return ""

        value = value.strip()

        # -------------------------------------------------
        # Remove common LinkedIn connection markers.
        #
        # Handle both correctly decoded bullets and the
        # mojibake form found in earlier GitHub logs.
        # -------------------------------------------------

        replacements = [
            "• 1st",
            "• 2nd",
            "• 3rd",
            "â€¢ 1st",
            "â€¢ 2nd",
            "â€¢ 3rd",
            "· 1st",
            "· 2nd",
            "· 3rd",
        ]

        for marker in replacements:

            value = (
                value.replace(
                    marker,
                    ""
                )
            )

        value = value.strip()

        # -------------------------------------------------
        # If a line contains obvious connection information,
        # keep only the portion before it.
        # -------------------------------------------------

        connection_markers = [
            " • 1st",
            " • 2nd",
            " • 3rd",
            " â€¢ 1st",
            " â€¢ 2nd",
            " â€¢ 3rd",
            " · 1st",
            " · 2nd",
            " · 3rd",
        ]

        for marker in connection_markers:

            if marker in value:

                value = (
                    value.split(
                        marker,
                        1
                    )[0]
                    .strip()
                )

        return value

    # =====================================================
    # UI TEXT FILTER
    # =====================================================

    @staticmethod
    def _looks_like_ui_text(value):

        if not value:
            return True

        lower = value.lower().strip()

        blocked_exact = {
            "connect",
            "follow",
            "message",
            "more",
            "see more",
            "send message",
            "contact info",
            "linkedin member",
            "view profile",
            "show more",
            "next",
            "previous",
        }

        if lower in blocked_exact:
            return True

        blocked_contains = (
            "connection degree",
            "followers",
            "mutual connections",
            "people also viewed",
            "linkedin member",
        )

        if any(
            token in lower
            for token in blocked_contains
        ):
            return True

        # A real person's name normally does not look like
        # a complete URL.
        if lower.startswith(
            (
                "http://",
                "https://"
            )
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

        print(
            "Applying location:",
            location
        )

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

            # -------------------------------------------------
            # IMPORTANT:
            #
            # V2 uses its own employee-result extraction.
            #
            # We do NOT use CompanyPage.get_profiles().
            #
            # The reason is that LinkedIn exposes many /in/
            # links which are not actual result cards.
            # -------------------------------------------------

            page_results = (
                self.get_search_result_profiles()
            )

            print(
                "V2 profiles extracted:",
                len(page_results)
            )

            # -------------------------------------------------
            # If LinkedIn returned no profiles, do not immediately
            # destroy the workflow or change the profile/email logic.
            #
            # Try one controlled DOM refresh/wait before moving on.
            # -------------------------------------------------

            if not page_results:

                print(
                    "No profiles extracted on current DOM."
                )

                try:

                    print(
                        "Waiting for employee results "
                        "to stabilize..."
                    )

                    self.page.wait_for_timeout(
                        2500
                    )

                except Exception:
                    pass

                # Re-read after the short stabilization wait.

                page_results = (
                    self.get_search_result_profiles()
                )

                print(
                    "V2 profiles extracted after "
                    "stabilization:",
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

                    # -------------------------------------------------
                    # DO NOT change this.
                    #
                    # LinkedInProfilePageV2 contains the original
                    # working profile/email extraction logic.
                    # -------------------------------------------------

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

                    # -------------------------------------------------
                    # Existing profile extraction.
                    #
                    # This preserves:
                    #
                    # email
                    # email_source
                    # linked_email_id
                    #
                    # including collection of multiple publicly
                    # visible email addresses.
                    # -------------------------------------------------

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
                #
                # Preserve the original working behavior.
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