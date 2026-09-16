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
        print("=" * 60)
        print("APPLYING LOCATION FILTER")
        print("=" * 60)

        print(
            "Requested location:",
            location
        )

        before_url = self.page.url

        print(
            "URL before location filter:",
            before_url
        )

        # ------------------------------------------------------------
        # Safety: must already be on company-scoped people search.
        # ------------------------------------------------------------
        before_url_lower = before_url.lower()

        if "/search/results/people/" not in before_url_lower:
            print(
                "[LOCATION ERROR] Not on LinkedIn people-search page."
            )
            return False

        if "currentcompany=" not in before_url_lower:
            print(
                "[LOCATION ERROR] currentCompany filter missing."
            )
            return False

        # ------------------------------------------------------------
        # Open Locations filter.
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

            clicked = False

            for i in range(location_count):
                try:
                    candidate = locations.nth(i)

                    if not candidate.is_visible():
                        continue

                    candidate.click(
                        timeout=15000
                    )

                    clicked = True

                    print(
                        f"Clicked Locations match #{i + 1}"
                    )

                    break

                except Exception:
                    continue

            if not clicked:
                print(
                    "[LOCATION ERROR] Could not click Locations filter."
                )
                return False

        except Exception as ex:
            print(
                "[LOCATION ERROR] Opening Locations failed:",
                repr(ex)
            )
            return False

        self.page.wait_for_timeout(
            1500
        )

        # ------------------------------------------------------------
        # ------------------------------------------------------------
        # Find LinkedIn's actual Location input.
        #
        # IMPORTANT:
        # LinkedIn does NOT consistently expose this UI as role="dialog".
        # Target the exact Add a location input instead.
        # ------------------------------------------------------------
        try:
            location_inputs = self.page.locator(
                "input[placeholder='Add a location']:visible"
            )

            input_count = location_inputs.count()

            print(
                "Visible Add a location inputs:",
                input_count
            )

            if input_count == 0:
                print(
                    "[LOCATION ERROR] No visible "
                    "Add a location input was found."
                )
                return False

            # LinkedIn can retain an older hidden instance.
            # Use the newest visible exact-placeholder input.
            location_box = location_inputs.last

            print(
                "Location input placeholder:",
                location_box.get_attribute("placeholder")
            )

            print(
                "Location input aria-controls:",
                location_box.get_attribute("aria-controls")
            )

            print(
                "Location input aria-owns:",
                location_box.get_attribute("aria-owns")
            )

            location_box.click()
            location_box.fill("")

            # Sequential typing reliably triggers LinkedIn autocomplete.
            location_box.press_sequentially(
                str(location).strip(),
                delay=100
            )

        except Exception as ex:
            print(
                "[LOCATION ERROR] Could not enter location:",
                repr(ex)
            )
            return False

        self.page.wait_for_timeout(
            2500
        )

        print(
            "Entered location:",
            location
        )

        print(
            "URL after entering location:",
            self.page.url
        )

        # ------------------------------------------------------------
        # CRITICAL LOCATION SUGGESTION SELECTION
        #
        # LinkedIn does not reliably expose the autocomplete as a
        # dialog/listbox/option. The previous patch also removed the
        # location_dialog variable while the old code still referenced
        # it, producing:
        # NameError("name 'location_dialog' is not defined")
        #
        # This implementation uses the exact Add a location input as
        # the anchor and walks its DOM ancestors. It never clicks a
        # page-wide "New Jersey" text match.
        # ------------------------------------------------------------

        requested_location = str(
            location
        ).strip()

        expected_location = (
            f"{requested_location}, United States"
        )

        print(
            "Selecting LinkedIn location option:",
            expected_location
        )

        location_selected = False

        def normalize_location_text(value):
            return re.sub(
                r"\s+",
                " ",
                str(value or "")
            ).strip().lower()

        requested_norm = normalize_location_text(
            requested_location
        )

        expected_norm = normalize_location_text(
            expected_location
        )

        def location_text_matches(value):
            normalized = normalize_location_text(value)

            if not normalized:
                return False

            return (
                normalized == expected_norm
                or normalized == requested_norm
                or normalized.startswith(requested_norm + ",")
                or normalized.startswith(requested_norm + " -")
                or normalized.startswith(requested_norm + " |")
            )

        def get_candidate_text(locator):
            for source in ("inner_text", "aria-label", "title"):
                try:
                    value = (
                        locator.inner_text(timeout=700)
                        if source == "inner_text"
                        else locator.get_attribute(source)
                    )

                    if value and location_text_matches(value):
                        return str(value).strip()

                except Exception:
                    pass

            return None

        def click_candidates(container, description):
            nonlocal location_selected

            try:
                count = container.count()
            except Exception:
                return False

            for i in range(count):
                try:
                    candidate = container.nth(i)

                    if not candidate.is_visible():
                        continue

                    matched_text = get_candidate_text(candidate)

                    if not matched_text:
                        continue

                    print(
                        "LOCATION AUTOCOMPLETE CANDIDATE:",
                        description,
                        "=>",
                        repr(matched_text)
                    )

                    try:
                        candidate.scroll_into_view_if_needed(timeout=1000)
                    except Exception:
                        pass

                    try:
                        candidate.click(timeout=5000)
                        location_selected = True
                        print(
                            "Location autocomplete candidate clicked successfully."
                        )
                        return True
                    except Exception as ex:
                        print(
                            "Location candidate click failed:",
                            repr(ex)
                        )

                except Exception:
                    continue

            return False

        self.page.wait_for_timeout(2500)

        # Re-acquire the exact active input.
        try:
            location_inputs = self.page.locator(
                "input[placeholder='Add a location']:visible"
            )

            if location_inputs.count() == 0:
                print(
                    "[LOCATION ERROR] Add a location input disappeared."
                )
                return False

            location_box = location_inputs.last

            print(
                "Autocomplete input confirmed."
            )

            print(
                "Autocomplete input aria-controls:",
                location_box.get_attribute("aria-controls")
            )

            print(
                "Autocomplete input aria-owns:",
                location_box.get_attribute("aria-owns")
            )

        except Exception as ex:
            print(
                "[LOCATION ERROR] Could not reacquire location input:",
                repr(ex)
            )
            return False

        # ------------------------------------------------------------
        # 1. ARIA-controlled popup, when available.
        # ------------------------------------------------------------
        try:
            controlled_ids = []

            for attr in ("aria-controls", "aria-owns"):
                value = location_box.get_attribute(attr)

                if value:
                    controlled_ids.extend(
                        item.strip()
                        for item in value.split()
                        if item.strip()
                    )

            print(
                "Controlled popup IDs:",
                controlled_ids
            )

            for controlled_id in controlled_ids:
                popup = self.page.locator(
                    f"[id='{controlled_id}']:visible"
                )

                if popup.count() == 0:
                    continue

                if click_candidates(
                    popup.locator("*:visible"),
                    f"ARIA popup {controlled_id}"
                ):
                    break

        except Exception as ex:
            print(
                "ARIA popup lookup failed:",
                repr(ex)
            )

        # ------------------------------------------------------------
        # 2. Walk upward from the actual input.
        #
        # This handles LinkedIn's generic DIV/SPAN autocomplete DOM.
        # ------------------------------------------------------------
        if not location_selected:
            try:
                ancestor = location_box

                for level in range(1, 9):
                    ancestor = ancestor.locator("xpath=..")

                    if ancestor.count() == 0:
                        break

                    try:
                        if not ancestor.is_visible():
                            continue
                    except Exception:
                        continue

                    try:
                        ancestor_text = normalize_location_text(
                            ancestor.inner_text(timeout=700)
                        )
                    except Exception:
                        ancestor_text = ""

                    print(
                        f"Location input ancestor #{level} text:",
                        repr(ancestor_text[:600])
                    )

                    # First use normal interactive elements.
                    if click_candidates(
                        ancestor.locator(
                            "li:visible, "
                            "button:visible, "
                            "[role='option']:visible, "
                            "[role='button']:visible, "
                            "a:visible"
                        ),
                        f"input ancestor #{level} interactive"
                    ):
                        break

                    if location_selected:
                        break

                    # Then inspect generic elements only when this
                    # ancestor actually contains the requested location.
                    if requested_norm in ancestor_text:
                        if click_candidates(
                            ancestor.locator(
                                "div:visible, span:visible"
                            ),
                            f"input ancestor #{level} generic"
                        ):
                            break

            except Exception as ex:
                print(
                    "Input-ancestor autocomplete lookup failed:",
                    repr(ex)
                )

        # ------------------------------------------------------------
        # 3. Visible suggestion containers.
        # ------------------------------------------------------------
        if not location_selected:
            try:
                containers = self.page.locator(
                    "ul:visible, "
                    "ol:visible, "
                    "[role='listbox']:visible, "
                    "[role='menu']:visible, "
                    "[class*='suggest']:visible, "
                    "[class*='autocomplete']:visible"
                )

                print(
                    "Visible suggestion containers:",
                    containers.count()
                )

                for i in range(containers.count()):
                    container = containers.nth(i)

                    try:
                        container_text = normalize_location_text(
                            container.inner_text(timeout=700)
                        )
                    except Exception:
                        container_text = ""

                    if requested_norm not in container_text:
                        continue

                    if click_candidates(
                        container.locator("*:visible"),
                        f"suggestion container #{i + 1}"
                    ):
                        break

            except Exception as ex:
                print(
                    "Suggestion-container lookup failed:",
                    repr(ex)
                )

        # ------------------------------------------------------------
        # HARD FAILURE WITH DOM DIAGNOSTICS
        # ------------------------------------------------------------
        if not location_selected:
            print(
                "ERROR: Could not click the LinkedIn "
                "location autocomplete option."
            )

            print(
                "Requested location:",
                requested_location
            )

            print(
                "Expected LinkedIn location:",
                expected_location
            )

            try:
                print("LOCATION INPUT OUTER HTML:")
                print(
                    location_box.evaluate(
                        "(el) => el.outerHTML"
                    )[:5000]
                )

                print("LOCATION INPUT PARENT OUTER HTML:")
                print(
                    location_box.locator(
                        "xpath=.."
                    ).evaluate(
                        "(el) => el.outerHTML"
                    )[:10000]
                )

            except Exception as ex:
                print(
                    "Location DOM diagnostics failed:",
                    repr(ex)
                )

            print(
                "Location filter result: False"
            )

            return False

        # IMPORTANT: Do NOT press Enter after selecting the suggestion.
        print(
            "Location suggestion selected successfully."
        )

        # IMPORTANT:
        # Do NOT press Enter.
        #
        # The previous implementation showed that Enter can cause
        # LinkedIn to leave the authenticated people-search page.
        self.page.wait_for_timeout(
            1000
        )

        # SAFETY CHECK
        #
        # The location click/highlight must never navigate to a
        # profile page or generic LinkedIn page.
        # ------------------------------------------------------------
        after_selection_url = self.page.url

        print(
            "URL after location selection:",
            after_selection_url
        )

        after_selection_lower = after_selection_url.lower()

        if "/in/" in after_selection_lower:
            print(
                "[LOCATION ERROR] Location selection opened a profile."
            )
            return False

        if "/search/results/people/" not in after_selection_lower:
            print(
                "[LOCATION ERROR] Location selection left people-search."
            )
            return False

        if "currentcompany=" not in after_selection_lower:
            print(
                "[LOCATION ERROR] currentCompany disappeared."
            )
            return False

        # ------------------------------------------------------------
        # Click Show results.
        #
        # IMPORTANT:
        # Do NOT use page.get_by_text("Show results").
        #
        # The previous implementation could match text from an
        # unrelated LinkedIn element and navigate away from the
        # authenticated people-search page.
        #
        # We require the actual Show results BUTTON belonging to
        # the active Location filter dialog.
        #
        # There is intentionally NO page-wide fallback.
        # ------------------------------------------------------------

        print("=" * 60)
        print("LOCATING SHOW RESULTS BUTTON")
        print("=" * 60)

        show_results = None
        selected_dialog_index = None

        # ------------------------------------------------------------
        # Locate the visible Location filter dialog.
        # ------------------------------------------------------------
        try:

            dialogs = self.page.locator(
                "[role='dialog']:visible"
            )

            dialog_count = dialogs.count()

            print(
                "Visible dialogs:",
                dialog_count
            )

            # Inspect newest dialog first.
            for i in range(
                dialog_count - 1,
                -1,
                -1
            ):

                try:

                    dialog = dialogs.nth(i)

                    if not dialog.is_visible():
                        continue

                    dialog_text = ""

                    try:

                        dialog_text = (
                            dialog.inner_text(
                                timeout=2000
                            )
                            .strip()
                        )

                    except Exception:
                        pass

                    print(
                        f"Dialog #{i + 1} text:",
                        repr(
                            dialog_text[:500]
                        )
                    )

                    # The Location filter dialog must contain
                    # LinkedIn's location input.
                    has_location_input = (
                        dialog.locator(
                            "input[placeholder='Add a location']"
                        ).count() > 0
                    )

                    print(
                        f"Dialog #{i + 1} "
                        f"has location input:",
                        has_location_input
                    )

                    if not has_location_input:
                        continue

                    # Only look for an actual BUTTON inside this
                    # Location dialog.
                    show_buttons = (
                        dialog.get_by_role(
                            "button",
                            name="Show results",
                            exact=True
                        )
                    )

                    button_count = (
                        show_buttons.count()
                    )

                    print(
                        f"Dialog #{i + 1} "
                        f"Show results buttons:",
                        button_count
                    )

                    for j in range(
                        button_count
                    ):

                        try:

                            candidate = (
                                show_buttons.nth(j)
                            )

                            if not candidate.is_visible():
                                continue

                            if not candidate.is_enabled():

                                print(
                                    f"Show results button "
                                    f"#{j + 1} is disabled."
                                )

                                continue

                            show_results = candidate
                            selected_dialog_index = i

                            print(
                                f"Selected Show results "
                                f"BUTTON #{j + 1} from "
                                f"Location dialog #{i + 1}."
                            )

                            break

                        except Exception as ex:

                            print(
                                f"Button #{j + 1} inspection "
                                f"failed:",
                                repr(ex)
                            )

                    if show_results is not None:
                        break

                except Exception as ex:

                    print(
                        f"Dialog #{i + 1} inspection failed:",
                        repr(ex)
                    )

        except Exception as ex:

            print(
                "Location dialog lookup failed:",
                repr(ex)
            )

        # ------------------------------------------------------------
        # HARD FAILURE
        #
        # DO NOT use a page-wide Show results selector.
        # ------------------------------------------------------------
        if show_results is None:

            print(
                "[LOCATION ERROR] Could not identify the "
                "Show results BUTTON inside the active "
                "Location filter dialog."
            )

            return False

        # ------------------------------------------------------------
        # Button diagnostics.
        # ------------------------------------------------------------
        try:

            print("=" * 60)
            print("SHOW RESULTS BUTTON DIAGNOSTICS")
            print("=" * 60)

            print(
                "Selected dialog index:",
                selected_dialog_index
            )

            print(
                "Tag:",
                show_results.evaluate(
                    "(el) => el.tagName"
                )
            )

            print(
                "Text:",
                repr(
                    show_results.inner_text(
                        timeout=2000
                    )
                )
            )

            print(
                "aria-label:",
                show_results.get_attribute(
                    "aria-label"
                )
            )

            print(
                "type:",
                show_results.get_attribute(
                    "type"
                )
            )

            print(
                "disabled:",
                show_results.get_attribute(
                    "disabled"
                )
            )

        except Exception as ex:

            print(
                "Button diagnostics failed:",
                repr(ex)
            )

        # ------------------------------------------------------------
        # Capture known-good URL before clicking.
        # ------------------------------------------------------------
        before_show_results_url = (
            self.page.url
        )

        print(
            "URL before Show results:",
            before_show_results_url
        )

        before_lower = (
            before_show_results_url.lower()
        )

        if (
            "/search/results/people/"
            not in before_lower
        ):

            print(
                "[LOCATION ERROR] Before clicking "
                "Show results, page is no longer "
                "people-search."
            )

            return False

        if (
            "currentcompany="
            not in before_lower
        ):

            print(
                "[LOCATION ERROR] Before clicking "
                "Show results, currentCompany is missing."
            )

            return False

        # ------------------------------------------------------------
        # CLICK THE REAL BUTTON.
        # ------------------------------------------------------------
        print("=" * 60)
        print("CLICKING SHOW RESULTS BUTTON")
        print("=" * 60)

        try:

            show_results.scroll_into_view_if_needed()

            show_results.click(
                timeout=15000
            )

            print(
                "Show results BUTTON clicked successfully."
            )

        except Exception as ex:

            print(
                "[LOCATION ERROR] Show results button "
                "click failed:",
                repr(ex)
            )

            return False

        # ------------------------------------------------------------
        # Wait for LinkedIn navigation.
        # ------------------------------------------------------------
        final_url = None

        for attempt in range(12):

            self.page.wait_for_timeout(
                1000
            )

            current_url = (
                self.page.url
            )

            print(
                f"Post-Show-results URL check "
                f"{attempt + 1}/12:",
                current_url
            )

            current_lower = (
                current_url.lower()
            )

            # Never accept LinkedIn root.
            if (
                current_lower.rstrip("/")
                == "https://www.linkedin.com"
            ):

                print(
                    "[LOCATION ERROR] Show results "
                    "navigated to LinkedIn root."
                )

                return False

            # Never accept profile navigation.
            if "/in/" in current_lower:

                print(
                    "[LOCATION ERROR] Show results "
                    "navigated to a profile."
                )

                return False

            # Require the company people-search page.
            if (
                "/search/results/people/"
                in current_lower
                and "currentcompany="
                in current_lower
            ):

                final_url = current_url
                break

        if not final_url:
            final_url = self.page.url

        # ------------------------------------------------------------
        # FINAL VALIDATION
        # ------------------------------------------------------------
        print("=" * 60)
        print("FINAL LOCATION FILTER VALIDATION")
        print("=" * 60)

        print(
            "Final URL:",
            final_url
        )

        final_lower = (
            final_url.lower()
        )

        # Must remain on people-search.
        if (
            "/search/results/people/"
            not in final_lower
        ):

            print(
                "[LOCATION ERROR] Final page is not "
                "people-search."
            )

            return False

        # Company filter must survive.
        if (
            "currentcompany="
            not in final_lower
        ):

            print(
                "[LOCATION ERROR] Final URL lost "
                "currentCompany."
            )

            return False

        # Never accept a profile.
        if "/in/" in final_lower:

            print(
                "[LOCATION ERROR] Final URL is a "
                "profile page."
            )

            return False

        print(
            "Location filter navigation validated successfully."
        )

        # Wait for the employee result list.
        try:
            self.page.locator(
                "a[href*='/in/']:visible"
            ).first.wait_for(
                state="visible",
                timeout=30000
            )
        except Exception:
            self.page.wait_for_timeout(
                5000
            )

        profile_count = self.page.locator(
            "a[href*='/in/']:visible"
        ).count()

        print(
            "Visible profile links after location filter:",
            profile_count
        )

        print(
            "Location applied successfully."
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

        if total_links == 0:
            print(
                "ERROR: No visible LinkedIn profile links found."
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
