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
        """
        Apply a LinkedIn location filter to the CURRENT company-scoped
        people-search page.

        The important part of this method is the dropdown selection:
        LinkedIn renders the location picker as a list of individual rows.
        We select an individual row whose OWN visible text represents the
        requested location. We never click the dropdown container itself.

        Examples:
            New Jersey
                -> New Jersey, United States

            Clifton, New Jersey
                -> Clifton, New Jersey, United States

            Austin, Texas
                -> Austin, Texas, United States
        """

        print("=" * 60)
        print("APPLYING LOCATION FILTER")
        print("=" * 60)

        requested_location = str(location or "").strip()

        if not requested_location:
            print("[LOCATION ERROR] Empty location was supplied.")
            return False

        print("Requested location:", requested_location)

        before_url = self.page.url
        print("URL before location filter:", before_url)

        def normalize(value):
            if value is None:
                return ""

            value = (
                str(value)
                .replace("\xa0", " ")
                .replace("\n", " ")
                .replace("\r", " ")
            )

            return re.sub(r"\s+", " ", value).strip().lower()

        requested_norm = normalize(requested_location)

        def query_values(url, key):
            try:
                from urllib.parse import urlsplit, parse_qs

                return parse_qs(
                    urlsplit(url).query,
                    keep_blank_values=True
                ).get(key, [])

            except Exception:
                return []

        def is_company_people_search(url):
            if not url:
                return False

            lower = url.lower()

            return (
                "/search/results/people/" in lower
                and "currentcompany=" in lower
                and "/in/" not in lower
            )

        def has_location_filter(url):
            try:
                from urllib.parse import urlsplit, parse_qs

                query = parse_qs(
                    urlsplit(url).query,
                    keep_blank_values=True
                )

                # LinkedIn has used different parameter names for the
                # geographic filter. Do not hard-code a specific geo ID.
                for key in (
                    "geoUrn",
                    "facetGeoRegion",
                    "geoId",
                    "geo_id"
                ):
                    values = query.get(key)

                    if values and any(
                        str(value).strip()
                        for value in values
                    ):
                        return True

                return False

            except Exception:
                return False

        # ------------------------------------------------------------
        # SAFETY CHECK #1
        #
        # Location must be applied only to the company-scoped people
        # search that open_employees_page() already established.
        # ------------------------------------------------------------

        if not is_company_people_search(before_url):
            print(
                "[LOCATION ERROR] Current page is not the selected "
                "company's people-search."
            )
            return False

        original_company_values = query_values(
            before_url,
            "currentCompany"
        )

        if not original_company_values:
            print(
                "[LOCATION ERROR] currentCompany could not be read "
                "from the current URL."
            )
            return False

        print(
            "Original currentCompany:",
            original_company_values
        )

        # ------------------------------------------------------------
        # 1. OPEN LOCATIONS
        # ------------------------------------------------------------

        try:
            locations = self.page.get_by_text(
                "Locations",
                exact=True
            )

            location_count = locations.count()

            print(
                "Exact Locations matches:",
                location_count
            )

            opened = False

            for index in range(location_count):
                try:
                    item = locations.nth(index)

                    if not item.is_visible():
                        continue

                    item.click(timeout=10000)

                    opened = True

                    print(
                        f"Clicked Locations filter #{index + 1}"
                    )

                    break

                except Exception as ex:
                    print(
                        f"Locations click #{index + 1} failed:",
                        repr(ex)
                    )

            if not opened:
                print(
                    "[LOCATION ERROR] Could not open Locations filter."
                )
                return False

        except Exception as ex:
            print(
                "[LOCATION ERROR] Opening Locations failed:",
                repr(ex)
            )
            return False

        self.page.wait_for_timeout(1000)

        # ------------------------------------------------------------
        # 2. FIND THE ACTUAL "ADD A LOCATION" INPUT
        # ------------------------------------------------------------

        try:
            inputs = self.page.locator(
                "input[placeholder='Add a location']:visible"
            )

            input_count = inputs.count()

            print(
                "Visible Add a location inputs:",
                input_count
            )

            if input_count == 0:
                print(
                    "[LOCATION ERROR] No visible Add a location input found."
                )
                return False

            location_box = inputs.last

            print(
                "Location input placeholder:",
                location_box.get_attribute("placeholder")
            )

        except Exception as ex:
            print(
                "[LOCATION ERROR] Location input lookup failed:",
                repr(ex)
            )
            return False

        # ------------------------------------------------------------
        # Helper: keep suggestion candidates inside the autocomplete
        # area directly below the location input.
        #
        # This prevents a matching "New Jersey" text elsewhere on the
        # page from ever being selected.
        # ------------------------------------------------------------

        def is_dropdown_candidate_box(box):
            try:
                input_box = location_box.bounding_box()

                if not input_box or not box:
                    return False

                input_bottom = (
                    input_box["y"] +
                    input_box["height"]
                )

                return (
                    box["y"] >= input_bottom - 5
                    and
                    box["y"] <= input_bottom + 450
                    and
                    box["x"] <= (
                        input_box["x"] +
                        input_box["width"] +
                        350
                    )
                    and
                    (
                        box["x"] +
                        box["width"]
                    ) >= max(
                        0,
                        input_box["x"] - 100
                    )
                )

            except Exception:
                return False

        # ------------------------------------------------------------
        # 3. TYPE LOCATION
        #
        # press_sequentially() is intentional. LinkedIn's autocomplete
        # reacts to keyboard/input events and can fail to populate the
        # suggestion list when the value is injected too quickly.
        # ------------------------------------------------------------

        try:
            location_box.click(timeout=10000)
            location_box.fill("")

            location_box.press_sequentially(
                requested_location,
                delay=100
            )

            print(
                "[LOCATION] Typed:",
                requested_location
            )

        except Exception as ex:
            print(
                "[LOCATION ERROR] Could not type location:",
                repr(ex)
            )
            return False

        # Allow LinkedIn autocomplete to render.
        self.page.wait_for_timeout(2500)

        # ------------------------------------------------------------
        # 4. LOCATION SUGGESTION MATCHING
        #
        # Screenshot-confirmed LinkedIn behavior:
        #
        #   New Jersey, United States
        #   Jersey City, New Jersey, United States
        #   Newark, New Jersey, United States
        #   ...
        #
        # For "New Jersey", the correct row is therefore:
        #
        #   New Jersey, United States
        #
        # The old implementation inspected a large parent container.
        # Its center could land on "Clifton" even though "New Jersey"
        # was the requested value.
        #
        # This implementation NEVER clicks the aggregate dropdown.
        # It looks for the individual visible text row.
        # ------------------------------------------------------------

        def represents_requested_location(text):
            value = normalize(text)

            if not value:
                return False

            # Exact match.
            if value == requested_norm:
                return True

            # State/region/country suggestion.
            if value == requested_norm + ", united states":
                return True

            # City/locality suggestion:
            #
            # requested = "clifton"
            # candidate  = "clifton, new jersey, united states"
            #
            # Only accept a candidate whose FIRST component is exactly
            # the requested value. This prevents:
            #
            # "New Jersey, United States Jersey City, ..."
            #
            # from ever being accepted as a single suggestion.
            if value.startswith(requested_norm + ","):
                parts = [
                    part.strip()
                    for part in value.split(",")
                ]

                if len(parts) >= 2:
                    first_part = parts[0]

                    if first_part != requested_norm:
                        return False

                    # A normal LinkedIn location suggestion is short.
                    # Reject giant aggregate/container text.
                    if len(value) > max(
                        160,
                        len(requested_norm) + 120
                    ):
                        return False

                    # If country is present, it must be the final
                    # component. This is deliberately permissive about
                    # the middle state/region component.
                    if "united states" in parts:
                        if parts[-1] != "united states":
                            return False

                    return True

            return False

        def get_location_candidates():
            """
            Return visible individual autocomplete rows.

            We first use semantic/accessibility locators and then use a
            DOM fallback. In both cases the candidate's OWN rendered text
            must match the requested location.
            """

            candidates = []

            # --------------------------------------------------------
            # Candidate labels that LinkedIn commonly renders.
            #
            # For the screenshot:
            #     requested = "New Jersey"
            #     exact_label = "New Jersey, United States"
            # --------------------------------------------------------

            exact_labels = [
                requested_norm,
                requested_norm + ", united states"
            ]

            # Remove duplicates while preserving order.
            exact_labels = list(
                dict.fromkeys(exact_labels)
            )

            # --------------------------------------------------------
            # A. Accessibility / text locators.
            #
            # get_by_text() is intentionally used with exact=True.
            # This prevents "New Jersey" from matching the entire
            # dropdown containing Jersey City, Newark, Clifton, etc.
            # --------------------------------------------------------

            # Playwright exact text matching is case-sensitive, so keep
            # the user's original capitalization for the locator itself.
            display_labels = [
                requested_location,
                requested_location + ", United States"
            ]

            display_labels = list(
                dict.fromkeys(display_labels)
            )

            for label in display_labels:
                try:
                    locator = self.page.get_by_text(
                        label,
                        exact=True
                    )

                    count = locator.count()

                    print(
                        f'Exact suggestion text "{label}" matches:',
                        count
                    )

                    for index in range(count):
                        try:
                            item = locator.nth(index)

                            if not item.is_visible():
                                continue

                            text = normalize(
                                item.inner_text(timeout=1000)
                            )

                            if not represents_requested_location(text):
                                continue

                            box = item.bounding_box()

                            if not box:
                                continue

                            if not is_dropdown_candidate_box(box):
                                continue

                            candidates.append(
                                {
                                    "locator": item,
                                    "text": text,
                                    "x": box["x"],
                                    "y": box["y"],
                                    "width": box["width"],
                                    "height": box["height"],
                                    "area": (
                                        box["width"]
                                        * box["height"]
                                    ),
                                    "source": (
                                        "get_by_text_exact"
                                    )
                                }
                            )

                        except Exception:
                            continue

                except Exception as ex:
                    print(
                        "Exact text candidate scan failed:",
                        repr(ex)
                    )

            # --------------------------------------------------------
            # A2. REGEX TEXT FALLBACK
            #
            # This handles a city typed without a state:
            #
            #     requested = "Clifton"
            #     LinkedIn   = "Clifton, New Jersey, United States"
            #
            # It is still filtered through represents_requested_location()
            # before it can be clicked.
            # --------------------------------------------------------

            try:
                escaped_requested = re.escape(
                    requested_location
                )

                regex_locator = self.page.get_by_text(
                    re.compile(
                        rf"^\s*{escaped_requested}"
                        rf"(?:\s*,\s*[^,]+)?"
                        rf"(?:\s*,\s*United States)?"
                        rf"\s*$",
                        re.IGNORECASE
                    )
                )

                count = regex_locator.count()

                print(
                    "Regex location suggestion matches:",
                    count
                )

                for index in range(count):
                    try:
                        item = regex_locator.nth(index)

                        if not item.is_visible():
                            continue

                        text = normalize(
                            item.inner_text(timeout=1000)
                        )

                        if not represents_requested_location(text):
                            continue

                        box = item.bounding_box()

                        if not box:
                            continue

                        candidates.append(
                            {
                                "locator": item,
                                "text": text,
                                "x": box["x"],
                                "y": box["y"],
                                "width": box["width"],
                                "height": box["height"],
                                "area": (
                                    box["width"]
                                    * box["height"]
                                ),
                                "source": (
                                    "get_by_text_regex"
                                )
                            }
                        )

                    except Exception:
                        continue

            except Exception as ex:
                print(
                    "Regex location candidate scan failed:",
                    repr(ex)
                )

            # --------------------------------------------------------
            # B. Role-based fallback.
            #
            # Depending on LinkedIn's current DOM, the row can be
            # exposed as role=option, listitem, button, or a normal
            # clickable div.
            # --------------------------------------------------------

            for selector in (
                "[role='option']:visible",
                "li:visible",
                "button:visible"
            ):
                try:
                    locator = self.page.locator(selector)

                    count = locator.count()

                    for index in range(count):
                        try:
                            item = locator.nth(index)

                            if not item.is_visible():
                                continue

                            text = normalize(
                                item.inner_text(timeout=500)
                            )

                            if not represents_requested_location(text):
                                continue

                            box = item.bounding_box()

                            if not box:
                                continue

                            if not is_dropdown_candidate_box(box):
                                continue

                            candidates.append(
                                {
                                    "locator": item,
                                    "text": text,
                                    "x": box["x"],
                                    "y": box["y"],
                                    "width": box["width"],
                                    "height": box["height"],
                                    "area": (
                                        box["width"]
                                        * box["height"]
                                    ),
                                    "source": selector
                                }
                            )

                        except Exception:
                            continue

                except Exception:
                    continue

            # --------------------------------------------------------
            # C. DOM fallback.
            #
            # This is intentionally simple:
            # inspect visible elements near the input and accept only
            # elements whose OWN innerText is the location.
            #
            # We do NOT inspect the center of the dropdown and we do
            # NOT click a parent that contains multiple locations.
            # --------------------------------------------------------

            try:
                input_box = location_box.bounding_box()

                if input_box:
                    dom_candidates = self.page.evaluate(
                        """
                        ({inputBox, requested}) => {
                            const norm = value =>
                                String(value || "")
                                    .replace(/\\s+/g, " ")
                                    .trim()
                                    .toLowerCase();

                            const req = norm(requested);

                            const represents = text => {
                                const value = norm(text);

                                if (!value) {
                                    return false;
                                }

                                if (value === req) {
                                    return true;
                                }

                                if (
                                    value ===
                                    req + ", united states"
                                ) {
                                    return true;
                                }

                                if (
                                    !value.startsWith(
                                        req + ","
                                    )
                                ) {
                                    return false;
                                }

                                const parts = value
                                    .split(",")
                                    .map(x => x.trim());

                                if (parts.length < 2) {
                                    return false;
                                }

                                if (parts[0] !== req) {
                                    return false;
                                }

                                if (
                                    value.length >
                                    Math.max(
                                        160,
                                        req.length + 120
                                    )
                                ) {
                                    return false;
                                }

                                if (
                                    parts.includes(
                                        "united states"
                                    ) &&
                                    parts[
                                        parts.length - 1
                                    ] !== "united states"
                                ) {
                                    return false;
                                }

                                return true;
                            };

                            const visible = el => {
                                if (!el) {
                                    return false;
                                }

                                const style =
                                    getComputedStyle(el);

                                const rect =
                                    el.getBoundingClientRect();

                                return (
                                    style.display !== "none" &&
                                    style.visibility !== "hidden" &&
                                    style.opacity !== "0" &&
                                    rect.width > 0 &&
                                    rect.height > 0
                                );
                            };

                            const top =
                                inputBox.y +
                                inputBox.height;

                            const bottom =
                                top + 450;

                            const left =
                                Math.max(
                                    0,
                                    inputBox.x - 100
                                );

                            const right =
                                inputBox.x +
                                inputBox.width +
                                350;

                            const result = [];

                            for (
                                const el of
                                document.querySelectorAll("*")
                            ) {
                                if (!visible(el)) {
                                    continue;
                                }

                                const rect =
                                    el.getBoundingClientRect();

                                if (
                                    rect.bottom < top ||
                                    rect.top > bottom ||
                                    rect.right < left ||
                                    rect.left > right
                                ) {
                                    continue;
                                }

                                const text = norm(
                                    el.innerText ||
                                    el.textContent ||
                                    el.getAttribute(
                                        "aria-label"
                                    ) ||
                                    ""
                                );

                                if (!represents(text)) {
                                    continue;
                                }

                                result.push({
                                    text: text,
                                    x: rect.x,
                                    y: rect.y,
                                    width: rect.width,
                                    height: rect.height,
                                    area:
                                        rect.width *
                                        rect.height,
                                    tag:
                                        el.tagName,
                                    role:
                                        el.getAttribute(
                                            "role"
                                        ),
                                    html:
                                        el.outerHTML.slice(
                                            0,
                                            2000
                                        )
                                });
                            }

                            return result;
                        }
                        """,
                        {
                            "inputBox": input_box,
                            "requested": requested_location
                        }
                    )

                    print(
                        "DOM exact location candidates:",
                        len(dom_candidates or [])
                    )

                    # DOM results cannot be clicked directly because
                    # evaluate() returns serializable data. We use them
                    # only as diagnostics / confirmation that LinkedIn
                    # rendered the correct row.
                    for item in dom_candidates or []:
                        print(
                            "DOM candidate:",
                            item.get("text"),
                            item.get("tag"),
                            item.get("role"),
                            item.get("width"),
                            item.get("height")
                        )

            except Exception as ex:
                print(
                    "DOM location scan failed:",
                    repr(ex)
                )

            # --------------------------------------------------------
            # Deduplicate Playwright candidates.
            # Prefer the smallest exact element. This normally means
            # the inner <span> containing the suggestion text rather
            # than the entire autocomplete list.
            # --------------------------------------------------------

            unique = []

            seen = set()

            for candidate in candidates:
                key = (
                    candidate["text"],
                    round(candidate["x"], 1),
                    round(candidate["y"], 1),
                    round(candidate["width"], 1),
                    round(candidate["height"], 1)
                )

                if key in seen:
                    continue

                seen.add(key)
                unique.append(candidate)

            unique.sort(
                key=lambda item: (
                    0
                    if item["text"] ==
                    requested_norm
                    else 1,
                    item["area"],
                    item["y"]
                )
            )

            return unique

        # ------------------------------------------------------------
        # 5. WAIT FOR AND SELECT THE CORRECT INDIVIDUAL ROW
        # ------------------------------------------------------------

        selected = False

        # Autocomplete can take a little longer on a busy LinkedIn
        # session. Poll instead of performing one fragile scan.
        for attempt in range(1, 9):
            candidates = get_location_candidates()

            print(
                f"[LOCATION] Suggestion scan {attempt}/8:",
                len(candidates),
                "candidate(s)"
            )

            if candidates:
                for candidate in candidates:
                    try:
                        item = candidate["locator"]

                        if not item.is_visible():
                            continue

                        print(
                            "[LOCATION] Selecting exact row:",
                            candidate["text"],
                            "| source:",
                            candidate["source"],
                            "| area:",
                            candidate["area"]
                        )

                        # Scroll the individual row into view.
                        item.scroll_into_view_if_needed(
                            timeout=3000
                        )

                        # Normal click first. This bubbles naturally
                        # from a text span to LinkedIn's clickable row.
                        try:
                            item.click(
                                timeout=10000
                            )
                        except Exception as click_ex:
                            # The visible text may be a child <span> inside
                            # LinkedIn's clickable suggestion row. A normal
                            # click is preferred; if Playwright reports an
                            # interception/overlay issue, dispatch the click
                            # on that SAME exact text element. We never click
                            # the dropdown container or an arbitrary point.
                            print(
                                "[LOCATION] Normal exact-row click failed; "
                                "using DOM click on the same element:",
                                repr(click_ex)
                            )

                            item.evaluate(
                                """el => {
                                    el.scrollIntoView({
                                        block: "center",
                                        inline: "nearest"
                                    });
                                    el.click();
                                }"""
                            )

                        selected = True

                        print(
                            "[LOCATION] Exact location row clicked."
                        )

                        break

                    except Exception as ex:
                        print(
                            "[LOCATION] Candidate click failed:",
                            repr(ex)
                        )

                if selected:
                    break

            self.page.wait_for_timeout(750)

        if not selected:
            print("=" * 60)
            print("LOCATION SUGGESTION NOT SAFELY FOUND")
            print("=" * 60)
            print(
                "Requested:",
                requested_location
            )
            print(
                "No individual LinkedIn autocomplete row whose "
                "own text represents the requested location was found."
            )
            print(
                "Refusing to click the aggregate dropdown or another city."
            )
            return False

        # Give LinkedIn time to update the selected chip/state.
        self.page.wait_for_timeout(1000)

        # ------------------------------------------------------------
        # 6. CLICK SHOW RESULTS
        # ------------------------------------------------------------

        try:
            show_results = self.page.get_by_role(
                "button",
                name=re.compile(
                    r"^\s*show\s+results\s*$",
                    re.IGNORECASE
                )
            )

            count = show_results.count()

            print(
                "Show Results buttons:",
                count
            )

            clicked = False

            for index in range(count):
                try:
                    button = show_results.nth(index)

                    if not button.is_visible():
                        continue

                    button.click(timeout=10000)

                    clicked = True

                    print(
                        "Clicked Show Results."
                    )

                    break

                except Exception as ex:
                    print(
                        f"Show Results click #{index + 1} failed:",
                        repr(ex)
                    )

            # Text fallback for LinkedIn DOM variants that do not expose
            # the control as a normal accessible button.
            if not clicked:
                text_buttons = self.page.get_by_text(
                    "Show results",
                    exact=True
                )

                count = text_buttons.count()

                print(
                    "Exact Show results text matches:",
                    count
                )

                for index in range(count):
                    try:
                        item = text_buttons.nth(index)

                        if not item.is_visible():
                            continue

                        item.click(timeout=10000)

                        clicked = True

                        print(
                            "Clicked Show results text control."
                        )

                        break

                    except Exception:
                        continue

            if not clicked:
                print(
                    "[LOCATION ERROR] Show Results control could not be clicked."
                )
                return False

        except Exception as ex:
            print(
                "[LOCATION ERROR] Show Results handling failed:",
                repr(ex)
            )
            return False

        # ------------------------------------------------------------
        # 7. WAIT FOR THE REAL FILTERED URL
        #
        # Do not treat closing the popup as success.
        # Success requires:
        #   - people search page
        #   - SAME currentCompany
        #   - actual location filter in URL
        # ------------------------------------------------------------

        final_url = ""

        for attempt in range(1, 21):
            try:
                current = self.page.url

                if "/in/" in current.lower():
                    print(
                        "[LOCATION ERROR] Show Results navigated to a profile."
                    )
                    return False

                current_company_values = query_values(
                    current,
                    "currentCompany"
                )

                if (
                    is_company_people_search(current)
                    and
                    current_company_values ==
                    original_company_values
                    and
                    has_location_filter(current)
                ):
                    final_url = current

                    print(
                        "[LOCATION] Filtered company people-search URL confirmed."
                    )

                    break

            except Exception as ex:
                print(
                    "[LOCATION] URL validation attempt failed:",
                    repr(ex)
                )

            self.page.wait_for_timeout(750)

        # ------------------------------------------------------------
        # 8. FINAL SAFETY VALIDATION
        # ------------------------------------------------------------

        if not final_url:
            final_url = self.page.url

        print("=" * 60)
        print("FINAL LOCATION FILTER VALIDATION")
        print("=" * 60)
        print("Final URL:", final_url)

        if not is_company_people_search(final_url):
            print(
                "[LOCATION ERROR] Final page is not company people-search."
            )
            return False

        if (
            query_values(
                final_url,
                "currentCompany"
            )
            != original_company_values
        ):
            print(
                "[LOCATION ERROR] currentCompany was lost or changed."
            )
            return False

        if "/in/" in final_url.lower():
            print(
                "[LOCATION ERROR] Final page is a profile."
            )
            return False

        if not has_location_filter(final_url):
            print(
                "[LOCATION ERROR] LinkedIn did not apply a location "
                "filter to the URL."
            )
            return False

        print(
            "Location filter applied successfully."
        )

        return True

    def get_profiles(self, company="", location=""):
        """
        Discover primary employee profile links from the authenticated
        LinkedIn company + location people-search results.

        IMPORTANT:

        LinkedIn may expose several /in/ links for a single employee
        result. The primary employee link normally contains the richer
        result-card text, such as:

            Name
            Job title / headline
            Location
            Company
            Connect / Message
            Mutual connections

        Mutual-connection profile links normally contain only the person's
        name.

        Therefore we score the rendered /in/ links and keep the richest
        link for each unique profile URL.

        This intentionally does NOT rely on brittle LinkedIn result-card
        CSS classes.
        """

        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)
        print("Requested company:", company)
        print("Requested location:", location)

        profiles = []

        # ------------------------------------------------------------
        # Locate the bounded LinkedIn employee-search area.
        # ------------------------------------------------------------

        search_area = None

        for selector in (
            "main:visible",
            "div.scaffold-finite-scroll__content:visible",
            "div.search-results-container:visible",
            "div[role='main']:visible",
        ):
            try:
                candidate = self.page.locator(selector).first

                if (
                    candidate.count()
                    and candidate.is_visible()
                ):
                    search_area = candidate

                    print(
                        "Using bounded employee search area:",
                        selector
                    )

                    break

            except Exception as ex:
                print(
                    "Search-area inspection failed:",
                    selector,
                    repr(ex)
                )

        if search_area is None:
            print(
                "ERROR: No bounded LinkedIn employee search area found."
            )
            return profiles

        # ------------------------------------------------------------
        # Canonical profile URL.
        # ------------------------------------------------------------

        def canonical_profile_url(href):
            if not href:
                return ""

            value = str(href).strip()

            if value.startswith("/"):
                value = (
                    "https://www.linkedin.com"
                    + value
                )

            value = (
                value
                .split("?", 1)[0]
                .split("#", 1)[0]
                .rstrip("/")
            )

            if "/in/" not in value.lower():
                return ""

            return value.lower()

        # ------------------------------------------------------------
        # Text normalization.
        # ------------------------------------------------------------

        def normalize_text(value):
            if not value:
                return ""

            value = (
                str(value)
                .replace("\xa0", " ")
                .replace("\n", " ")
                .replace("\r", " ")
            )

            value = re.sub(
                r"\s+",
                " ",
                value
            )

            return value.strip().lower()

        requested_company_normalized = normalize_text(
            company
        )

        requested_location_normalized = normalize_text(
            location
        )

        # ------------------------------------------------------------
        # Location tokens.
        #
        # Example:
        # "New Jersey"
        # -> ["new", "jersey"]
        # ------------------------------------------------------------

        location_tokens = [
            token
            for token in re.findall(
                r"[a-z0-9]+",
                requested_location_normalized
            )
            if len(token) >= 3
        ]

        # ------------------------------------------------------------
        # Company tokens.
        #
        # Example:
        # "SmartWorks, LLC"
        # -> ["smartworks", "llc"]
        #
        # We use the meaningful token(s) as supporting evidence only.
        # ------------------------------------------------------------

        company_tokens = [
            token
            for token in re.findall(
                r"[a-z0-9]+",
                requested_company_normalized
            )
            if len(token) >= 3
        ]

        # ------------------------------------------------------------
        # Collect all visible /in/ links.
        #
        # This preserves the DOM behavior that previously worked.
        # ------------------------------------------------------------

        try:
            links = search_area.locator(
                "a[href*='/in/']:visible"
            )

            total_links = links.count()

        except Exception as ex:
            print(
                "Visible profile-link lookup failed:",
                repr(ex)
            )
            return profiles

        print(
            "Visible /in/ links available:",
            total_links
        )

        # LinkedIn can render a valid zero-result page without any /in/
        # anchors. Give the results page a short opportunity to finish
        # rendering before deciding that the result set is empty.
        if total_links == 0:
            zero_result_detected = False

            for attempt in range(1, 11):
                try:
                    page_text = normalize_text(
                        search_area.inner_text(
                            timeout=1500
                        )
                    )

                    zero_markers = (
                        "no results found",
                        "no results",
                        "no people found",
                        "we couldn't find",
                        "try adjusting your search"
                    )

                    if any(
                        marker in page_text
                        for marker in zero_markers
                    ):
                        zero_result_detected = True
                        print(
                            "LinkedIn zero-result state detected."
                        )
                        break

                    links = search_area.locator(
                        "a[href*='/in/']:visible"
                    )

                    total_links = links.count()

                    if total_links > 0:
                        print(
                            "Profile links appeared after initial wait:",
                            total_links
                        )
                        break

                except Exception as ex:
                    print(
                        f"Zero-result/profile wait {attempt}/10 failed:",
                        repr(ex)
                    )

                self.page.wait_for_timeout(750)

            if total_links == 0:
                # Whether LinkedIn exposed an explicit "no results" message
                # or simply rendered an empty result set, an empty list is
                # the correct data result. Do not throw and do not fabricate
                # profiles.
                if zero_result_detected:
                    print(
                        "Valid zero-profile result: LinkedIn reports no matches."
                    )
                else:
                    print(
                        "Valid zero-profile result: no profile links "
                        "were rendered."
                    )

                return profiles
            # Zero profiles is a valid search result. It must not be
            # treated as an exception or as a reason to remove the
            # requested company/location filters.
            print(
                "No visible LinkedIn profile links found."
            )
            print(
                "Valid zero-profile result: returning an empty profile list."
            )
            return profiles

        # ------------------------------------------------------------
        # best_by_url:
        #
        # One employee can have multiple /in/ anchors.
        #
        # Keep only the richest/highest-confidence representation for
        # that profile URL.
        # ------------------------------------------------------------

        best_by_url = {}

        for index in range(total_links):

            try:
                link = links.nth(index)

                href = canonical_profile_url(
                    link.get_attribute("href")
                )

                if not href:
                    continue

                raw_text = ""

                try:
                    raw_text = (
                        link.inner_text(
                            timeout=2000
                        )
                        .strip()
                    )
                except Exception:
                    pass

                text = normalize_text(
                    raw_text
                )

                if not text:
                    continue

                score = 0
                reasons = []

                # ----------------------------------------------------
                # Strongest signal:
                #
                # The employee result anchor can contain "mutual
                # connections" because the complete employee result is
                # rendered inside that anchor.
                # ----------------------------------------------------

                if "mutual connections" in text:
                    score += 100
                    reasons.append(
                        "contains mutual-connections result text"
                    )

                # ----------------------------------------------------
                # Requested location is a very strong signal.
                #
                # Mutual connections generally do not contain the
                # employee's geographic result location.
                # ----------------------------------------------------

                if (
                    requested_location_normalized
                    and requested_location_normalized in text
                ):
                    score += 80
                    reasons.append(
                        "contains requested location"
                    )

                elif location_tokens:
                    matched_location_tokens = sum(
                        1
                        for token in location_tokens
                        if token in text
                    )

                    if matched_location_tokens:
                        score += (
                            25
                            * matched_location_tokens
                        )

                        reasons.append(
                            "contains location tokens"
                        )

                # ----------------------------------------------------
                # Requested company is another strong signal.
                # ----------------------------------------------------

                if (
                    requested_company_normalized
                    and requested_company_normalized in text
                ):
                    score += 70
                    reasons.append(
                        "contains requested company"
                    )

                else:
                    matched_company_tokens = sum(
                        1
                        for token in company_tokens
                        if token in text
                    )

                    if matched_company_tokens:
                        score += (
                            20
                            * matched_company_tokens
                        )

                        reasons.append(
                            "contains company tokens"
                        )

                # ----------------------------------------------------
                # Employee result action signals.
                # ----------------------------------------------------

                if "connect" in text:
                    score += 15
                    reasons.append(
                        "contains Connect"
                    )

                if "message" in text:
                    score += 15
                    reasons.append(
                        "contains Message"
                    )

                if "follow" in text:
                    score += 10
                    reasons.append(
                        "contains Follow"
                    )

                # ----------------------------------------------------
                # Richer text is useful because mutual-connection
                # anchors are normally just a person's name.
                # ----------------------------------------------------

                text_length = len(
                    text
                )

                if text_length >= 150:
                    score += 35
                    reasons.append(
                        "rich result text"
                    )

                elif text_length >= 100:
                    score += 25
                    reasons.append(
                        "rich result text"
                    )

                elif text_length >= 60:
                    score += 15
                    reasons.append(
                        "extended result text"
                    )

                elif text_length <= 60:
                    score -= 20
                    reasons.append(
                        "short profile-link text"
                    )

                # ----------------------------------------------------
                # Very short name-only links with no location/company
                # evidence are treated as likely nested people.
                # ----------------------------------------------------

                if (
                    text_length <= 60
                    and requested_location_normalized
                    not in text
                    and not (
                        requested_company_normalized
                        and requested_company_normalized in text
                    )
                    and "mutual connections" not in text
                ):
                    score -= 50
                    reasons.append(
                        "likely nested/mutual profile"
                    )

                existing = best_by_url.get(
                    href
                )

                candidate = {
                    "url": href,
                    "text": raw_text.replace(
                        "\n",
                        " "
                    ).strip(),
                    "normalized_text": text,
                    "score": score,
                    "reasons": reasons,
                    "dom_index": index,
                }

                # Keep the strongest representation of the same URL.
                if (
                    existing is None
                    or score > existing["score"]
                ):
                    best_by_url[href] = candidate

                print("-" * 60)
                print(
                    "PROFILE LINK:",
                    index + 1
                )
                print(
                    "URL:",
                    href
                )
                print(
                    "Text:",
                    raw_text.replace(
                        "\n",
                        " "
                    ).strip()[:500]
                )
                print(
                    "Score:",
                    score
                )
                print(
                    "Reasons:",
                    ", ".join(reasons)
                )

            except Exception as ex:
                print(
                    "Profile-link scoring failed:",
                    repr(ex)
                )

        # ------------------------------------------------------------
        # Sort strongest primary employee links first.
        #
        # Preserve DOM order when scores are equal.
        # ------------------------------------------------------------

        ranked = sorted(
            best_by_url.values(),
            key=lambda item: (
                -item["score"],
                item["dom_index"],
            )
        )

        print("=" * 60)
        print(
            "UNIQUE PROFILE URLs AFTER DEDUP:",
            len(ranked)
        )
        print("=" * 60)

        # ------------------------------------------------------------
        # Do not blindly accept extremely weak name-only links.
        #
        # A primary employee result should normally have at least one
        # meaningful result signal:
        #
        #   location
        #   company
        #   mutual-connections result text
        #   Connect/Message/Follow
        #   rich result text
        #
        # Workflow-level profile validation remains authoritative.
        # ------------------------------------------------------------

        reliable = []

        for item in ranked:

            text = item["normalized_text"]

            strong_signal = (
                "mutual connections" in text
                or (
                    requested_location_normalized
                    and requested_location_normalized in text
                )
                or (
                    requested_company_normalized
                    and requested_company_normalized in text
                )
                or "connect" in text
                or "message" in text
                or "follow" in text
                or len(text) >= 100
            )

            if not strong_signal:
                print(
                    "SKIP weak/naked /in/ link:",
                    item["url"],
                    "|",
                    item["text"]
                )
                continue

            reliable.append(
                item
            )

        print(
            "Reliable primary employee candidates:",
            len(reliable)
        )

        # ------------------------------------------------------------
        # Build result records.
        # ------------------------------------------------------------

        for item in reliable:

            profile_url = item["url"]

            profiles.append(
                {
                    "full_name": item["text"],
                    "profile_url": profile_url,
                    "company": company,
                    "location": location,
                }
            )

            print("-" * 60)
            print(
                "PRIMARY EMPLOYEE CANDIDATE:"
            )
            print(
                "Name/Text:",
                item["text"]
            )
            print(
                "URL:",
                profile_url
            )
            print(
                "Score:",
                item["score"]
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
