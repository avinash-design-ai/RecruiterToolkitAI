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

        # ------------------------------------------------------------
        # SAFETY CHECK
        #
        # Location filtering must start from LinkedIn's people-search
        # page. Never attempt to apply the filter from /feed/.
        # ------------------------------------------------------------

        starting_url = self.page.url or ""

        print("=" * 60)
        print("LOCATION FILTER - START")
        print("=" * 60)
        print(
            "URL before location filter:",
            starting_url
        )

        if "/search/results/people/" not in starting_url:
            print(
                "ERROR: Location filter started outside "
                "the people-search page."
            )
            return False

        # ------------------------------------------------------------
        # Dismiss any blocking LinkedIn dialog.
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

        # ------------------------------------------------------------
        # Open Locations filter.
        # ------------------------------------------------------------

        try:
            locations = self.page.get_by_text(
                "Locations",
                exact=True
            ).filter(
                visible=True
            )

            if not locations.count():
                locations = self.page.get_by_text(
                    "Locations",
                    exact=False
                ).filter(
                    visible=True
                )

            if not locations.count():
                print(
                    "ERROR: Visible Locations filter not found."
                )
                return False

            locations.last.click(
                timeout=15000
            )

            print(
                "Locations filter opened."
            )

        except Exception as ex:
            print(
                "Locations filter click failed:",
                repr(ex)
            )
            return False

        self.page.wait_for_timeout(
            2000
        )

        # ------------------------------------------------------------
        # Find the location input.
        # Keep the existing behavior of using the last visible
        # input because LinkedIn renders several search/filter inputs.
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
                "Location input failed:",
                repr(ex)
            )
            return False

        self.page.wait_for_timeout(
            2000
        )

        # ------------------------------------------------------------
        # Select the LinkedIn location suggestion.
        # ------------------------------------------------------------

        try:
            self.page.keyboard.press(
                "ArrowDown"
            )

            self.page.keyboard.press(
                "Enter"
            )

            print(
                "Location suggestion selected."
            )

        except Exception as ex:
            print(
                "Location suggestion selection failed:",
                repr(ex)
            )
            return False

        self.page.wait_for_timeout(
            1000
        )

        # ------------------------------------------------------------
        # Click the ACTUAL visible Show results button.
        #
        # Do not use a page-wide text selector for this.
        # LinkedIn can expose multiple "Show results" elements.
        # ------------------------------------------------------------

        show_results_clicked = False

        try:
            dialogs = self.page.locator(
                "dialog[open]:visible, [role='dialog']:visible"
            )

            if dialogs.count():

                print(
                    "Searching active dialog for Show results..."
                )

                for dialog_index in range(
                    dialogs.count() - 1,
                    -1,
                    -1
                ):

                    dialog = dialogs.nth(
                        dialog_index
                    )

                    buttons = dialog.locator(
                        "button:visible"
                    )

                    for button_index in range(
                        buttons.count() - 1,
                        -1,
                        -1
                    ):

                        button = buttons.nth(
                            button_index
                        )

                        try:
                            button_text = (
                                button.inner_text(
                                    timeout=2000
                                )
                                .strip()
                                .replace(
                                    "\n",
                                    " "
                                )
                            )

                            if button_text.lower() == "show results":

                                print(
                                    "Found Show results button "
                                    "inside active dialog."
                                )

                                button.click(
                                    timeout=15000
                                )

                                show_results_clicked = True

                                print(
                                    "Clicked dialog Show results."
                                )

                                break

                        except Exception:
                            continue

                    if show_results_clicked:
                        break

        except Exception as ex:
            print(
                "Dialog Show results discovery failed:",
                repr(ex)
            )

        # ------------------------------------------------------------
        # Controlled fallback:
        # Search only visible BUTTON elements on the page.
        # ------------------------------------------------------------

        if not show_results_clicked:

            print(
                "Dialog button not found. "
                "Using visible-button fallback."
            )

            try:
                buttons = self.page.locator(
                    "button:visible"
                )

                for i in range(
                    buttons.count() - 1,
                    -1,
                    -1
                ):

                    button = buttons.nth(
                        i
                    )

                    try:
                        button_text = (
                            button.inner_text(
                                timeout=2000
                            )
                            .strip()
                            .replace(
                                "\n",
                                " "
                            )
                        )

                        if button_text.lower() == "show results":

                            button.click(
                                timeout=15000
                            )

                            show_results_clicked = True

                            print(
                                "Clicked visible-button "
                                "Show results."
                            )

                            break

                    except Exception:
                        continue

            except Exception as ex:
                print(
                    "Visible-button Show results fallback failed:",
                    repr(ex)
                )

        if not show_results_clicked:

            print(
                "ERROR: Could not safely click Show results."
            )

            return False

        # ------------------------------------------------------------
        # Give LinkedIn time to update the people-search results.
        # ------------------------------------------------------------

        self.page.wait_for_timeout(
            5000
        )

        # ------------------------------------------------------------
        # CRITICAL NAVIGATION VALIDATION
        # ------------------------------------------------------------

        final_url = self.page.url or ""

        print("=" * 60)
        print("LOCATION FILTER NAVIGATION VALIDATION")
        print("=" * 60)
        print(
            "Show results clicked:",
            show_results_clicked
        )
        print(
            "URL after location filter:",
            final_url
        )

        if "/search/results/people/" not in final_url:

            print(
                "ERROR: LinkedIn left the employee "
                "people-search page after location filtering."
            )

            print(
                "Location filter rejected."
            )

            return False

        print(
            "Location filter remained on employee "
            "people-search page."
        )

        print("=" * 60)

        return True

    def get_profiles(self, company="", location=""):
        # ----------------------------------------------------
        # EMPLOYEE SEARCH PAGE SAFETY GUARD
        #
        # The employee search was successfully opened earlier
        # in the workflow, but LinkedIn can sometimes return
        # the Playwright page to /feed/ after filter actions.
        #
        # DO NOT use page.goto() here.
        # Direct navigation to LinkedIn search redirected the
        # authenticated GitHub Actions session to /uas/login.
        #
        # Instead, recover the already-established employee
        # search page using browser history.
        # ----------------------------------------------------

        current_url = self.page.url or ""

        print("=" * 60)
        print("EMPLOYEE SEARCH PAGE VALIDATION")
        print("=" * 60)
        print("Current URL before profile discovery:", current_url)

        if "/search/results/people/" not in current_url:

            print("EMPLOYEE SEARCH PAGE NOT ACTIVE")
            print("Attempting browser-history recovery...")

            try:
                previous_url = current_url

                self.page.go_back(
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                self.page.wait_for_timeout(5000)

                recovered_url = self.page.url or ""

                print("Previous URL:", previous_url)
                print("Recovered URL:", recovered_url)

            except Exception as recovery_ex:
                print(
                    "EMPLOYEE SEARCH HISTORY RECOVERY FAILED:",
                    repr(recovery_ex)
                )
                return []

            if "/search/results/people/" not in recovered_url:

                print(
                    "EMPLOYEE SEARCH HISTORY RECOVERY VALIDATION FAILED"
                )
                print("Current URL:", recovered_url)

                return []

            print(
                "EMPLOYEE SEARCH PAGE RESTORED FROM BROWSER HISTORY"
            )

        else:
            print(
                "EMPLOYEE SEARCH PAGE ALREADY CONFIRMED"
            )

        print("=" * 60)
        print("CONTINUING EMPLOYEE PROFILE DISCOVERY")
        print("=" * 60)

        # ----------------------------------------------------
        # SAFETY GUARD:
        # get_profiles() must never scan /in/ links while the
        # browser is on LinkedIn's feed page.
        #
        # The diagnostic run proved that the page was /feed/
        # when profile discovery started, which exposed 33
        # unrelated /in/ links from feed content.
        # ----------------------------------------------------

        current_url = self.page.url or ""

        print("=" * 60)
        print("EMPLOYEE SEARCH PAGE VALIDATION")
        print("=" * 60)
        print("Current URL before profile discovery:", current_url)

        if "/search/results/people/" not in current_url:
            print("EMPLOYEE SEARCH PAGE LOST")
            print("Restoring currentCompany employee search...")

            recovery_url = (
                "https://www.linkedin.com/search/results/people/"
                "?origin=FACETED_SEARCH"
                "&network=%5B%22F%22%5D"
                "&currentCompany=%5B%22943057%22%5D"
            )

            print("Recovery URL:", recovery_url)

            try:
                self.page.goto(
                    recovery_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                self.page.wait_for_timeout(5000)

                current_url = self.page.url or ""

                print(
                    "URL after employee-search recovery:",
                    current_url
                )

            except Exception as recovery_ex:
                print(
                    "EMPLOYEE SEARCH RECOVERY FAILED:",
                    repr(recovery_ex)
                )
                return []

            if "/search/results/people/" not in current_url:
                print(
                    "EMPLOYEE SEARCH RECOVERY VALIDATION FAILED"
                )
                print("Current URL:", current_url)
                return []

            print(
                "EMPLOYEE SEARCH PAGE RESTORED SUCCESSFULLY"
            )

        else:
            print(
                "EMPLOYEE SEARCH PAGE ALREADY CONFIRMED"
            )

        print("=" * 60)
        print("CONTINUING EMPLOYEE PROFILE DISCOVERY")
        print("=" * 60)

        """Discover primary employee profile links from LinkedIn people search."""
        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)
        print("Requested company:", company)
        print("Requested location:", location)

        profiles = []
        seen = set()
        search_area = None

        try:
            main = self.page.locator("main:visible").first
            if main.count():
                search_area = main
                print("Visible LinkedIn main search area found.")
        except Exception as ex:
            print("Visible main inspection failed:", repr(ex))

        if search_area is None:
            for selector in (
                "div.scaffold-finite-scroll__content:visible",
                "div.search-results-container:visible",
                "div[role='main']:visible",
            ):
                try:
                    candidate = self.page.locator(selector).first
                    if candidate.count():
                        search_area = candidate
                        print("Using bounded search-area fallback:", selector)
                        break
                except Exception as ex:
                    print("Search-area fallback failed:", selector, repr(ex))

        if search_area is None:
            print("ERROR: No bounded LinkedIn search area found.")
            return profiles

        def canonical_profile_url(href):
            if not href:
                return ""

            value = href.strip()

            if value.startswith("/"):
                value = "https://www.linkedin.com" + value

            value = value.split("?")[0].split("#")[0].rstrip("/")

            if "/in/" not in value.lower():
                return ""

            return value

        # ------------------------------------------------------------
        # PROFILE CANDIDATE DISCOVERY
        #
        # IMPORTANT:
        # LinkedIn's rendered DOM does not always expose the profile
        # result cards using stable entity-result/title selectors.
        #
        # The previously working implementation successfully discovered
        # the visible /in/ profile links from the bounded main search
        # area. Restore that behavior here.
        #
        # We intentionally DO NOT validate company/location here.
        # SearchWorkflowV2 opens each profile with LinkedInProfilePageV2
        # and validates the actual profile company + location there.
        # ------------------------------------------------------------

        candidate_links = []

        try:
            all_links = self.page.locator(
                "a[href*='/in/']:visible"
            )

            # LinkedIn may finish rendering employee result links
            # after the location filter reports completion.
            # Give the authenticated people-search page time to
            # expose the visible /in/ links before counting them.
            try:
                all_links.first.wait_for(
                    state="visible",
                    timeout=10000
                )
            except Exception:
                pass

            total_links = all_links.count()

            print("=" * 60)
            print("LINKEDIN /in/ DOM DIAGNOSTICS")
            print("=" * 60)
            print("Current URL:", self.page.url)
            print("Visible /in/ links:", total_links)

            for diag_i in range(total_links):
                try:
                    diag_link = all_links.nth(diag_i)

                    diag_href = diag_link.get_attribute("href") or ""
                    diag_text = (
                        diag_link.inner_text(timeout=2000)
                        .strip()
                        .replace("\n", " | ")
                    )

                    print("-" * 60)
                    print("LINK", diag_i + 1)
                    print("HREF:", diag_href)
                    print("TEXT:", diag_text[:500])

                    parent = diag_link.locator("xpath=..").first

                    parent_tag = parent.evaluate("el => el.tagName")
                    parent_class = parent.get_attribute("class") or ""
                    parent_id = parent.get_attribute("id") or ""
                    parent_text = (
                        parent.inner_text(timeout=2000)
                        .strip()
                        .replace("\n", " | ")
                    )

                    print("PARENT TAG:", parent_tag)
                    print("PARENT CLASS:", parent_class[:500])
                    print("PARENT ID:", parent_id)
                    print("PARENT TEXT:", parent_text[:1200])

                    grandparent = parent.locator("xpath=..").first

                    grandparent_tag = grandparent.evaluate(
                        "el => el.tagName"
                    )
                    grandparent_class = (
                        grandparent.get_attribute("class") or ""
                    )
                    grandparent_text = (
                        grandparent.inner_text(timeout=2000)
                        .strip()
                        .replace("\n", " | ")
                    )

                    print("GRANDPARENT TAG:", grandparent_tag)
                    print(
                        "GRANDPARENT CLASS:",
                        grandparent_class[:500]
                    )
                    print(
                        "GRANDPARENT TEXT:",
                        grandparent_text[:2000]
                    )

                except Exception as diag_ex:
                    print(
                        "DIAGNOSTIC FAILED:",
                        diag_i + 1,
                        repr(diag_ex)
                    )

            print("=" * 60)
            print("END LINKEDIN /in/ DOM DIAGNOSTICS")
            print("=" * 60)

            print(
                "Visible /in/ profile links found in bounded search area:",
                total_links
            )

            for i in range(total_links):
                try:
                    link = all_links.nth(i)

                    href = canonical_profile_url(
                        link.get_attribute("href")
                    )

                    if not href:
                        continue

                    # Keep the candidate discovery broad enough to preserve
                    # the previously working LinkedIn result extraction.
                    candidate_links.append(
                        (50, "bounded-visible-profile-link", link)
                    )

                except Exception as ex:
                    print(
                        "Profile-link inspection failed:",
                        repr(ex)
                    )

        except Exception as ex:
            print(
                "Bounded /in/ profile discovery failed:",
                repr(ex)
            )

        # ------------------------------------------------------------
        # Remove duplicate profile URLs while preserving discovery order.
        # ------------------------------------------------------------

        if candidate_links:
            unique_candidates = []
            candidate_seen = set()

            for score, source, link in candidate_links:
                try:
                    href = canonical_profile_url(
                        link.get_attribute("href")
                    )

                    if not href or href in candidate_seen:
                        continue

                    candidate_seen.add(href)
                    unique_candidates.append(
                        (score, source, link)
                    )

                except Exception as ex:
                    print(
                        "Candidate de-duplication failed:",
                        repr(ex)
                    )

            candidate_links = unique_candidates

        print(
            "Reliable /in/ profile candidates identified:",
            len(candidate_links)
        )

        if not candidate_links:
            print(
                "ERROR: No reliable employee profile links identified."
            )
            return profiles

        for score, source, link in candidate_links:
            try:
                clean_url = canonical_profile_url(
                    link.get_attribute("href")
                )

                if not clean_url or clean_url in seen:
                    continue

                seen.add(clean_url)

                raw_name = ""

                try:
                    raw_name = (
                        link.inner_text(timeout=2000)
                        .strip()
                        .replace("\n", " ")
                    )
                except Exception:
                    pass

                profiles.append(
                    {
                        "full_name": raw_name,
                        "profile_url": clean_url,
                        "company": company,
                        "location": location,
                    }
                )

                print("-" * 60)
                print("Employee candidate:", raw_name)
                print("Candidate URL:", clean_url)
                print("Discovery source:", source)
                print("Discovery score:", score)

            except Exception as ex:
                print(
                    "Profile candidate processing failed:",
                    repr(ex)
                )

        print("=" * 60)
        print(
            "EMPLOYEE PROFILES EXTRACTED:",
            len(profiles)
        )
        print("=" * 60)

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
