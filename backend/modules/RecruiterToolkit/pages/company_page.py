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
        # Find the actual location input.
        # ------------------------------------------------------------
        try:
            inputs = self.page.locator(
                "input:visible"
            )

            input_count = inputs.count()

            print(
                "Visible inputs:",
                input_count
            )

            if input_count == 0:
                print(
                    "[LOCATION ERROR] No visible inputs."
                )
                return False

            location_box = inputs.last

            print(
                "Location input placeholder:",
                location_box.get_attribute("placeholder")
            )

            location_box.fill(
                location
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
        # Do NOT use:
        #   [role='listitem']
        #
        # LinkedIn profile result cards are also listitems.
        #
        # We specifically look for text matching the requested
        # location and reject anything contained inside an /in/
        # profile link.
        # ------------------------------------------------------------
        print(
            "Selecting actual location suggestion..."
        )

        normalized_location = " ".join(
            str(location)
            .replace("\xa0", " ")
            .strip()
            .split()
        ).lower()

        selected = False

        # First pass: exact visible text.
        try:
            exact_matches = self.page.get_by_text(
                location,
                exact=True
            )

            exact_count = exact_matches.count()

            print(
                "Exact location-text matches:",
                exact_count
            )

            for i in range(exact_count):
                try:
                    candidate = exact_matches.nth(i)

                    if not candidate.is_visible():
                        continue

                    # Reject candidates that belong to a profile link.
                    profile_link_ancestor = candidate.locator(
                        "xpath=ancestor::a[contains(@href, '/in/')]"
                    )

                    if profile_link_ancestor.count():
                        print(
                            f"Skipping exact match #{i + 1}: "
                            "inside profile link"
                        )
                        continue

                    # Reject profile/search result containers.
                    parent_text = ""

                    try:
                        parent = candidate.locator(
                            "xpath=.."
                        )

                        parent_text = (
                            parent.inner_text(
                                timeout=1000
                            )
                            .strip()
                        )
                    except Exception:
                        pass

                    if (
                        parent_text
                        and normalized_location not in parent_text.lower()
                    ):
                        continue

                    print(
                        "Clicking exact location suggestion:",
                        candidate.inner_text(
                            timeout=2000
                        ).strip()
                    )

                    candidate.click(
                        timeout=10000
                    )

                    selected = True

                    break

                except Exception as ex:
                    print(
                        "Exact location candidate skipped:",
                        repr(ex)
                    )

        except Exception as ex:
            print(
                "Exact location lookup failed:",
                repr(ex)
            )

        # ------------------------------------------------------------
        # Second pass: visible location-like candidates.
        #
        # Look inside common autocomplete elements, but reject
        # anything that belongs to a profile /in/ link.
        # ------------------------------------------------------------
        if not selected:

            print(
                "Exact location suggestion not selected."
            )

            selectors = [
                "li:visible",
                "[role='option']:visible",
                "[role='button']:visible",
                "button:visible",
            ]

            for selector in selectors:

                try:
                    candidates = self.page.locator(
                        selector
                    )

                    count = candidates.count()

                    print(
                        f"{selector} count:",
                        count
                    )

                    for i in range(count):

                        try:
                            candidate = candidates.nth(i)

                            if not candidate.is_visible():
                                continue

                            text_value = (
                                candidate.inner_text(
                                    timeout=1000
                                )
                                .strip()
                            )

                            if not text_value:
                                continue

                            text_normalized = " ".join(
                                text_value
                                .replace("\xa0", " ")
                                .split()
                            ).lower()

                            # Must contain the requested location.
                            if normalized_location not in text_normalized:
                                continue

                            # Never click a profile result.
                            profile_link_ancestor = candidate.locator(
                                "xpath=ancestor::a[contains(@href, '/in/')]"
                            )

                            if profile_link_ancestor.count():
                                continue

                            # Never click a profile-result container.
                            if (
                                "/in/" in text_value.lower()
                                or
                                "message" in text_normalized
                                and "mutual connections" in text_normalized
                            ):
                                continue

                            print(
                                "Candidate location suggestion:",
                                repr(text_value[:300])
                            )

                            candidate.click(
                                timeout=10000
                            )

                            selected = True

                            print(
                                "Location suggestion clicked."
                            )

                            break

                        except Exception:
                            continue

                    if selected:
                        break

                except Exception as ex:
                    print(
                        f"Location selector scan failed for {selector}:",
                        repr(ex)
                    )

        # ------------------------------------------------------------
        # Keyboard fallback.
        #
        # ArrowDown is allowed only as a fallback.
        # NEVER press Enter here because Enter previously navigated
        # away from the company people-search page.
        # ------------------------------------------------------------
        if not selected:

            print(
                "DOM location suggestion not found."
            )

            try:
                # ------------------------------------------------------------
                # KEYBOARD FALLBACK
                #
                # We must select the autocomplete item, not merely highlight it.
                # Keep focus on the actual location input so Enter applies the
                # highlighted LinkedIn location suggestion rather than submitting
                # the surrounding search form.
                # ------------------------------------------------------------
                location_box.click()

                self.page.wait_for_timeout(500)

                location_box.press("ArrowDown")

                self.page.wait_for_timeout(500)

                print(
                    "Location suggestion highlighted using input keyboard fallback."
                )

                location_box.press("Enter")

                self.page.wait_for_timeout(1500)

                # ------------------------------------------------------------
                # VERIFY THAT THE LOCATION WAS ACTUALLY APPLIED
                # ------------------------------------------------------------
                current_url = self.page.url.lower()

                print(
                    "URL after keyboard location selection:",
                    self.page.url
                )

                # Never accept a profile or unrelated LinkedIn page.
                if "/in/" in current_url:
                    print(
                        "[LOCATION ERROR] Keyboard selection opened a profile."
                    )
                    return False

                if "/search/results/people/" not in current_url:
                    print(
                        "[LOCATION ERROR] Keyboard selection left people-search."
                    )
                    return False

                if "currentcompany=" not in current_url:
                    print(
                        "[LOCATION ERROR] currentCompany disappeared after "
                        "keyboard location selection."
                    )
                    return False

                # ------------------------------------------------------------
                # VERIFY THE LOCATION UI STATE.
                #
                # After a successful LinkedIn autocomplete selection, the input
                # is normally cleared/replaced by the selected location chip.
                # Search the visible page for the requested location.
                # ------------------------------------------------------------
                location_applied = False

                try:
                    visible_location = self.page.get_by_text(
                        location,
                        exact=False
                    )

                    visible_count = visible_location.count()

                    for i in range(visible_count):
                        try:
                            candidate = visible_location.nth(i)

                            if not candidate.is_visible():
                                continue

                            text_value = (
                                candidate.inner_text(
                                    timeout=1000
                                )
                                .strip()
                            )

                            normalized_text = " ".join(
                                text_value
                                .replace("\xa0", " ")
                                .split()
                            ).lower()

                            if normalized_location in normalized_text:
                                # Do not accept profile-card text as evidence.
                                profile_ancestor = candidate.locator(
                                    "xpath=ancestor::a[contains(@href, '/in/')]"
                                )

                                if profile_ancestor.count():
                                    continue

                                location_applied = True

                                print(
                                    "Verified applied location UI:",
                                    repr(text_value[:300])
                                )

                                break

                        except Exception:
                            continue

                except Exception as ex:
                    print(
                        "Location UI verification failed:",
                        repr(ex)
                    )

                if not location_applied:
                    print(
                        "[LOCATION ERROR] Keyboard selection did not produce "
                        "verifiable applied location."
                    )
                    return False

                print(
                    "Location suggestion selected and verified."
                )

                selected = True

        # ------------------------------------------------------------
            except Exception as ex:
                print(
                    "[LOCATION ERROR] Keyboard fallback failed:",
                    repr(ex)
                )
                return False

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
        # ------------------------------------------------------------
        print(
            "Looking for Show results..."
        )

        try:
            show_results = self.page.get_by_text(
                "Show results",
                exact=True
            )

            show_count = show_results.count()

            print(
                "Show results exact matches:",
                show_count
            )

            clicked_show_results = False

            for i in range(show_count):

                try:
                    candidate = show_results.nth(i)

                    if not candidate.is_visible():
                        continue

                    candidate.click(
                        timeout=15000
                    )

                    clicked_show_results = True

                    print(
                        f"Clicked Show results #{i + 1}"
                    )

                    break

                except Exception:
                    continue

            if not clicked_show_results:
                print(
                    "[LOCATION ERROR] Could not click Show results."
                )
                return False

        except Exception as ex:
            print(
                "[LOCATION ERROR] Show results failed:",
                repr(ex)
            )
            return False

        self.page.wait_for_timeout(
            4000
        )

        # ------------------------------------------------------------
        # Final validation.
        # ------------------------------------------------------------
        final_url = self.page.url

        print(
            "Final URL after location filter:",
            final_url
        )

        final_url_lower = final_url.lower()

        if "/search/results/people/" not in final_url_lower:
            print(
                "[LOCATION ERROR] Final page is not people-search."
            )
            return False

        if "currentcompany=" not in final_url_lower:
            print(
                "[LOCATION ERROR] Final URL lost currentCompany."
            )
            return False

        if "/in/" in final_url_lower:
            print(
                "[LOCATION ERROR] Final URL is a profile."
            )
            return False

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
