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


def search_result_supports_company(search_result_text, requested_company):
    """Allow visible search-result company association in addition to exact profile company."""
    result = normalize_company(search_result_text)
    requested = normalize_company(requested_company)
    if not result or not requested:
        return False
    if requested in result:
        return True
    generic = {"inc","llc","ltd","corp","corporation","company","co","limited","the"}
    tokens = [t for t in requested.split() if t not in generic and len(t) >= 3]
    return bool(tokens and all(t in result.split() for t in tokens))



class SearchWorkflowProfilePage(LinkedInProfilePageV2):
    """
    Workflow-local navigation fix.

    The employee search page is NEVER used as the profile page.
    For every candidate we:
      1. stay on the authenticated employee-search page,
      2. find the exact candidate /in/ href,
      3. Ctrl-click that exact link and capture the newly opened tab,
      4. verify the new tab is the requested profile,
      5. let LinkedInProfilePageV2 handle extraction,
      6. close only the temporary profile tab.

    This preserves the working CompanyPage search/filter/pagination flow
    and prevents profile navigation from replacing the employee search page.
    """

    @staticmethod
    def _canonical_profile_url(value):
        if not value:
            return ""
        value = str(value).strip()
        if value.startswith("/"):
            value = "https://www.linkedin.com" + value
        return value.split("?")[0].split("#")[0].rstrip("/").lower()

    @staticmethod
    def _blocked_url(url):
        u = (url or "").lower()
        return (
            "/authwall" in u
            or "/login" in u
            or "/ssr-login/" in u
            or "remember-me-auto-login" in u
        )


    def _employee_search_page(self):
        """
        Locate the live authenticated company-scoped employee-search page.

        Do not assume self.page is still the search page: during profile
        extraction self.page is intentionally switched to a temporary profile
        tab. The browser context is the authoritative source.
        """
        try:
            context = self.page.context
        except Exception:
            return None

        pages = []
        try:
            pages = list(context.pages)
        except Exception:
            return None

        # Prefer a company people-search page. This also survives the case
        # where self.page is currently a profile tab or LinkedIn feed.
        for candidate in pages:
            try:
                if candidate.is_closed():
                    continue
                url = str(candidate.url or "")
                lower = url.lower()
                if (
                    "/search/results/people/" in lower
                    and "currentcompany=" in lower
                    and "/login" not in lower
                    and "/authwall" not in lower
                    and "/ssr-login" not in lower
                ):
                    print("Authenticated employee search page found in browser context:")
                    print(url)
                    return candidate
            except Exception:
                continue

        # Preserve the original-page fallback if it is still usable.
        try:
            original = getattr(self, "_original_profile_page", None)
            if original and not original.is_closed():
                lower = str(original.url or "").lower()
                if (
                    "/search/results/people/" in lower
                    and "currentcompany=" in lower
                ):
                    return original
        except Exception:
            pass

        print("No authenticated company-scoped employee-search page found in browser context.")
        return None


    def open_profile(self, profile_url):
        requested = self._canonical_profile_url(profile_url)
        if not requested or "/in/" not in requested:
            print("INVALID PROFILE URL:", profile_url)
            return False

        search_page = self._employee_search_page()
        if search_page is None:
            print("PROFILE OPEN FAILED: authenticated employee-search page is not available.")
            return False

        self._original_profile_page = search_page
        self.profile_url = str(profile_url).strip()

        print("PROFILE NAVIGATION MODE: authenticated search page -> exact link -> new tab")
        print("REQUESTED PROFILE:", self.profile_url)
        print("SEARCH PAGE REMAINS:", search_page.url)

        try:
            exact_link = None
            links = search_page.locator("a[href*='/in/']:visible")
            count = links.count()

            for i in range(count):
                try:
                    href = links.nth(i).get_attribute("href")
                    if self._canonical_profile_url(href) == requested:
                        exact_link = links.nth(i)
                        break
                except Exception:
                    continue

            if exact_link is None:
                print("EXACT EMPLOYEE PROFILE LINK NOT FOUND ON SEARCH PAGE.")
                return False

            print("EXACT EMPLOYEE PROFILE LINK FOUND.")

            # Capture the new tab explicitly. This is the important fix:
            # the authenticated employee-search page is not replaced.
            profile_page = None
            try:
                context = search_page.context
                # Use the browser-context page event so we capture the actual
                # new tab created by the authenticated LinkedIn click.
                with context.expect_page(timeout=15000) as page_info:
                    exact_link.click(modifiers=["Control"], timeout=15000)
                profile_page = page_info.value
            except Exception as ex:
                print("CTRL-CLICK NEW-TAB OPEN FAILED:", repr(ex))

            if profile_page is None:
                print("PROFILE OPEN FAILED: no new profile tab was created.")
                return False

            self._temporary_profile_page = profile_page
            self.page = profile_page

            try:
                profile_page.wait_for_load_state("domcontentloaded", timeout=30000)
            except Exception:
                pass

            try:
                profile_page.wait_for_timeout(2500)
            except Exception:
                pass

            actual = self._canonical_profile_url(profile_page.url)
            print("PROFILE TAB URL:", profile_page.url)

            if self._blocked_url(profile_page.url):
                print("AUTHWALL/LOGIN DETECTED ON PROFILE TAB.")
                print(
                    "Trying a fresh temporary-tab direct profile navigation "
                    "fallback without touching the employee-search page."
                )

                try:
                    if not profile_page.is_closed():
                        profile_page.close()
                except Exception:
                    pass

                self._temporary_profile_page = None

                try:
                    fallback_page = search_page.context.new_page()
                    self._temporary_profile_page = fallback_page
                    self.page = fallback_page

                    fallback_page.goto(
                        str(profile_url).strip(),
                        wait_until="domcontentloaded",
                        timeout=60000
                    )
                    fallback_page.wait_for_timeout(4000)

                    fallback_url = fallback_page.url
                    print("PROFILE DIRECT-FALLBACK URL:", fallback_url)

                    if (
                        not self._blocked_url(fallback_url)
                        and self._canonical_profile_url(fallback_url) == requested
                        and "/in/" in fallback_url.lower()
                    ):
                        print(
                            "EXACT AUTHENTICATED EMPLOYEE PROFILE OPENED "
                            "USING TEMPORARY DIRECT-NAVIGATION FALLBACK."
                        )
                        return True

                    print(
                        "DIRECT-NAVIGATION FALLBACK ALSO REACHED "
                        "AUTHWALL/LOGIN OR WRONG URL."
                    )

                    try:
                        if not fallback_page.is_closed():
                            fallback_page.close()
                    except Exception:
                        pass

                    self._temporary_profile_page = None
                    self.page = search_page

                except Exception as fallback_ex:
                    print(
                        "DIRECT-NAVIGATION PROFILE FALLBACK FAILED:",
                        repr(fallback_ex)
                    )

                    try:
                        if self._temporary_profile_page is not None:
                            if not self._temporary_profile_page.is_closed():
                                self._temporary_profile_page.close()
                    except Exception:
                        pass

                    self._temporary_profile_page = None
                    self.page = search_page

                return False

            if actual != requested:
                print("REJECTED: profile tab URL does not match requested candidate.")
                print("Requested:", requested)
                print("Actual:", actual)
                return False

            print("EXACT AUTHENTICATED EMPLOYEE PROFILE OPENED.")
            return True

        except Exception as ex:
            print("PROFILE NEW-TAB NAVIGATION FAILED:", repr(ex))
            return False


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


    # =====================================================
    # AUTHENTICATED EMPLOYEE SEARCH PAGE OWNERSHIP
    # =====================================================

    def _restore_employee_search_page(self):
        """
        Re-anchor BOTH SearchWorkflowV2.page and CompanyPage.page to the live
        authenticated company-scoped LinkedIn people-search tab.

        This is the critical state invariant for V2:

            self.page == self.company_page.page == employee-search Page

        Profile extraction is allowed to use a temporary profile tab, but that
        tab must never become the page used for the next candidate or for
        pagination.

        The method never navigates a tab. It only inspects existing Playwright
        context pages, so it cannot turn a working authenticated session into
        a login redirect.
        """
        context = None

        try:
            context = self.page.context
        except Exception:
            try:
                context = self.company_page.page.context
            except Exception:
                context = None

        if context is None:
            print("SEARCH PAGE RESTORE FAILED: browser context unavailable.")
            return False

        try:
            pages = list(context.pages)
        except Exception as ex:
            print("SEARCH PAGE RESTORE FAILED: could not inspect context pages:", repr(ex))
            return False

        valid_pages = []

        for candidate in pages:
            try:
                if candidate.is_closed():
                    continue

                url = str(candidate.url or "").strip()
                lower = url.lower()

                if (
                    "/search/results/people/" in lower
                    and "currentcompany=" in lower
                    and "/login" not in lower
                    and "/authwall" not in lower
                    and "/checkpoint" not in lower
                    and "/ssr-login" not in lower
                    and "remember-me-auto-login" not in lower
                ):
                    valid_pages.append(candidate)
            except Exception:
                continue

        if not valid_pages:
            print("SEARCH PAGE RESTORE FAILED: no authenticated company people-search tab exists.")
            return False

        # Prefer the currently-owned CompanyPage tab when it is still valid.
        selected = None
        try:
            owned = self.company_page.page
            if owned in valid_pages:
                selected = owned
        except Exception:
            pass

        # Otherwise choose the newest live people-search tab.
        if selected is None:
            selected = valid_pages[-1]

        try:
            self.page = selected
            self.company_page.page = selected
        except Exception as ex:
            print("SEARCH PAGE RESTORE FAILED: could not assign page ownership:", repr(ex))
            return False

        print("=" * 60)
        print("EMPLOYEE SEARCH PAGE RESTORED")
        print("=" * 60)
        print("Workflow page URL:", self.page.url)
        print("CompanyPage page URL:", self.company_page.page.url)
        print("Company-scoped people search:", True)

        return True

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
        max_profiles=None
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

        try:
            max_profiles = int(max_profiles)
        except (TypeError, ValueError):
            raise ValueError(
                "max_profiles must be a positive integer."
            )

        if max_profiles < 1:
            raise ValueError(
                "max_profiles must be at least 1."
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

        # Keep SearchWorkflowV2 and CompanyPage pointed at the exact same
        # authenticated employee-search page.
        if opened:
            try:
                self.page = self.company_page.page
                print(
                    "Employee-search page ownership synchronized:",
                    self.page.url
                )
            except Exception as ex:
                print(
                    "Employee-search page ownership synchronization failed:",
                    repr(ex)
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

            # First recover from an already-open authenticated company
            # people-search tab. This is non-navigational and cannot turn a
            # valid session into /login/ or /uas/login/.
            try:
                if self._restore_employee_search_page():
                    opened = True
                    print(
                        "Existing authenticated employee-search tab "
                        "recovered without navigation."
                    )
            except Exception as ex:
                print(
                    "Existing employee-search tab recovery failed:",
                    repr(ex)
                )

            current_url = self.page.url.lower()

            if not opened and (
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

                # Candidate is marked seen only after it is
                # successfully retained in results.

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

                profile = None

                try:

                    # Re-anchor to the authenticated employee search page before
                    # opening EVERY candidate. The search page is never the profile page.
                    if not self._restore_employee_search_page():
                        print(
                            "PROFILE OPEN FAILED: employee-search page is not available."
                        )
                        print("Candidate NOT counted as collected.")
                        print("Continuing to next candidate...")
                        continue

                    current_employee_url = str(
                        self.company_page.page.url or ""
                    ).lower()

                    if (
                        "/search/results/people/" not in current_employee_url
                        or "currentcompany=" not in current_employee_url
                    ):
                        print(
                            "PROFILE OPEN FAILED: current page is not company-scoped employee search."
                        )
                        print("Current URL:", self.company_page.page.url)
                        print("Candidate NOT counted as collected.")
                        print("Continuing to next candidate...")
                        continue

                    self.page = self.company_page.page

                    # self.page remains the authenticated employee-search page.
                    # LinkedInProfilePageV2.open_profile() searches that page for
                    # the EXACT candidate URL and Ctrl-clicks that exact link
                    # into a temporary profile tab.
                    profile = SearchWorkflowProfilePage(
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

                        print("PROFILE PAGE COULD NOT BE OPENED.")
                        print("Candidate NOT counted as collected.")
                        print("Continuing to next candidate...")
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

                    if not data.get("full_name"):

                        print("PROFILE OPENED BUT PROFILE DATA WAS EMPTY.")
                        print("Candidate NOT counted as collected.")
                        print("Continuing to next candidate...")
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

                    search_result_text = row.get(
                        "search_result_text",
                        ""
                    )

                    search_result_company_matches = (
                        search_result_supports_company(
                            search_result_text,
                            company
                        )
                    )

                    company_matches = (
                        (
                            bool(actual_company_normalized)
                            and
                            actual_company_normalized == requested_company_normalized
                        )
                        or
                        search_result_company_matches
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
                        "PROFILE COMPANY EXACT MATCH:",
                        (
                            bool(actual_company_normalized)
                            and
                            actual_company_normalized == requested_company_normalized
                        )
                    )

                    print(
                        "SEARCH RESULT COMPANY ASSOCIATION MATCH:",
                        search_result_company_matches
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

                    # Mark only after all profile validation succeeded
                    # and the candidate was actually retained.
                    seen_urls.add(
                        candidate_url
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

                    print("Profile processing failed:", repr(ex))
                    print("Candidate NOT counted as collected.")
                    print("Continuing to next candidate...")
                    continue

                finally:
                    # ALWAYS close the temporary profile tab used by this candidate.
                    # LinkedInProfilePageV2 normally closes it during get_profile(),
                    # but this finally block guarantees cleanup on every success,
                    # rejection, exception, or early-return path.
                    try:
                        temporary_profile_page = None

                        if profile is not None:
                            temporary_profile_page = getattr(
                                profile,
                                "_temporary_profile_page",
                                None
                            )

                        if (
                            temporary_profile_page is not None
                            and not temporary_profile_page.is_closed()
                        ):
                            temporary_profile_page.close()
                            print("PROFILE TAB CLOSED.")

                    except Exception as cleanup_ex:
                        print(
                            "PROFILE TAB CLEANUP WARNING:",
                            repr(cleanup_ex)
                        )

                    # Re-anchor the workflow and CompanyPage to the SAME
                    # authenticated employee-search page before the next candidate
                    # and before pagination.
                    if not self._restore_employee_search_page():
                        print(
                            "SEARCH PAGE RESTORE WARNING: "
                            "employee-search page could not be re-anchored."
                        )

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

            if not self._restore_employee_search_page():
                print("SAFE STOP: authenticated company employee-search page was lost.")
                break

            # Never paginate from a feed/root/profile/login page.
            current_employee_url = str(self.company_page.page.url or "").lower()
            if (
                "/search/results/people/" not in current_employee_url
                or "currentcompany=" not in current_employee_url
            ):
                print("SAFE STOP: page ownership invariant failed before pagination.")
                print("Current URL:", self.company_page.page.url)
                break

            has_next = self.company_page.next_page()

            print("Next page:", has_next)

            if not has_next:
                print("No more employee pages.")
                break

            # Hard postcondition: CompanyPage.next_page() must leave the
            # workflow on the same authenticated company-scoped people-search
            # page it claimed to open. This protects against LinkedIn's
            # transient root-page redirect.
            validated_next_url = str(
                self.company_page.page.url or ""
            ).lower()

            if (
                "/search/results/people/" not in validated_next_url
                or "currentcompany=" not in validated_next_url
            ):
                print(
                    "SAFE STOP: next_page() returned True but the live "
                    "CompanyPage is no longer on company people-search."
                )
                print(
                    "Invalid next-page URL:",
                    self.company_page.page.url
                )
                break

            self.page = self.company_page.page
            print(
                "Pagination page ownership synchronized:",
                self.page.url
            )

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
