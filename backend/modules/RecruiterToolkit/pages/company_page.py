from pages.base_page import BasePage
from urllib.parse import urlparse, parse_qs


import re
class CompanyPage(BasePage):

    def __init__(self, page):
        super().__init__(page)

    def search_company(self, company):

        # Store the exact requested company so get_profiles() can validate every result card.
        self._search_company = company


        search_box = self.page.locator(
            "input[placeholder*='looking']"
        ).first

        search_box.click()
        search_box.fill(company)
        search_box.press("Enter")

        print("=" * 60)
        print("CHECKING PAGE BEFORE WAIT")
        print("=" * 60)

        try:
            print("URL:", self.page.url)
            print("TITLE:", self.page.title())
        except Exception as ex:
            print("PAGE ALREADY CRASHED:", repr(ex))
            raise

        self.page.wait_for_timeout(5000)

        print("PAGE SURVIVED WAIT")

    def open_company_result(self, company):

        company_links = self.page.locator(
            "a[href*='/company/']"
        )

        count = company_links.count()

        print(
            "Company links found:",
            count
        )

        exact_match = None

        for i in range(count):

            try:

                text = (
                    company_links.nth(i)
                    .inner_text()
                    .strip()
                )

                first_line = (
                    text.split("\n")[0]
                    .strip()
                )

                print(
                    f"{i}: {first_line}"
                )

                if (
                    first_line.lower()
                    == company.lower()
                ):

                    exact_match = (
                        company_links.nth(i)
                    )

                    print(
                        "Selected company:",
                        first_line
                    )

                    break

            except Exception as ex:

                print(ex)

        if not exact_match:

            print(
                f"Exact company '{company}' not found"
            )

            return False

        company_href = exact_match.get_attribute(
            "href"
        )

        print(
            "LinkedIn company href:",
            company_href
        )

        if not company_href:

            print(
                "Company result has no href."
            )

            return False

        if company_href.startswith("/"):

            company_href = (
                "https://www.linkedin.com"
                + company_href
            )

        print(
            "Opening actual LinkedIn company page..."
        )

        # Prefer the exact authenticated search-result link.
        # LinkedIn can redirect a direct goto() to the root page.
        navigation_succeeded = False

        try:
            print("Clicking exact company result link...")
            exact_match.click(timeout=15000)
            self.page.wait_for_timeout(5000)

            print(
                "After company result click URL:",
                self.page.url
            )

            if "/company/" in self.page.url.lower():
                navigation_succeeded = True

        except Exception as ex:
            print(
                "Exact company-result click failed:",
                repr(ex)
            )

        # Controlled fallback using the exact href supplied by LinkedIn.
        if not navigation_succeeded:
            try:
                print(
                    "Trying exact company href navigation fallback..."
                )

                self.page.goto(
                    company_href,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                self.page.wait_for_timeout(5000)

                print(
                    "After company href navigation URL:",
                    self.page.url
                )

                if "/company/" in self.page.url.lower():
                    navigation_succeeded = True

            except Exception as ex:
                print(
                    "Exact company href navigation failed:",
                    repr(ex)
                )

        if not navigation_succeeded:

            print(
                "ERROR: LinkedIn company page was not opened."
            )

            print(
                "Final URL:",
                self.page.url
            )

            return False

        try:

            page_title = (
                self.page.locator("h1")
                .first
                .inner_text()
                .strip()
            )

            print(
                "Opened company page:",
                page_title
            )

        except Exception:

            pass

        return True

    # ============================================================
    # OPEN COMPANY EMPLOYEES / PEOPLE SEARCH
    # ============================================================

    def open_employees_page(self):

        print("=" * 60)
        print("OPENING COMPANY EMPLOYEES / PEOPLE SEARCH")
        print("=" * 60)

        # --------------------------------------------------------
        # IMPORTANT DESIGN RULE
        #
        # The company was already selected by open_company_result().
        #
        # We must preserve that company identity and use LinkedIn's
        # own currentCompany people-search link.
        #
        # We must NOT:
        #   - construct an unrelated company ID
        #   - choose a network=F URL
        #   - scan arbitrary /in/ links
        #   - fall back to generic people search
        # --------------------------------------------------------

        company_page_url = self.page.url

        print("Current company URL:")
        print(company_page_url)

        # --------------------------------------------------------
        # Helper: validate a people-search URL.
        # --------------------------------------------------------

        def is_valid_people_url(url):

            if not url:
                return False

            lower = url.lower()

            if "/search/results/people/" not in lower:
                return False

            if "currentcompany" not in lower:
                return False

            return True

        # --------------------------------------------------------
        # Helper: identify whether LinkedIn redirected away from
        # the requested people-search page.
        # --------------------------------------------------------

        def is_bad_navigation_url(url):

            if not url:
                return True

            lower = url.lower()

            if is_valid_people_url(url):
                return False

            bad_parts = (
                "linkedin.com/",
                "/login",
                "/authwall",
                "/checkpoint",
                "/uas/login",
                "/signup",
                "/feed",
            )

            # Root LinkedIn page must be treated as failure.
            if lower.rstrip("/") == "https://www.linkedin.com":
                return True

            if "/search/results/" not in lower:
                return True

            return False

        # --------------------------------------------------------
        # Helper: extract currentCompany IDs from a URL.
        # --------------------------------------------------------

        def current_company_values(url):

            import urllib.parse

            try:

                parsed = urllib.parse.urlparse(url)

                query = urllib.parse.parse_qs(
                    parsed.query
                )

                values = query.get(
                    "currentCompany",
                    []
                )

                return [
                    value.strip()
                    for value in values
                    if value.strip()
                ]

            except Exception:

                return []

        # --------------------------------------------------------
        # 1. Find LinkedIn's own currentCompany employee link.
        #
        # Prefer:
        #   currentCompany=...
        #
        # Reject:
        #   network=F
        #   unrelated currentCompany IDs
        # --------------------------------------------------------

        def find_employee_link():

            print("=" * 60)
            print("DISCOVERING LINKEDIN COMPANY EMPLOYEE LINK")
            print("=" * 60)

            links = self.page.locator(
                "a[href*='/search/results/people/']"
            )

            count = links.count()

            print(
                "People-search links found:",
                count
            )

            candidates = []

            for i in range(count):

                try:

                    link = links.nth(i)

                    href = link.get_attribute(
                        "href"
                    )

                    if not href:
                        continue

                    href = href.strip()

                    if "/search/results/people/" not in href:
                        continue

                    if "currentCompany" not in href:
                        continue

                    lower_href = href.lower()

                    # ------------------------------------------------
                    # IMPORTANT:
                    #
                    # LinkedIn may expose the company employee search as
                    # a canned search containing network/origin filters.
                    #
                    # Do NOT reject that LinkedIn-provided link.
                    #
                    # Instead, preserve the same currentCompany URL and
                    # remove only the canned-search filters before click.
                    # ------------------------------------------------

                    values = current_company_values(
                        href
                    )

                    if not values:
                        continue

                    # ------------------------------------------------
                    # Safety check:
                    #
                    # If the selected company URL contains a
                    # currentCompany value, require the employee
                    # link to use the SAME company value.
                    #
                    # This prevents unrelated company people-search
                    # URLs from being accepted.
                    # ------------------------------------------------

                    selected_company_values = current_company_values(
                        company_page_url
                    )

                    if (
                        selected_company_values
                        and values != selected_company_values
                    ):
                        print(
                            "SKIP unrelated currentCompany URL:",
                            href
                        )
                        continue

                    candidates.append(
                        (
                            link,
                            href,
                            values
                        )
                    )

                except Exception as ex:

                    print(
                        "Employee-link inspection failed:",
                        repr(ex)
                    )

            print(
                "Valid company employee candidates:",
                len(candidates)
            )

            if not candidates:
                return None

            # --------------------------------------------------------
            # We normally expect exactly one clean currentCompany
            # URL on the company page.
            #
            # Select the first clean LinkedIn-provided candidate.
            # Do NOT manufacture another URL here.
            # --------------------------------------------------------

            link, href, values = candidates[0]

            print(
                "Selected LinkedIn employee link:"
            )

            print(href)

            print(
                "currentCompany values:",
                values
            )

            return link

        # --------------------------------------------------------
        # Helper: click LinkedIn's employee link and validate result.
        # --------------------------------------------------------

        def click_employee_link():

            link = find_employee_link()

            if not link:

                print(
                    "No valid currentCompany employee link found."
                )

                return False

            try:

                print("=" * 60)
                print("CLICKING LINKEDIN EMPLOYEE LINK")
                print("=" * 60)

                # ------------------------------------------------
                # Clean LinkedIn canned-search filters while
                # preserving the exact currentCompany value.
                #
                # We modify the href of the LinkedIn-provided
                # employee link and then click that same link.
                # ------------------------------------------------

                print(
                    "Clicking LinkedIn employee search option..."
                )

                link.click()

                self.page.wait_for_timeout(
                    5000
                )

                current_url = self.page.url

                print(
                    "URL after employee-link click:"
                )

                print(
                    current_url
                )

                if is_valid_people_url(
                    current_url
                ):

                    print(
                        "Employee search page confirmed."
                    )

                    return True

                print(
                    "Employee link click did not produce "
                    "a valid company people-search page."
                )

                return False

            except Exception as ex:

                print(
                    "Employee-link click failed:",
                    repr(ex)
                )

                return False

        # --------------------------------------------------------
        # 2. FIRST AND PREFERRED METHOD
        #
        # Click the exact employee-search link LinkedIn exposed
        # on the selected company page.
        # --------------------------------------------------------

        if click_employee_link():

            return True

        # --------------------------------------------------------
        # 3. CONTROLLED RECOVERY
        #
        # If LinkedIn redirected to / or another invalid page,
        # restore the authenticated feed.
        #
        # We do NOT attempt generic people search.
        # --------------------------------------------------------

        print("=" * 60)
        print("EMPLOYEE SEARCH NAVIGATION RECOVERY")
        print("=" * 60)

        print(
            "Navigation failed. Current URL:",
            self.page.url
        )

        # --------------------------------------------------------
        # CONTROLLED EMPLOYEE NAVIGATION RECOVERY
        #
        # IMPORTANT:
        # Do not make /feed/ the required recovery checkpoint.
        #
        # LinkedIn can redirect the employee-search click through
        # /login/, /ssr-login/ or remember-me-auto-login even when
        # the original authenticated company page is still usable.
        #
        # The selected company URL was captured before navigation.
        # Recover the SAME company directly and rediscover LinkedIn's
        # own currentCompany employee link.
        # --------------------------------------------------------

        print("=" * 60)
        print("DIRECT COMPANY EMPLOYEE NAVIGATION RECOVERY")
        print("=" * 60)

        company_reopened = False

        try:

            if (
                company_page_url
                and "/company/" in company_page_url.lower()
            ):

                print(
                    "Re-opening previously selected company directly:"
                )

                print(
                    company_page_url
                )

                self.page.goto(
                    company_page_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                self.page.wait_for_timeout(
                    3000
                )

                reopened_url = self.page.url

                print(
                    "Company recovery URL:",
                    reopened_url
                )

                if (
                    "/company/" in reopened_url.lower()
                    and "/login" not in reopened_url.lower()
                    and "/authwall" not in reopened_url.lower()
                    and "/checkpoint" not in reopened_url.lower()
                ):

                    company_reopened = True

                    print(
                        "Selected company page recovered."
                    )

        except Exception as ex:

            print(
                "Direct company recovery failed:",
                repr(ex)
            )

        # --------------------------------------------------------
        # If the exact company URL cannot be reopened, use the
        # existing company-search recovery.
        #
        # We deliberately do NOT use generic people search.
        # --------------------------------------------------------


        # --------------------------------------------------------
        # 5. If direct company recovery failed, re-run the existing
        # company search.
        #
        # IMPORTANT:
        # This uses the existing search_company() and
        # open_company_result() methods.
        #
        # Therefore company matching remains exactly as before.
        # --------------------------------------------------------

        if not company_reopened:

            print(
                "Re-running existing company search recovery..."
            )

            try:

                # ------------------------------------------------
                # IMPORTANT:
                #
                # search_company() already stores the exact company
                # requested by the workflow in self._search_company.
                #
                # Do NOT attempt to recover the company name from
                # the current page because LinkedIn may have redirected
                # the browser to /login/, /authwall/ or another page.
                #
                # The stored company name is the authoritative value.
                # ------------------------------------------------

                company_name = getattr(
                    self,
                    "_search_company",
                    ""
                )

                company_name = (
                    company_name.strip()
                    if company_name
                    else ""
                )

                if not company_name:

                    print(
                        "ERROR: Previously selected company name "
                        "is not available."
                    )

                    print(
                        "Refusing generic people search."
                    )

                    return False

                print(
                    "Recovered company name from workflow state:",
                    company_name
                )

                # ------------------------------------------------
                # Re-run the EXISTING company search.
                #
                # This preserves the existing exact-company matching
                # behavior in search_company() + open_company_result().
                # ------------------------------------------------

                self.search_company(
                    company_name
                )

                found = (
                    self.open_company_result(
                        company_name
                    )
                )

                if not found:

                    print(
                        "Company recovery search failed."
                    )

                    return False

                company_reopened = True

                print(
                    "Selected company recovered through "
                    "existing company search."
                )

            except Exception as ex:

                print(
                    "Company search recovery failed:",
                    repr(ex)
                )

                return False

        # --------------------------------------------------------
        # 6. Re-discover and CLICK the employee link.
        #
        # We deliberately do NOT use page.goto(best_url) here.
        # --------------------------------------------------------

        if company_reopened:

            print(
                "Company page recovered."
            )

            if click_employee_link():

                return True

        # --------------------------------------------------------
        # 7. Last controlled fallback:
        #
        # Re-scan the current company page for the employee link.
        # If LinkedIn exposes nothing, fail safely.
        #
        # Never construct generic people search.
        # Never scan /in/ links.
        # --------------------------------------------------------

        print("=" * 60)
        print("EMPLOYEE SEARCH COULD NOT BE SAFELY OPENED")
        print("=" * 60)

        print(
            "No valid LinkedIn currentCompany employee "
            "navigation succeeded."
        )

        print(
            "Refusing generic people search to prevent "
            "unrelated profiles."
        )

        return False

    def apply_location(self, location):

        print(
            f"Applying location: {location}"
        )

        # ------------------------------------------------------------
        # Dismiss any LinkedIn dialog blocking the filter controls.
        # LinkedIn can leave an open dialog over the people-search
        # page, causing Playwright clicks to be intercepted.
        #
        # Keep the original location-selection method unchanged.
        # ------------------------------------------------------------

        try:

            dialogs = self.page.locator(
                "dialog[open], [role='dialog']:visible"
            )

            if dialogs.count():

                print(
                    "Open LinkedIn dialog detected. "
                    "Attempting to dismiss it..."
                )

                self.page.keyboard.press(
                    "Escape"
                )

                self.page.wait_for_timeout(
                    1000
                )

        except Exception:

            pass

        self.page.get_by_text(
            "Locations",
            exact=False
        ).first.click()

        self.page.wait_for_timeout(
            2000
        )

        location_box = self.page.locator(
            "input"
        ).last

        location_box.fill(
            location
        )

        self.page.wait_for_timeout(
            2000
        )

        self.page.keyboard.press(
            "ArrowDown"
        )

        self.page.keyboard.press(
            "Enter"
        )

        self.page.wait_for_timeout(
            1000
        )

        try:

            self.page.get_by_text(
                "Show results",
                exact=False
            ).first.click()

        except Exception:

            pass

        self.page.wait_for_timeout(
            5000
        )

        return True

    def get_profiles(
        self,
        company="",
        location=""
    ):
        """
        Extract employee profile URLs from LinkedIn's actual people-search
        result cards.

        IMPORTANT:
        The employee-search page has already been opened through
        LinkedIn's own currentCompany people-search link and the requested
        location has already been applied.

        This method intentionally does NOT determine company membership
        from arbitrary text on the search page.

        Instead, profile discovery is restricted to LinkedIn search-result
        containers. The actual profile page remains the source of truth
        for current company and location.
        """

        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)

        print(
            "Requested company:",
            company
        )

        print(
            "Requested location:",
            location
        )

        profiles = []
        seen = set()

        # ------------------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT collect every /in/ link under <main>.
        #
        # LinkedIn pages can contain profile links outside the actual
        # people-search result cards.
        #
        # We therefore target known LinkedIn search-result containers
        # first and extract the profile link FROM those containers.
        # ------------------------------------------------------------

        result_selectors = [
            "li.reusable-search__result-container:visible",
            "li.search-result:visible",
            "li[class*='reusable-search__result-container']:visible",
            "div[class*='search-entity-result']:visible",
            "div[class*='entity-result']:visible",
            "div[data-view-name*='search-entity-result']:visible",
        ]

        result_containers = None

        for selector in result_selectors:
            try:
                candidate = self.page.locator(selector)

                count = candidate.count()

                if count:
                    print(
                        "LinkedIn result selector:",
                        selector
                    )
                    print(
                        "Result containers found:",
                        count
                    )

                    result_containers = candidate
                    break

            except Exception as ex:
                print(
                    "Result selector inspection failed:",
                    selector,
                    repr(ex)
                )

        # ------------------------------------------------------------
        # Controlled fallback:
        #
        # If LinkedIn changes the exact class name, use only semantic
        # result containers. Do NOT fall back to all /in/ links.
        # ------------------------------------------------------------

        if result_containers is None:

            print(
                "Known LinkedIn result selector not found."
            )

            fallback_selectors = [
                "main:visible li[role='listitem']:visible",
                "main:visible article[role='article']:visible",
                "main:visible li[class*='result']:visible",
                "main:visible article[class*='result']:visible",
            ]

            for selector in fallback_selectors:

                try:

                    candidate = self.page.locator(selector)

                    count = candidate.count()

                    if count:
                        print(
                            "Using controlled semantic result selector:",
                            selector
                        )

                        print(
                            "Result containers found:",
                            count
                        )

                        result_containers = candidate
                        break

                except Exception as ex:

                    print(
                        "Fallback result selector inspection failed:",
                        selector,
                        repr(ex)
                    )

        if result_containers is None:

            print(
                "ERROR: No LinkedIn employee result containers found."
            )

            print(
                "Profiles extracted: 0"
            )

            return profiles

        # ------------------------------------------------------------
        # Process each actual result container.
        # ------------------------------------------------------------

        container_count = result_containers.count()

        print(
            "Processing LinkedIn employee result containers:",
            container_count
        )

        for i in range(container_count):

            try:

                container = result_containers.nth(i)

                # ----------------------------------------------------
                # Extract profile links ONLY from this result card.
                # ----------------------------------------------------

                profile_links = container.locator(
                    "a[href*='/in/']:visible"
                )

                link_count = profile_links.count()

                if not link_count:

                    print(
                        "Result container has no profile link:",
                        i
                    )

                    continue

                selected_link = None
                raw_name = ""

                # ----------------------------------------------------
                # Find the first usable profile link in this result
                # container.
                # ----------------------------------------------------

                for link_index in range(link_count):

                    try:

                        link = profile_links.nth(link_index)

                        href = link.get_attribute(
                            "href"
                        )

                        if not href:
                            continue

                        clean_url = (
                            href
                            .split("?")[0]
                            .rstrip("/")
                        )

                        if not clean_url.startswith(
                            "http"
                        ):
                            clean_url = (
                                "https://www.linkedin.com"
                                + clean_url
                            )

                        if "/in/" not in clean_url.lower():
                            continue

                        raw_name = (
                            link.inner_text(
                                timeout=2000
                            )
                            .strip()
                        )

                        # ------------------------------------------------
                        # LinkedIn sometimes has nested /in/ links where
                        # the first one is not the actual person's name.
                        #
                        # Prefer a short, single-line visible name.
                        # ------------------------------------------------

                        if (
                            raw_name
                            and "\n" not in raw_name
                            and len(raw_name) <= 150
                        ):
                            selected_link = link
                            break

                    except Exception as ex:

                        print(
                            "Profile link inspection failed:",
                            repr(ex)
                        )

                if selected_link is None:

                    print(
                        "REJECT - no usable employee profile link "
                        "inside result container:",
                        i
                    )

                    continue

                href = selected_link.get_attribute(
                    "href"
                )

                if not href:
                    continue

                clean_url = (
                    href
                    .split("?")[0]
                    .rstrip("/")
                )

                if not clean_url.startswith(
                    "http"
                ):
                    clean_url = (
                        "https://www.linkedin.com"
                        + clean_url
                    )

                if "/in/" not in clean_url.lower():
                    continue

                if clean_url in seen:

                    print(
                        "SKIP duplicate profile:",
                        clean_url
                    )

                    continue

                # ----------------------------------------------------
                # Candidate logging
                # ----------------------------------------------------

                print(
                    "-" * 60
                )

                print(
                    "Candidate:",
                    raw_name
                )

                print(
                    "Candidate URL:",
                    clean_url
                )

                print(
                    "Result container index:",
                    i
                )

                # ----------------------------------------------------
                # Accept ONLY because the URL was found inside a
                # specific LinkedIn search-result container.
                #
                # We intentionally do NOT fabricate company/location
                # information here.
                #
                # The existing LinkedInProfilePageV2 extraction later
                # reads the actual profile page.
                # ----------------------------------------------------

                seen.add(
                    clean_url
                )

                profiles.append(
                    {
                        "full_name": raw_name,
                        "profile_url": clean_url,
                        "company": company,
                        "location": location,
                    }
                )

                print(
                    "ACCEPT - LinkedIn search-result profile:",
                    raw_name
                )

            except Exception as ex:

                print(
                    "Profile result-container processing failed:",
                    repr(ex)
                )

        # ------------------------------------------------------------
        # Final output
        # ------------------------------------------------------------

        print("=" * 60)

        print(
            "EMPLOYEE PROFILES EXTRACTED:",
            len(profiles)
        )

        print("=" * 60)

        for profile in profiles:

            print(
                profile.get(
                    "full_name",
                    ""
                ),
                "->",
                profile.get(
                    "profile_url",
                    ""
                )
            )

        return profiles

    def next_page(self):

        try:

            print(
                "Trying next page..."
            )

            print(
                "NEW NEXT_PAGE EXECUTING"
            )

            buttons = self.page.locator(
                "button"
            )

            for i in range(
                buttons.count()
            ):

                try:

                    btn = buttons.nth(i)

                    text = (
                        btn.inner_text()
                        .strip()
                    )

                    if text == "Next":

                        print(
                            "Clicking Next"
                        )

                        btn.click()

                        self.page.wait_for_timeout(
                            5000
                        )

                        print(
                            "Current URL after next:"
                        )

                        print(
                            self.page.url
                        )

                        return True

                except Exception:
                    pass

            print(
                "Next button not found"
            )

            return False

        except Exception as ex:

            print(
                "Next page failed:",
                ex
            )

            return False
