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

        starting_url = self.page.url or ""

        print(
            "URL before location filter:",
            starting_url
        )

        # ------------------------------------------------------------
        # SAFETY CHECK
        #
        # Location filtering is only valid from the authenticated
        # LinkedIn company people-search page.
        #
        # Never attempt this operation from /feed/, /login/,
        # /authwall/ or a generic search page.
        # ------------------------------------------------------------

        if "/search/results/people/" not in starting_url.lower():

            print(
                "ERROR: Location filter started outside "
                "the people-search page."
            )

            return False

        if "currentcompany=" not in starting_url.lower():

            print(
                "ERROR: People-search URL does not contain "
                "currentCompany."
            )

            return False

        # ------------------------------------------------------------
        # Dismiss only an unrelated blocking dialog if one exists.
        #
        # IMPORTANT:
        # Do not blindly press Escape when the location dialog itself
        # is open.
        # ------------------------------------------------------------

        try:

            dialogs = self.page.locator(
                "dialog[open]:visible, [role='dialog']:visible"
            )

            dialog_count = dialogs.count()

            print(
                "Visible dialogs before Locations:",
                dialog_count
            )

            for i in range(dialog_count):

                try:

                    dialog = dialogs.nth(i)

                    dialog_text = (
                        dialog.inner_text(
                            timeout=2000
                        )
                        .strip()
                        .replace("\n", " ")
                    )

                    print(
                        "Existing dialog:",
                        dialog_text[:300]
                    )

                except Exception:
                    pass

        except Exception as ex:

            print(
                "Dialog inspection failed:",
                repr(ex)
            )

        # ------------------------------------------------------------
        # OPEN LOCATIONS FILTER
        #
        # Do not use Locator.filter(visible=True).
        # Playwright Python does not support that argument.
        #
        # Instead, inspect each matching element with is_visible().
        # ------------------------------------------------------------

        try:

            locations = self.page.get_by_text(
                "Locations",
                exact=True
            )

            location_count = locations.count()

            print(
                "Locations elements found:",
                location_count
            )

            clicked_locations = False

            for i in range(
                location_count - 1,
                -1,
                -1
            ):

                try:

                    candidate = locations.nth(i)

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

                except Exception as ex:

                    print(
                        "Locations candidate",
                        i,
                        "could not be clicked:",
                        repr(ex)
                    )

            if not clicked_locations:

                # Controlled fallback for LinkedIn DOM variants.
                locations = self.page.get_by_text(
                    "Locations",
                    exact=False
                )

                location_count = locations.count()

                for i in range(
                    location_count - 1,
                    -1,
                    -1
                ):

                    try:

                        candidate = locations.nth(i)

                        if not candidate.is_visible():
                            continue

                        candidate.click(
                            timeout=15000
                        )

                        clicked_locations = True

                        print(
                            "Locations filter opened "
                            "using fallback text match."
                        )

                        break

                    except Exception:
                        continue

            if not clicked_locations:

                print(
                    "ERROR: Could not safely open Locations filter."
                )

                return False

        except Exception as ex:

            print(
                "Locations filter discovery failed:",
                repr(ex)
            )

            return False

        self.page.wait_for_timeout(1500)

        # ------------------------------------------------------------
        # LOCATION INPUT
        #
        # Use only visible inputs.
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

        # Allow LinkedIn's suggestion list to render.
        self.page.wait_for_timeout(2500)

        # ------------------------------------------------------------
        # SELECT LOCATION SUGGESTION
        #
        # THIS IS THE CRITICAL FIX.
        #
        # Do NOT use:
        #
        #     ArrowDown
        #     Enter
        #
        # because Enter can submit/close the LinkedIn filter dialog
        # before Show results is clicked.
        #
        # Instead, click the actual visible suggestion.
        # ------------------------------------------------------------

        suggestion_clicked = False

        try:

            # First try semantic listbox options.
            options = self.page.locator(
                "[role='option']:visible"
            )

            option_count = options.count()

            print(
                "Visible location options:",
                option_count
            )

            requested_location = (
                location.strip().lower()
            )

            for i in range(
                option_count
            ):

                try:

                    option = options.nth(i)

                    option_text = (
                        option.inner_text(
                            timeout=2000
                        )
                        .strip()
                        .replace("\n", " ")
                    )

                    print(
                        "Location option:",
                        option_text[:300]
                    )

                    if (
                        option_text.lower()
                        == requested_location
                        or requested_location
                        in option_text.lower()
                    ):

                        option.click(
                            timeout=15000
                        )

                        suggestion_clicked = True

                        print(
                            "Location suggestion clicked:",
                            option_text
                        )

                        break

                except Exception:
                    continue

        except Exception as ex:

            print(
                "Location option inspection failed:",
                repr(ex)
            )

        # ------------------------------------------------------------
        # FALLBACK:
        #
        # Search visible exact text inside the active dialog.
        # We still CLICK the suggestion. We never press Enter.
        # ------------------------------------------------------------

        if not suggestion_clicked:

            try:

                dialogs = self.page.locator(
                    "dialog[open]:visible, [role='dialog']:visible"
                )

                dialog_count = dialogs.count()

                print(
                    "Visible dialogs while locating "
                    "location suggestion:",
                    dialog_count
                )

                requested_location = (
                    location.strip().lower()
                )

                for dialog_index in range(
                    dialog_count - 1,
                    -1,
                    -1
                ):

                    try:

                        dialog = dialogs.nth(
                            dialog_index
                        )

                        matches = dialog.get_by_text(
                            location,
                            exact=True
                        )

                        match_count = matches.count()

                        for i in range(
                            match_count - 1,
                            -1,
                            -1
                        ):

                            try:

                                match = matches.nth(i)

                                if not match.is_visible():
                                    continue

                                match.click(
                                    timeout=15000
                                )

                                suggestion_clicked = True

                                print(
                                    "Location suggestion clicked "
                                    "inside active dialog."
                                )

                                break

                            except Exception:
                                continue

                        if suggestion_clicked:
                            break

                    except Exception:
                        continue

            except Exception as ex:

                print(
                    "Dialog location suggestion fallback failed:",
                    repr(ex)
                )

        if not suggestion_clicked:

            # Last controlled fallback: visible text anywhere,
            # but still require an actual click.
            try:

                matches = self.page.get_by_text(
                    location,
                    exact=True
                )

                match_count = matches.count()

                print(
                    "Exact location text matches:",
                    match_count
                )

                for i in range(
                    match_count - 1,
                    -1,
                    -1
                ):

                    try:

                        match = matches.nth(i)

                        if not match.is_visible():
                            continue

                        match.click(
                            timeout=15000
                        )

                        suggestion_clicked = True

                        print(
                            "Location suggestion clicked "
                            "using exact-text fallback."
                        )

                        break

                    except Exception:
                        continue

            except Exception as ex:

                print(
                    "Exact location fallback failed:",
                    repr(ex)
                )

        if not suggestion_clicked:

            print(
                "ERROR: Could not safely select the "
                "LinkedIn location suggestion."
            )

            print(
                "Current URL:",
                self.page.url
            )

            return False

        # IMPORTANT:
        # Do not press Enter here.
        self.page.wait_for_timeout(1000)

        # ------------------------------------------------------------
        # SHOW RESULTS
        #
        # Search ONLY the active dialog first.
        # Match the actual button text exactly.
        # ------------------------------------------------------------

        show_results_clicked = False

        try:

            dialogs = self.page.locator(
                "dialog[open]:visible, [role='dialog']:visible"
            )

            dialog_count = dialogs.count()

            print(
                "Visible dialogs before Show results:",
                dialog_count
            )

            for dialog_index in range(
                dialog_count - 1,
                -1,
                -1
            ):

                try:

                    dialog = dialogs.nth(
                        dialog_index
                    )

                    buttons = dialog.locator(
                        "button:visible"
                    )

                    button_count = buttons.count()

                    for button_index in range(
                        button_count - 1,
                        -1,
                        -1
                    ):

                        try:

                            button = buttons.nth(
                                button_index
                            )

                            button_text = (
                                button.inner_text(
                                    timeout=2000
                                )
                                .strip()
                                .replace("\n", " ")
                            )

                            if (
                                button_text.lower()
                                == "show results"
                            ):

                                print(
                                    "Found Show results "
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

                except Exception:
                    continue

        except Exception as ex:

            print(
                "Active dialog Show results inspection failed:",
                repr(ex)
            )

        # ------------------------------------------------------------
        # FALLBACK:
        # Search visible button elements only.
        # ------------------------------------------------------------

        if not show_results_clicked:

            try:

                buttons = self.page.locator(
                    "button:visible"
                )

                button_count = buttons.count()

                print(
                    "Visible buttons on page:",
                    button_count
                )

                for i in range(
                    button_count - 1,
                    -1,
                    -1
                ):

                    try:

                        button = buttons.nth(i)

                        button_text = (
                            button.inner_text(
                                timeout=2000
                            )
                            .strip()
                            .replace("\n", " ")
                        )

                        if (
                            button_text.lower()
                            == "show results"
                        ):

                            print(
                                "Found visible Show results button."
                            )

                            button.click(
                                timeout=15000
                            )

                            show_results_clicked = True

                            print(
                                "Clicked visible Show results."
                            )

                            break

                    except Exception:
                        continue

            except Exception as ex:

                print(
                    "Visible Show results fallback failed:",
                    repr(ex)
                )

        if not show_results_clicked:

            print(
                "ERROR: Could not safely click Show results."
            )

            print(
                "Current URL:",
                self.page.url
            )

            return False

        # ------------------------------------------------------------
        # WAIT FOR LINKEDIN TO UPDATE RESULTS
        # ------------------------------------------------------------

        self.page.wait_for_timeout(
            5000
        )

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

        # ------------------------------------------------------------
        # FINAL SAFETY CHECK
        #
        # The filter operation is successful ONLY if LinkedIn
        # remains on the company people-search page.
        # ------------------------------------------------------------

        if "/search/results/people/" not in final_url.lower():

            print(
                "ERROR: LinkedIn left the employee "
                "people-search page after location filtering."
            )

            print(
                "Location filter rejected."
            )

            return False

        if "currentcompany=" not in final_url.lower():

            print(
                "ERROR: Location filter removed currentCompany."
            )

            print(
                "Location filter rejected."
            )

            return False

        print(
            "Location filter successfully remained on "
            "the authenticated company people-search page."
        )

        print("=" * 60)

        return True

    def get_profiles(self, company="", location=""):

        # ------------------------------------------------------------
        # EMPLOYEE SEARCH PAGE SAFETY GUARD
        #
        # get_profiles() must NEVER attempt to recover the page by:
        #
        #   - browser history
        #   - page.goto()
        #   - a hard-coded company ID
        #   - generic people search
        #
        # The workflow must arrive here with the correct authenticated
        # company people-search page already active.
        # ------------------------------------------------------------

        current_url = self.page.url or ""

        print("=" * 60)
        print("EMPLOYEE SEARCH PAGE VALIDATION")
        print("=" * 60)
        print(
            "Current URL before profile discovery:",
            current_url
        )

        if "/search/results/people/" not in current_url.lower():

            print(
                "ERROR: EMPLOYEE SEARCH PAGE IS NOT ACTIVE."
            )

            print(
                "Profile discovery stopped safely."
            )

            return []

        if "currentcompany=" not in current_url.lower():

            print(
                "ERROR: EMPLOYEE SEARCH URL DOES NOT "
                "CONTAIN currentCompany."
            )

            print(
                "Profile discovery stopped safely."
            )

            return []

        print(
            "EMPLOYEE SEARCH PAGE CONFIRMED."
        )

        print("=" * 60)
        print("CONTINUING EMPLOYEE PROFILE DISCOVERY")
        print("=" * 60)

        # ------------------------------------------------------------
        # The remainder of the existing profile-discovery logic is
        # deliberately preserved.
        #
        # Only the unsafe recovery code above has been removed.
        # ------------------------------------------------------------

        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)
        print("Requested company:", company)
        print("Requested location:", location)

        profiles = []
        seen = set()
        search_area = None

        try:

            main = self.page.locator(
                "main:visible"
            ).first

            if main.count():

                search_area = main

                print(
                    "Visible LinkedIn main search area found."
                )

        except Exception as ex:

            print(
                "Visible main inspection failed:",
                repr(ex)
            )

        if search_area is None:

            for selector in (
                "div.scaffold-finite-scroll__content:visible",
                "div.search-results-container:visible",
                "div[role='main']:visible",
            ):

                try:

                    candidate = self.page.locator(
                        selector
                    ).first

                    if candidate.count():

                        search_area = candidate

                        print(
                            "Using bounded search-area fallback:",
                            selector
                        )

                        break

                except Exception as ex:

                    print(
                        "Search-area fallback failed:",
                        selector,
                        repr(ex)
                    )

        if search_area is None:

            print(
                "ERROR: No bounded LinkedIn search area found."
            )

            return profiles

        def canonical_profile_url(href):

            if not href:
                return ""

            value = href.strip()

            if value.startswith("/"):

                value = (
                    "https://www.linkedin.com"
                    + value
                )

            value = (
                value
                .split("?")[0]
                .split("#")[0]
                .rstrip("/")
            )

            if "/in/" not in value.lower():
                return ""

            return value

        # ------------------------------------------------------------
        # PROFILE CANDIDATE DISCOVERY
        #
        # IMPORTANT:
        # Search ONLY inside the bounded employee-search area.
        #
        # Never scan the entire LinkedIn document while looking for
        # employee profiles.
        # ------------------------------------------------------------

        candidate_links = []

        try:

            all_links = search_area.locator(
                "a[href*='/in/']:visible"
            )

            try:

                all_links.first.wait_for(
                    state="visible",
                    timeout=10000
                )

            except Exception:

                pass

            total_links = all_links.count()

            print(
                "Visible /in/ links inside bounded "
                "employee search area:",
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

                    candidate_links.append(
                        (
                            50,
                            "bounded-visible-profile-link",
                            link
                        )
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
        # Remove duplicate profile URLs while preserving order.
        # ------------------------------------------------------------

        if candidate_links:

            unique_candidates = []
            candidate_seen = set()

            for score, source, link in candidate_links:

                try:

                    href = canonical_profile_url(
                        link.get_attribute("href")
                    )

                    if (
                        not href
                        or href in candidate_seen
                    ):
                        continue

                    candidate_seen.add(href)

                    unique_candidates.append(
                        (
                            score,
                            source,
                            link
                        )
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

                if (
                    not clean_url
                    or clean_url in seen
                ):
                    continue

                seen.add(clean_url)

                raw_name = ""

                try:

                    raw_name = (
                        link.inner_text(
                            timeout=2000
                        )
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
                print(
                    "Employee candidate:",
                    raw_name
                )
                print(
                    "Candidate URL:",
                    clean_url
                )
                print(
                    "Discovery source:",
                    source
                )
                print(
                    "Discovery score:",
                    score
                )

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
