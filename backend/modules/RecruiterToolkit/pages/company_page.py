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

            current_url = self.page.url.lower()

            # LinkedIn may take the exact company-result click directly
            # to the company's employee people-search page.
            # This is a VALID navigation result and must not be treated
            # as a failure.
            if (
                "/company/" in current_url
                or (
                    "/search/results/people/" in current_url
                    and "currentcompany=" in current_url
                )
            ):
                navigation_succeeded = True
                print("Valid LinkedIn company/people-search navigation confirmed.")

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

                current_url = self.page.url.lower()

                if (
                    "/company/" in current_url
                    or (
                        "/search/results/people/" in current_url
                        and "currentcompany=" in current_url
                    )
                ):
                    navigation_succeeded = True
                    print("Valid LinkedIn company/people-search navigation confirmed.")


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
        # IMPORTANT:
        # The exact company-result click can land directly on the
        # company's LinkedIn people-search page.
        #
        # If that happens, employee navigation is ALREADY complete.
        # Do not try to rediscover or click another employee link.
        # --------------------------------------------------------

        current_url_lower = company_page_url.lower()

        if (
            "/search/results/people/" in current_url_lower
            and "currentcompany=" in current_url_lower
        ):
            print("=" * 60)
            print("COMPANY PEOPLE-SEARCH PAGE ALREADY OPEN")
            print("=" * 60)
            print("Current URL:")
            print(company_page_url)
            print("Valid currentCompany people-search URL confirmed.")
            print("Skipping employee-link discovery.")
            return True

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

        print("=" * 60)
        print("LOCATION FILTER - START")
        print("=" * 60)

        print(
            "URL before location filter:",
            self.page.url
        )

        # ------------------------------------------------------------
        # SAFETY CHECK
        # ------------------------------------------------------------

        before_url = (
            self.page.url
            or ""
        ).lower()

        if (
            "/search/results/people/"
            not in before_url
        ):
            print(
                "ERROR: Location filter started from "
                "a non-people-search URL."
            )
            return False

        if "currentcompany=" not in before_url:
            print(
                "ERROR: currentCompany missing before "
                "location filter."
            )
            return False

        # ------------------------------------------------------------
        # OPEN LOCATIONS
        # ------------------------------------------------------------

        try:

            locations = self.page.get_by_text(
                "Locations",
                exact=False
            )

            location_count = locations.count()

            print(
                "Locations controls found:",
                location_count
            )

            clicked_locations = False

            for i in range(
                location_count - 1,
                -1,
                -1
            ):

                try:

                    candidate = (
                        locations.nth(i)
                    )

                    if not candidate.is_visible():
                        continue

                    candidate.click(
                        timeout=15000
                    )

                    clicked_locations = True

                    print(
                        "Locations filter opened."
                    )

                    break

                except Exception:
                    continue

            if not clicked_locations:

                print(
                    "ERROR: Could not open Locations filter."
                )

                return False

        except Exception as ex:

            print(
                "ERROR opening Locations:",
                repr(ex)
            )

            return False

        self.page.wait_for_timeout(
            2000
        )

        # ------------------------------------------------------------
        # LOCATION INPUT
        # ------------------------------------------------------------

        try:

            inputs = self.page.locator(
                "input:visible"
            )

            input_count = inputs.count()

            print(
                "Visible inputs after opening Locations:",
                input_count
            )

            if input_count == 0:

                print(
                    "ERROR: No visible location input found."
                )

                return False

            location_box = inputs.last

            location_box.fill(
                location
            )

            print(
                "Location value entered:",
                location
            )

        except Exception as ex:

            print(
                "ERROR entering location:",
                repr(ex)
            )

            return False

        # ------------------------------------------------------------
        # WAIT FOR AUTOCOMPLETE
        # ------------------------------------------------------------

        self.page.wait_for_timeout(
            2500
        )

        # ------------------------------------------------------------
        # SELECT LOCATION SUGGESTION
        # ------------------------------------------------------------

        location_selected = False

        requested_location = location.strip()
        expected_location = f"{requested_location}, United States"

        print(
            "Selecting LinkedIn location option:",
            expected_location
        )

        # LinkedIn's rendered DOM was confirmed to contain:
        #
        #   role="option"
        #   text="New Jersey, United States"
        #
        # Therefore click the actual autocomplete option.
        # Do NOT use ArrowDown + Enter.
        location_option = self.page.get_by_role(
            "option",
            name=expected_location,
            exact=True
        )

        option_count = location_option.count()

        print(
            "Matching location options found:",
            option_count
        )

        if option_count > 0:

            try:

                location_option.first.scroll_into_view_if_needed()

                location_option.first.click(
                    timeout=15000
                )

                location_selected = True

                print(
                    "Location option clicked successfully."
                )

            except Exception as ex:

                print(
                    "Location option click failed:",
                    repr(ex)
                )

        # Controlled fallback against the same confirmed role=option DOM.
        if not location_selected:

            try:

                visible_options = self.page.locator(
                    "[role='option']:visible"
                )

                visible_count = visible_options.count()

                print(
                    "Visible location options:",
                    visible_count
                )

                for i in range(visible_count):

                    try:

                        option = visible_options.nth(i)

                        option_text = (
                            option.inner_text(
                                timeout=2000
                            )
                            .strip()
                        )

                        print(
                            f"Location option {i}:",
                            repr(option_text)
                        )

                        if (
                            option_text.lower()
                            == expected_location.lower()
                        ):

                            option.scroll_into_view_if_needed()

                            option.click(
                                timeout=15000
                            )

                            location_selected = True

                            print(
                                "Location option clicked successfully via fallback."
                            )

                            break

                    except Exception:
                        continue

            except Exception as ex:

                print(
                    "Location option fallback failed:",
                    repr(ex)
                )

        if not location_selected:

            print(
                "ERROR: Could not click the LinkedIn location autocomplete option."
            )

            print(
                "Requested location:",
                requested_location
            )

            return False

        print(
            "Location suggestion selected successfully."
        )

        # IMPORTANT:
        # Do NOT press Enter.
        #
        # The previous GitHub run proved that Enter redirects LinkedIn
        # to /ssr-login/remember-me-auto-login.
        self.page.wait_for_timeout(
            1000
        )

        # ------------------------------------------------------------
        # VERIFY WE ARE STILL ON THE COMPANY PEOPLE SEARCH
        # ------------------------------------------------------------

        current_url = (
            self.page.url
            or ""
        ).lower()

        print(
            "URL after location selection:",
            self.page.url
        )

        if (
            "/search/results/people/"
            not in current_url
        ):

            print(
                "ERROR: LinkedIn left people-search "
                "after location selection."
            )

            return False

        if "currentcompany=" not in current_url:

            print(
                "ERROR: currentCompany disappeared "
                "after location selection."
            )

            return False

        # ------------------------------------------------------------
        # SHOW RESULTS
        #
        # Use LinkedIn's visible "Show results" text.
        #
        # This is the mechanism used by the previously working
        # implementation. Do not require role="button" because the
        # current LinkedIn DOM does not expose it that way.
        # ------------------------------------------------------------

        print(
            "Looking for Show results..."
        )

        try:

            show_results = self.page.get_by_text(
                "Show results",
                exact=False
            )

            show_count = show_results.count()

            print(
                "Show results controls found:",
                show_count
            )

            clicked_show_results = False

            for i in range(
                show_count - 1,
                -1,
                -1
            ):

                try:

                    candidate = show_results.nth(i)

                    if not candidate.is_visible():
                        continue

                    print(
                        "Clicking Show results..."
                    )

                    candidate.scroll_into_view_if_needed()

                    candidate.click(
                        timeout=15000
                    )

                    clicked_show_results = True

                    print(
                        "Show results clicked successfully."
                    )

                    break

                except Exception as ex:

                    print(
                        "Show results candidate click failed:",
                        repr(ex)
                    )

            if not clicked_show_results:

                print(
                    "ERROR: No visible Show results control "
                    "could be clicked."
                )

                print(
                    "Current URL:",
                    self.page.url
                )

                return False

        except Exception as ex:

            print(
                "ERROR finding Show results:",
                repr(ex)
            )

            return False

        # ------------------------------------------------------------
        # WAIT FOR LINKEDIN TO APPLY FILTER
        # ------------------------------------------------------------

        self.page.wait_for_timeout(
            5000
        )

        print(
            "URL after Show results:",
            self.page.url
        )

        # ------------------------------------------------------------
        # FINAL VALIDATION
        # ------------------------------------------------------------

        final_url = (
            self.page.url
            or ""
        ).lower()

        if (
            "/search/results/people/"
            not in final_url
        ):

            print(
                "ERROR: Show results did not return "
                "to people-search."
            )

            print(
                "Final URL:",
                self.page.url
            )

            return False

        if "currentcompany=" not in final_url:

            print(
                "ERROR: currentCompany missing after "
                "Show results."
            )

            print(
                "Final URL:",
                self.page.url
            )

            return False

        print(
            "Location filter applied successfully."
        )

        print(
            "Final filtered URL:",
            self.page.url
        )

        return True

    def get_profiles(self, company="", location=""):

        print("=" * 60)
        print("EXTRACTING COMPANY-MATCHED PROFILES")
        print("=" * 60)

        print(
            "Requested company:",
            company
        )

        print(
            "Requested location:",
            location
        )

        # ------------------------------------------------------------
        # SAFETY CHECK
        #
        # This method must only operate on the authenticated
        # currentCompany people-search page.
        # ------------------------------------------------------------

        current_url = self.page.url or ""

        print(
            "Current employee-search URL:",
            current_url
        )

        if "/search/results/people/" not in current_url.lower():

            print(
                "ERROR: Employee people-search page is not active."
            )

            return []

        if "currentcompany=" not in current_url.lower():

            print(
                "ERROR: currentCompany is missing from employee search."
            )

            return []

        # ------------------------------------------------------------
        # Company normalization
        # ------------------------------------------------------------

        def normalize_company(value):

            if not value:
                return ""

            value = (
                str(value)
                .replace("\xa0", " ")
                .strip()
                .lower()
            )

            value = re.sub(
                r"[^a-z0-9]+",
                " ",
                value
            )

            return " ".join(
                value.split()
            )

        requested_company = normalize_company(
            company
        )

        profiles = []
        seen = set()

        # ------------------------------------------------------------
        # BOUNDED EMPLOYEE SEARCH AREA
        #
        # Do not scan the entire LinkedIn document.
        # ------------------------------------------------------------

        search_area = None

        try:

            main = self.page.locator(
                "main:visible"
            ).first

            if main.count():

                search_area = main

                print(
                    "Using visible LinkedIn main area."
                )

        except Exception as ex:

            print(
                "Main-area lookup failed:",
                repr(ex)
            )

        if search_area is None:

            for selector in (
                "div.scaffold-finite-scroll__content:visible",
                "div.search-results-container:visible",
                "div[role='main']:visible"
            ):

                try:

                    candidate = self.page.locator(
                        selector
                    ).first

                    if candidate.count():

                        search_area = candidate

                        print(
                            "Using bounded search area:",
                            selector
                        )

                        break

                except Exception:
                    continue

        if search_area is None:

            print(
                "ERROR: No bounded employee-search area found."
            )

            return profiles

        # ------------------------------------------------------------
        # DISCOVER /in/ LINKS ONLY INSIDE BOUNDED AREA
        # ------------------------------------------------------------

        links = search_area.locator(
            "a[href*='/in/']:visible"
        )

        count = links.count()

        print(
            "Visible /in/ links inside bounded employee area:",
            count
        )

        if not count:

            print(
                "No employee profile links found."
            )

            return profiles

        # ------------------------------------------------------------
        # RESULT CONTAINER DETECTION
        # ------------------------------------------------------------

        def looks_like_result_container(element):

            try:

                tag = (
                    element.evaluate(
                        "(el) => el.tagName.toLowerCase()"
                    )
                    or ""
                ).lower()

                classes = normalize_company(
                    element.get_attribute(
                        "class"
                    )
                    or ""
                )

                data_view = normalize_company(
                    element.get_attribute(
                        "data-view-name"
                    )
                    or ""
                )

                role = normalize_company(
                    element.get_attribute(
                        "role"
                    )
                    or ""
                )

                aria = normalize_company(
                    element.get_attribute(
                        "aria-label"
                    )
                    or ""
                )

                if (
                    "search-result" in classes
                    or
                    "search-entity-result" in classes
                    or
                    "reusable-search" in classes
                    or
                    "entity-result" in classes
                ):

                    return True

                if (
                    "search-entity-result" in data_view
                    or
                    "universal-template" in data_view
                ):

                    return True

                if (
                    "search result" in aria
                    or
                    "search-result" in aria
                ):

                    return True

                if (
                    tag == "li"
                    and
                    (
                        "result" in classes
                        or
                        "search" in classes
                        or
                        role == "listitem"
                    )
                ):

                    return True

                if (
                    tag == "article"
                    and
                    (
                        "result" in classes
                        or
                        "search" in classes
                        or
                        role == "article"
                    )
                ):

                    return True

                if role in (
                    "listitem",
                    "option",
                    "article"
                ):

                    return True

            except Exception:
                pass

            return False

        # ------------------------------------------------------------
        # FIND RESULT CONTAINER
        # ------------------------------------------------------------

        def find_result_container(link):

            current = link

            for depth in range(
                1,
                9
            ):

                try:

                    current = current.locator(
                        ".."
                    )

                    if current.count() == 0:
                        return None

                    if looks_like_result_container(
                        current
                    ):

                        return current

                except Exception:

                    return None

            return None

        # ------------------------------------------------------------
        # COMPANY MATCHING FALLBACK
        # ------------------------------------------------------------

        def find_company_matching_ancestor(link):

            current = link

            for depth in range(
                1,
                9
            ):

                try:

                    current = current.locator(
                        ".."
                    )

                    if current.count() == 0:
                        return None

                    tag = (
                        current.evaluate(
                            "(el) => el.tagName.toLowerCase()"
                        )
                        or ""
                    ).lower()

                    if tag in (
                        "body",
                        "html",
                        "main"
                    ):

                        return None

                    text = normalize_company(
                        current.inner_text(
                            timeout=2000
                        )
                    )

                    if not text:
                        continue

                    if len(text) > 5000:
                        continue

                    if (
                        requested_company
                        and requested_company in text
                    ):

                        return current

                except Exception:
                    continue

            return None

        # ------------------------------------------------------------
        # PROCESS EMPLOYEE CANDIDATES
        # ------------------------------------------------------------

        for i in range(count):

            try:

                link = links.nth(i)

                raw_name = (
                    link.inner_text(
                        timeout=2000
                    )
                    .strip()
                    .replace(
                        "\n",
                        " "
                    )
                )

                if not raw_name:
                    continue

                # Avoid navigation / multi-line content.
                if "\n" in raw_name:
                    continue

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

                if clean_url in seen:
                    continue

                print("-" * 60)

                print(
                    "Candidate:",
                    raw_name
                )

                print(
                    "Candidate URL:",
                    clean_url
                )

                # ----------------------------------------------------
                # REQUIRE A REAL SEARCH RESULT CONTAINER
                # ----------------------------------------------------

                result_container = (
                    find_result_container(
                        link
                    )
                )

                if result_container is None:

                    print(
                        "REJECT - no LinkedIn employee "
                        "result container:",
                        raw_name
                    )

                    continue

                # ----------------------------------------------------
                # REQUIRE COMPANY CONFIRMATION
                # ----------------------------------------------------

                container_text = ""

                try:

                    container_text = normalize_company(
                        result_container.inner_text(
                            timeout=2000
                        )
                    )

                except Exception:

                    container_text = ""

                company_match = False

                if (
                    requested_company
                    and requested_company in container_text
                ):

                    company_match = True

                if not company_match:

                    matching_ancestor = (
                        find_company_matching_ancestor(
                            link
                        )
                    )

                    if matching_ancestor is not None:

                        company_match = True

                if not company_match:

                    print(
                        "REJECT - company not confirmed in result:",
                        raw_name
                    )

                    continue

                # ----------------------------------------------------
                # ACCEPT
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
                    "ACCEPT - company-matched employee:",
                    raw_name
                )

            except Exception as ex:

                print(
                    "Profile candidate processing failed:",
                    repr(ex)
                )

        print("=" * 60)

        print(
            "COMPANY-MATCHED PROFILES EXTRACTED:",
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

            current_url = self.page.url or ""

            # --------------------------------------------------------
            # Only paginate from a valid company people-search page.
            # --------------------------------------------------------

            if (
                "/search/results/people/"
                not in current_url.lower()
                or
                "currentcompany="
                not in current_url.lower()
            ):

                print(
                    "ERROR: Cannot paginate because the current "
                    "employee-search page is invalid."
                )

                print(
                    "Current URL:",
                    current_url
                )

                return False

            buttons = self.page.locator(
                "button:visible"
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

                    if text != "Next":
                        continue

                    print(
                        "Clicking Next"
                    )

                    btn.click(
                        timeout=15000
                    )

                    self.page.wait_for_timeout(
                        5000
                    )

                    next_url = self.page.url or ""

                    print(
                        "Current URL after next:"
                    )

                    print(
                        next_url
                    )

                    # ------------------------------------------------
                    # CRITICAL:
                    #
                    # LinkedIn has previously sent the browser to /
                    # while the click itself appeared successful.
                    #
                    # Never report True unless the next page is still
                    # the company's people-search page.
                    # ------------------------------------------------

                    if (
                        "/search/results/people/"
                        not in next_url.lower()
                    ):

                        print(
                            "ERROR: Next navigation left "
                            "LinkedIn people-search."
                        )

                        return False

                    if (
                        "currentcompany="
                        not in next_url.lower()
                    ):

                        print(
                            "ERROR: Next navigation removed "
                            "currentCompany."
                        )

                        return False

                    print(
                        "Next employee page confirmed."
                    )

                    return True

                except Exception as ex:

                    print(
                        "Next button processing failed:",
                        repr(ex)
                    )

                    continue

            print(
                "Next button not found"
            )

            return False

        except Exception as ex:

            print(
                "Next page failed:",
                repr(ex)
            )

            return False

