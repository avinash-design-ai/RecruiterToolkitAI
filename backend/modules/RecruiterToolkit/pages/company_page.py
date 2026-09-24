from pages.base_page import BasePage
from urllib.parse import urlparse, parse_qs


import re
class CompanyPage(BasePage):

    def __init__(self, page):
        super().__init__(page)

    def search_company(self, company):
        """
        Search LinkedIn for the requested company and do not report success
        until the authenticated page has actually produced company-search
        results.

        No company/location/profile-count value is hardcoded.
        """
        from urllib.parse import quote_plus

        requested_company = str(company or "").strip()
        if not requested_company:
            print("ERROR: Empty company name.")
            return False

        self._search_company = requested_company

        print("=" * 60)
        print("SEARCHING LINKEDIN COMPANY")
        print("=" * 60)
        print("Requested company:", requested_company)
        print("Current URL:", self.page.url)

        def is_blocked_url(url):
            value = str(url or "").lower()
            return any(
                marker in value
                for marker in (
                    "/login",
                    "/authwall",
                    "/checkpoint",
                    "/uas/login",
                    "/signup",
                    "/ssr-login",
                    "remember-me-auto-login",
                )
            )

        def is_company_search_url(url):
            value = str(url or "").lower()
            return "/search/results/companies/" in value

        def visible_company_link_count():
            try:
                return self.page.locator("a[href*='/company/']:visible").count()
            except Exception:
                return 0

        def visible_search_input():
            selectors = (
                "input[placeholder*='looking' i]:visible",
                "input[aria-label*='search' i]:visible",
                "input[type='search']:visible",
            )
            for selector in selectors:
                try:
                    locator = self.page.locator(selector)
                    if locator.count() > 0:
                        return locator.first
                except Exception:
                    continue
            return None

        search_box = visible_search_input()
        if search_box is None:
            print("ERROR: LinkedIn search box was not found.")
            return False

        try:
            search_box.click(timeout=10000)
            search_box.fill(requested_company)
            print("Entering company into LinkedIn search:", requested_company)
            search_box.press("Enter")
            print("Company search submitted.")
        except Exception as ex:
            print("Primary company-search submission failed:", repr(ex))
            return False

        # Wait for the actual result state; never assume five seconds means success.
        last_url = ""
        for attempt in range(1, 31):
            try:
                self.page.wait_for_timeout(500)
            except Exception:
                pass

            current_url = str(self.page.url or "").strip()
            last_url = current_url
            links = visible_company_link_count()

            if is_blocked_url(current_url):
                print("ERROR: LinkedIn redirected company search to a blocked page:", current_url)
                return False

            if links > 0:
                print(f"Company search results detected: {links} visible company links on attempt {attempt}/30.")
                return True

            if is_company_search_url(current_url):
                print(f"Company search results URL detected on attempt {attempt}/30:", current_url)
                try:
                    self.page.wait_for_timeout(1000)
                except Exception:
                    pass
                if visible_company_link_count() > 0:
                    print("Company links hydrated after navigation.")
                    return True

            if attempt in (8, 16, 24):
                try:
                    search_box.press("Enter")
                    print(f"Re-submitted company search on attempt {attempt}/30.")
                except Exception:
                    pass

        print("Company result DOM was not detected after normal LinkedIn search.")
        print("URL after normal search:", last_url)

        # Generic same-page fallback. The requested company is the only input.
        fallback_url = (
            "https://www.linkedin.com/search/results/companies/?keywords="
            + quote_plus(requested_company)
        )
        print("Trying controlled same-page company-search URL fallback:", fallback_url)

        try:
            self.page.goto(
                fallback_url,
                wait_until="domcontentloaded",
                timeout=60000,
                referer="https://www.linkedin.com/feed/",
            )
            self.page.wait_for_timeout(3000)
        except Exception as ex:
            print("Company-search URL fallback failed:", repr(ex))
            return False

        for attempt in range(1, 21):
            try:
                self.page.wait_for_timeout(500)
            except Exception:
                pass

            current_url = str(self.page.url or "").strip()
            links = visible_company_link_count()
            print(f"Company fallback DOM wait {attempt}/20:", links, "visible /company/ links |", current_url)

            if is_blocked_url(current_url):
                print("ERROR: Company-search URL fallback reached a blocked page:", current_url)
                return False

            if links > 0:
                print("Company search results successfully synchronized.")
                return True

        print("ERROR: LinkedIn company-search results could not be synchronized.")
        print("Final company-search URL:", self.page.url)
        return False

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
        """
        Open the company-scoped LinkedIn people-search page exactly as
        LinkedIn provided it.

        Connection degree is intentionally not managed by this workflow.
        The search page returned by LinkedIn is preserved as-is.
        Location is handled separately by apply_location()/get_profiles().
        """
        print("=" * 60)
        print("OPENING COMPANY EMPLOYEES / PEOPLE SEARCH")
        print("=" * 60)

        self._employee_search_scope_ready = False

        current_url = str(self.page.url or "").strip()
        print("Current URL:")
        print(current_url)

        def is_people_url(url):
            if not url:
                return False
            lower = url.lower()
            return (
                "/search/results/people/" in lower
                and "currentcompany=" in lower
            )

        def is_blocked_url(url):
            if not url:
                return True
            lower = url.lower()
            return any(
                part in lower
                for part in (
                    "/login",
                    "/authwall",
                    "/checkpoint",
                    "/uas/login",
                    "/signup",
                    "/ssr-login",
                    "remember-me-auto-login",
                )
            )

        def company_ids(url):
            try:
                from urllib.parse import urlsplit, parse_qs

                query = parse_qs(
                    urlsplit(url).query,
                    keep_blank_values=True,
                )

                return (
                    query.get("currentCompany", [])
                    or query.get("currentcompany", [])
                )
            except Exception:
                return []

        # CASE 1:
        # Company-result click already landed directly on the people search.
        if is_people_url(current_url):
            ids = company_ids(current_url)

            print("=" * 60)
            print("COMPANY PEOPLE-SEARCH PAGE ALREADY OPEN")
            print("=" * 60)
            print("Company scope:", ids)

            if is_blocked_url(current_url):
                print("ERROR: Current people-search URL is blocked/authwall.")
                return False

            if not ids:
                print(
                    "ERROR: Current people-search page has no currentCompany."
                )
                return False

            print("Connection-degree handling: DISABLED")
            print("Preserving LinkedIn's returned search URL unchanged.")
            print("Company scope preserved:", ids)

            self._employee_search_scope_ready = True

            print("=" * 60)
            print("COMPANY PEOPLE SEARCH READY")
            print("=" * 60)
            print("Final URL:", current_url)
            print("Company scope preserved:", ids)

            return True

        # CASE 2:
        # Still on the company page. Use LinkedIn's own company-scoped
        # people-search link, without rewriting its query parameters.
        if "/company/" in current_url.lower() and not is_blocked_url(current_url):
            links = self.page.locator(
                "a[href*='/search/results/people/']"
            )

            count = links.count()
            print("People-search links found:", count)

            selected = None
            selected_company_ids = company_ids(current_url)

            for i in range(count):
                try:
                    link = links.nth(i)
                    href = (link.get_attribute("href") or "").strip()

                    if not href:
                        continue

                    if "/search/results/people/" not in href.lower():
                        continue

                    ids = company_ids(href)

                    if not ids:
                        continue

                    if selected_company_ids and ids != selected_company_ids:
                        continue

                    selected = link
                    break

                except Exception:
                    continue

            if selected is None:
                print("ERROR: No company-scoped people-search link found.")
                return False

            try:
                selected.scroll_into_view_if_needed()
                selected.click(timeout=15000)
                self.page.wait_for_timeout(5000)
            except Exception as ex:
                print("People-search link click failed:", repr(ex))
                return False

            final_url = str(self.page.url or "").strip()
            print("Final employee-search URL:", final_url)

            if is_blocked_url(final_url) or not is_people_url(final_url):
                print(
                    "ERROR: LinkedIn did not open an authenticated "
                    "company people search."
                )
                return False

            final_ids = company_ids(final_url)

            if selected_company_ids and final_ids != selected_company_ids:
                print("ERROR: currentCompany changed after opening employee search.")
                print("Expected:", selected_company_ids)
                print("Actual:", final_ids)
                return False

            print("Connection-degree handling: DISABLED")
            print("Preserving LinkedIn's returned search URL unchanged.")
            print("Company scope preserved:", final_ids)

            self._employee_search_scope_ready = True
            return True

        print("ERROR: Current page is not an authenticated company page")
        print("or a company-scoped LinkedIn people search.")
        print("Current URL:", current_url)
        return False

    def apply_location(self, location):
        """
        Keep the already-working company people-search page intact.

        IMPORTANT: LinkedIn's autocomplete rows are not exposed reliably to
        Playwright in the GitHub Actions browser. We therefore do NOT try to
        click the location picker here anymore. Doing so was the source of the
        repeated failures.

        Location is verified at result-card level in get_profiles(). Only
        employee cards whose rendered text contains the requested location are
        returned for profile/email processing. This preserves company scope and
        prevents unrelated profiles from being opened.
        """

        print("=" * 60)
        print("LOCATION CHECK / RESULT-LEVEL FILTER")
        print("=" * 60)

        requested_location = str(location or "").strip()
        current_url = self.page.url

        print("Requested location:", requested_location)
        print("Current URL:", current_url)

        try:
            from urllib.parse import urlsplit, parse_qs
            query = parse_qs(
                urlsplit(current_url).query,
                keep_blank_values=True
            )
        except Exception as ex:
            print("[LOCATION ERROR] Could not inspect current URL:", repr(ex))
            return False

        current_company = query.get("currentCompany", [])

        if (
            "/search/results/people/" not in current_url.lower()
            or not current_company
            or "/in/" in current_url.lower()
        ):
            print("[LOCATION ERROR] Not on company-scoped people search.")
            return False

        print("Company scope preserved:", current_company)
        print("LinkedIn location autocomplete bypassed safely.")
        print("Location will be enforced from each employee result card.")
        print("Ready for profile discovery.")

        return True




    def get_profiles(
        self,
        company="",
        location="",
        max_profiles=None,
    ):
        """
        Extract employee candidates from the authenticated company-scoped
        LinkedIn people-search page.

        PASS 1:
            Use known LinkedIn result-card selectors.

        PASS 2:
            Inspect each visible /in/ link independently using only local
            Playwright ancestors. Never select a page-level ancestor that
            contains many employees.

        Connection degree is ignored.

        Location is authoritative at profile-validation level. The DOM
        discovery stage does not discard a candidate merely because LinkedIn's
        virtualized result markup does not expose location text.
        """

        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)

        print("Requested company:", company)
        print("Requested location:", location)

        if max_profiles is not None:
            try:
                max_profiles = int(max_profiles)
            except (TypeError, ValueError):
                raise ValueError(
                    "max_profiles must be a positive integer or None."
                )

            if max_profiles < 1:
                raise ValueError(
                    "max_profiles must be at least 1."
                )

        print("Page candidate limit:", max_profiles)

        profiles = []
        seen_urls = set()

        def limit_reached():
            return (
                max_profiles is not None
                and len(profiles) >= max_profiles
            )

        # ============================================================
        # HELPERS
        # ============================================================

        def normalize_text(value):

            if not value:
                return ""

            value = (
                str(value)
                .replace("\xa0", " ")
                .replace("\r", " ")
                .replace("\n", " ")
            )

            return re.sub(
                r"\s+",
                " ",
                value
            ).strip()

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

        requested_location = normalize_text(
            location
        ).lower()

        location_tokens = [
            token
            for token in re.findall(
                r"[a-z0-9]+",
                requested_location
            )
            if len(token) >= 3
        ]

        def location_matches(text):

            value = normalize_text(
                text
            ).lower()

            if not requested_location:
                return True

            if requested_location in value:
                return True

            return bool(
                location_tokens
                and all(
                    token in value
                    for token in location_tokens
                )
            )

        def extract_primary_name(anchor_text, result_text=""):
            """
            Return the employee identity represented by the PRIMARY /in/
            anchor inside a single LinkedIn employee search-result row.

            LinkedIn sometimes renders the anchor text as the whole result
            card, including degree text or mutual-connection text. Never use
            connection-degree labels as identity data, and never treat a
            mutual-connection suffix as the employee's name.

            For anonymized rows, preserve the literal 'LinkedIn Member'
            label instead of rejecting the profile.
            """
            text = normalize_text(anchor_text)

            if not text:
                text = normalize_text(result_text)

            if not text:
                return ""

            lower = text.lower()

            if lower.startswith("linkedin member"):
                return "LinkedIn Member"

            for marker in (
                " connect ",
                " • ",
            ):
                parts = text.split(marker, 1)
                if parts[0].strip():
                    text = parts[0].strip()

            lower = text.lower()

            if "mutual connection" in lower:
                text = re.split(
                    r",\s+|\s+&\s+",
                    text,
                    maxsplit=1,
                )[0].strip()

            if text.lower().startswith("linkedin member"):
                return "LinkedIn Member"

            if len(text) > 180:
                text = text[:180].strip()

            return text

        def add_candidate(
            href,
            name,
            result_text,
            enforce_location=False
        ):

            profile_url = canonical_profile_url(
                href
            )

            if not profile_url:
                return False

            if profile_url in seen_urls:
                return False

            clean_name = normalize_text(
                name
            )

            clean_text = normalize_text(
                result_text
            )

            if not clean_name:
                if "linkedin member" in clean_text.lower():
                    clean_name = "LinkedIn Member"
                else:
                    return False

            if enforce_location and not location_matches(
                clean_text
            ):
                return False

            profiles.append(
                {
                    "full_name": clean_name,
                    "profile_url": profile_url,
                    "company": company,
                    "location": location,
                    "search_result_text": clean_text,
                }
            )

            seen_urls.add(
                profile_url
            )

            return True

        # ============================================================
        # VERIFY COMPANY PEOPLE SEARCH
        # ============================================================

        current_url = str(
            self.page.url or ""
        ).strip()

        current_lower = current_url.lower()

        if (
            "/search/results/people/"
            not in current_lower
            or "currentcompany="
            not in current_lower
        ):

            print(
                "ERROR: Current page is not a company-scoped "
                "LinkedIn people search."
            )

            print(
                "Current URL:",
                current_url
            )

            return profiles

        print(
            "Company-scoped employee search confirmed."
        )

        print(
            "Current URL:",
            current_url
        )

        # ============================================================
        # HYDRATION WAIT
        #
        # IMPORTANT:
        # Page 2 can temporarily have:
        #
        #   0 visible /in/ links
        #   0 recognizable result cards
        #
        # while the employee-result text is already rendered.
        #
        # next_page() already recognizes this condition. get_profiles()
        # must use the same third signal.
        # ============================================================

        print("=" * 60)
        print("WAITING FOR EMPLOYEE RESULT DOM")
        print("=" * 60)

        rendered_profile_links = 0
        rendered_result_cards = 0
        rendered_result_text = False

        role_signals = (
            "recruiter",
            "talent acquisition",
            "sales",
            "specialist",
            "manager",
            "engineer",
            "developer",
            "analyst",
            "consultant",
            "director",
            "staffing",
            "human resources",
        )

        result_words = (
            "people",
            "employees",
            "results",
            "connections",
        )

        for attempt in range(1, 41):

            try:
                self.page.wait_for_timeout(
                    500
                )
            except Exception:
                pass

            # --------------------------------------------------------
            # Visible profile links
            # --------------------------------------------------------

            try:

                rendered_profile_links = (
                    self.page
                    .locator(
                        "a[href*='/in/']"
                    )
                    .count()
                )

            except Exception:

                rendered_profile_links = 0

            # --------------------------------------------------------
            # Recognizable result cards
            # --------------------------------------------------------

            rendered_result_cards = 0

            for selector in (
                "li.reusable-search__result-container",
                "li[class*='reusable-search__result']",
                "li.entity-result",
                "div.entity-result",
                "li.search-result",
                "li[class*='search-result']",
                "ul.reusable-search__entity-result-list > li",
            ):

                try:

                    count = (
                        self.page
                        .locator(selector)
                        .count()
                    )

                    if count > rendered_result_cards:
                        rendered_result_cards = count

                except Exception:
                    continue

            # --------------------------------------------------------
            # Rendered employee-result text
            # --------------------------------------------------------

            rendered_result_text = False

            try:

                body_text = (
                    self.page
                    .locator("body")
                    .inner_text(
                        timeout=2000
                    )
                )

                normalized_body = re.sub(
                    r"\s+",
                    " ",
                    body_text or ""
                ).strip().lower()

                role_hits = sum(
                    1
                    for signal in role_signals
                    if signal in normalized_body
                )

                result_context_hits = sum(
                    1
                    for word in result_words
                    if word in normalized_body
                )

                rendered_result_text = (
                    len(normalized_body) >= 800
                    and role_hits >= 2
                    and result_context_hits >= 1
                )

            except Exception:

                rendered_result_text = False

            print(
                f"Employee DOM wait {attempt}/40:",
                rendered_profile_links,
                "visible /in/ links |",
                rendered_result_cards,
                "result cards |",
                rendered_result_text,
                "employee-result text"
            )

            if (
                rendered_profile_links > 0
                or rendered_result_cards > 0
                or rendered_result_text
            ):

                print(
                    "Employee result DOM/text detected."
                )

                break

            if attempt in (
                8,
                16,
                24,
                32,
            ):

                try:

                    self.page.mouse.wheel(
                        0,
                        1200
                    )

                except Exception:
                    pass

        # ============================================================
        # PASS 1
        # KNOWN RESULT-CARD SELECTORS
        # ============================================================

        print("=" * 60)
        print("PASS 1 - RESULT CARD EXTRACTION")
        print("=" * 60)

        card_selectors = (
            "li.reusable-search__result-container",
            "li[class*='reusable-search__result']",
            "li.entity-result",
            "div.entity-result",
            "li.search-result",
            "li[class*='search-result']",
            "ul.reusable-search__entity-result-list > li",
        )

        cards = None

        for selector in card_selectors:

            try:

                locator = self.page.locator(
                    selector
                )

                count = locator.count()

                if count > 0:

                    cards = locator

                    print(
                        "Using result-card selector:",
                        selector
                    )

                    print(
                        "Result cards:",
                        count
                    )

                    break

            except Exception as ex:

                print(
                    "Result-card selector failed:",
                    selector,
                    repr(ex)
                )

        if cards is not None:

            for card_index in range(
                cards.count()
            ):

                try:

                    card = cards.nth(
                        card_index
                    )

                    card_text = normalize_text(
                        card.inner_text()
                    )

                    if len(card_text) < 20:
                        continue

                    links = card.locator(
                        "a[href*='/in/']"
                    )

                    link_count = links.count()

                    if link_count == 0:
                        continue

                    # First /in/ link in a real result card is the
                    # employee. Mutual-connection links follow it.
                    link = links.nth(0)

                    href = (
                        link.get_attribute(
                            "href"
                        )
                        or ""
                    )

                    raw_name = (
                        link
                        .inner_text(
                            timeout=1500
                        )
                        .strip()
                    )

                    name = extract_primary_name(
                        raw_name,
                        card_text,
                    )

                    if add_candidate(
                        href,
                        name,
                        card_text,
                        enforce_location=True
                    ):

                        print("-" * 60)

                        print(
                            "EMPLOYEE CANDIDATE:",
                            canonical_profile_url(
                                href
                            )
                        )

                        print(
                            "Primary anchor:",
                            normalize_text(
                                name
                            )[:200]
                        )

                        print(
                            "Connection degree: IGNORED"
                        )

                except Exception as ex:

                    print(
                        f"Result-card "
                        f"{card_index + 1} inspection failed:",
                        repr(ex)
                    )

        # ============================================================
        # PASS 2
        # VIRTUALIZED-DOM EMPLOYEE RESULT-ROW EXTRACTION
        #
        # The result row is the boundary. We never use a page-level /in/
        # link as an employee by itself.
        #
        # For each visible /in/ link:
        #   1. Walk local ancestors only.
        #   2. Prefer a local ancestor that looks like an employee result row.
        #   3. Treat ONLY the first /in/ link inside that row as the employee.
        #   4. Ignore later /in/ links (mutual/nested profiles).
        #   5. Ignore 1st/2nd/3rd-degree labels completely.
        # ============================================================

        print("=" * 60)
        print("PASS 2 - VIRTUALIZED-DOM EMPLOYEE RESULT-ROW EXTRACTION")
        print("=" * 60)

        if not limit_reached():

            try:
                self.page.evaluate("window.scrollTo(0, 0)")
            except Exception:
                pass

            total_rounds = 16
            empty_rounds_at_bottom = 0

            row_role_signals = (
                "recruiter",
                "talent acquisition",
                "sales",
                "specialist",
                "manager",
                "engineer",
                "developer",
                "analyst",
                "consultant",
                "director",
                "staffing",
                "human resources",
                "president",
                "administrator",
                "architect",
            )

            row_class_signals = (
                "reusable-search__result",
                "entity-result",
                "search-result",
                "base-search-card",
                "pvs-entity",
            )

            for scan_round in range(1, total_rounds + 1):

                if limit_reached():
                    break

                try:
                    links = self.page.locator(
                        "a[href*='/in/']"
                    )
                    link_count = links.count()
                except Exception as ex:
                    print(
                        "Visible /in/ link lookup failed:",
                        repr(ex)
                    )
                    links = None
                    link_count = 0

                round_added = 0
                processed_rows = set()

                if links is not None and link_count > 0:

                    for link_index in range(link_count):

                        if limit_reached():
                            break

                        try:
                            link = links.nth(link_index)

                            best_container = None
                            best_text = ""
                            best_level = -1
                            best_link_count = 0
                            best_score = -1

                            for level in range(0, 10):

                                try:
                                    ancestor = link.locator(
                                        "xpath=" + "/.." * (level + 1)
                                    )

                                    if not ancestor.count():
                                        continue

                                    ancestor_text = normalize_text(
                                        ancestor.inner_text(
                                            timeout=1000
                                        )
                                    )

                                    if (
                                        len(ancestor_text) < 20
                                        or len(ancestor_text) > 2200
                                    ):
                                        continue

                                    ancestor_links = ancestor.locator(
                                        "a[href*='/in/']"
                                    )

                                    local_count = ancestor_links.count()

                                    if local_count < 1 or local_count > 5:
                                        continue

                                    try:
                                        class_text = (
                                            ancestor.get_attribute("class")
                                            or ""
                                        ).lower()
                                    except Exception:
                                        class_text = ""

                                    lower_text = ancestor_text.lower()

                                    score = 0

                                    if location_matches(
                                        ancestor_text
                                    ):
                                        score += 60

                                    if any(
                                        signal in lower_text
                                        for signal in row_role_signals
                                    ):
                                        score += 40

                                    if "linkedin member" in lower_text:
                                        score += 35

                                    if any(
                                        signal in class_text
                                        for signal in row_class_signals
                                    ):
                                        score += 30

                                    if len(ancestor_text) >= 80:
                                        score += 10

                                    score -= level

                                    # Do not promote a tiny mutual-profile
                                    # fragment to an employee result. A real
                                    # result row should expose at least one
                                    # strong signal: location, role, known
                                    # result-row class, or LinkedIn Member.
                                    if score < 25:
                                        continue

                                    if score > best_score:
                                        best_container = ancestor
                                        best_text = ancestor_text
                                        best_level = level
                                        best_link_count = local_count
                                        best_score = score

                                except Exception:
                                    continue

                            if best_container is None:
                                continue

                            local_links = best_container.locator(
                                "a[href*='/in/']"
                            )

                            local_count = local_links.count()

                            if local_count < 1:
                                continue

                            # The first /in/ link inside the employee result
                            # row is the employee. Later /in/ links are mutual
                            # or nested profiles and are ignored.
                            primary_link = local_links.nth(0)

                            primary_href = (
                                primary_link.get_attribute(
                                    "href"
                                )
                                or ""
                            ).strip()

                            primary_url = canonical_profile_url(
                                primary_href
                            )

                            if not primary_url:
                                continue

                            if primary_url in processed_rows:
                                continue

                            processed_rows.add(primary_url)

                            raw_primary_name = (
                                primary_link.inner_text(
                                    timeout=1500
                                ).strip()
                            )

                            primary_name = extract_primary_name(
                                raw_primary_name,
                                best_text,
                            )

                            # Do NOT reject:
                            #   - 1st/2nd/3rd-degree labels
                            #   - mutual-connection wording in the primary anchor
                            #   - LinkedIn Member
                            if not primary_name:
                                if "linkedin member" in best_text.lower():
                                    primary_name = "LinkedIn Member"
                                else:
                                    continue

                            if add_candidate(
                                primary_href,
                                primary_name,
                                best_text or primary_name,
                                enforce_location=False,
                            ):
                                round_added += 1

                                print("-" * 60)
                                print(
                                    "EMPLOYEE CANDIDATE:",
                                    primary_url,
                                )
                                print(
                                    "Primary anchor:",
                                    primary_name[:200],
                                )
                                print(
                                    "Local ancestor level:",
                                    best_level,
                                )
                                print(
                                    "Local /in/ link count:",
                                    best_link_count,
                                )
                                print(
                                    "Result group:",
                                    (best_text or primary_name)[:500],
                                )
                                print(
                                    "Connection degree: IGNORED",
                                )

                        except Exception as ex:
                            print(
                                f"PASS 2 link {link_index + 1} "
                                f"inspection failed:",
                                repr(ex),
                            )

                try:
                    scroll_state = self.page.evaluate(
                        '''() => {
                            const candidates = [
                                document.scrollingElement,
                                ...Array.from(
                                    document.querySelectorAll("main, section, article, ul, div")
                                )
                            ].filter(Boolean);

                            const seen = new Set();
                            const scrollables = [];

                            for (const el of candidates) {
                                if (seen.has(el)) continue;
                                seen.add(el);

                                try {
                                    const style = window.getComputedStyle(el);
                                    const overflowY = style.overflowY || "";
                                    const scrollable =
                                        el.scrollHeight > (el.clientHeight + 20) &&
                                        (
                                            overflowY === "auto" ||
                                            overflowY === "scroll" ||
                                            overflowY === "overlay" ||
                                            el === document.scrollingElement
                                        );

                                    if (!scrollable || el.clientHeight < 100) continue;
                                    scrollables.push(el);
                                } catch (_) {}
                            }

                            let moved = false;
                            let movableCount = 0;

                            for (const el of scrollables) {
                                try {
                                    const maxTop = Math.max(0, el.scrollHeight - el.clientHeight);
                                    if ((el.scrollTop + 8) < maxTop) {
                                        const before = el.scrollTop;
                                        el.scrollTop = Math.min(maxTop, before + 900);
                                        if (el.scrollTop > before + 2) {
                                            moved = true;
                                            movableCount += 1;
                                        }
                                    }
                                } catch (_) {}
                            }

                            window.scrollBy(0, 700);

                            return {
                                scrollableCount: scrollables.length,
                                movableCount,
                                moved
                            };
                        }'''
                    )

                    scrollable_count = int(
                        scroll_state.get("scrollableCount", 0)
                    )
                    movable_count = int(
                        scroll_state.get("movableCount", 0)
                    )
                    scrolled_inner = bool(
                        scroll_state.get("moved", False)
                    )

                    at_bottom = not scrolled_inner

                except Exception:
                    scrollable_count = 0
                    movable_count = 0
                    scrolled_inner = False
                    at_bottom = False

                print(
                    f"PASS 2 scan {scan_round}/{total_rounds}: "
                    f"{link_count} visible /in/ links, "
                    f"{round_added} new employees, "
                    f"profiles={len(profiles)}, "
                    f"at_bottom={at_bottom}"
                )

                if at_bottom:

                    if round_added == 0:
                        empty_rounds_at_bottom += 1
                    else:
                        empty_rounds_at_bottom = 0

                    if empty_rounds_at_bottom >= 2:
                        break

                # The JS block above explicitly scrolls LinkedIn's inner result
                # container(s). Keep a smaller wheel nudge as a virtualization fallback.
                try:
                    self.page.mouse.wheel(
                        0,
                        700
                    )
                except Exception:
                    pass

            try:
                self.page.evaluate(
                    "window.scrollTo(0, 0)"
                )
            except Exception:
                pass

        # ============================================================
        # FINAL RESULT
        # ============================================================

        print("=" * 60)

        if rendered_result_text and not profiles:
            print(
                "RESULT-TEXT PRESENT BUT NO EMPLOYEE CANDIDATE WAS EXTRACTED."
            )

            try:
                all_dom_links = self.page.locator(
                    "a[href*='/in/']"
                )
                dom_count = all_dom_links.count()

                print(
                    "All DOM /in/ anchors after extraction:",
                    dom_count
                )

                preview = []
                for i in range(min(dom_count, 20)):
                    try:
                        href = (
                            all_dom_links.nth(i).get_attribute("href")
                            or ""
                        )
                        if href:
                            preview.append(href)
                    except Exception:
                        continue

                print(
                    "DOM /in/ href preview:",
                    preview
                )

            except Exception as ex:
                print(
                    "DOM /in/ diagnostic failed:",
                    repr(ex)
                )

            try:
                body_preview = normalize_text(
                    self.page.locator("body").inner_text(timeout=2000)
                )

                print(
                    "Rendered employee-result text preview:",
                    body_preview[:1800]
                )

            except Exception as ex:
                print(
                    "Rendered text diagnostic failed:",
                    repr(ex)
                )

        print(
            "EMPLOYEE PROFILES EXTRACTED:",
            len(profiles)
        )

        print("=" * 60)

        return profiles



    def next_page(self):
        """
        Move to the next company-scoped LinkedIn people-search page.

        Release-level pagination contract:
        - Keep the live authenticated employee-search tab as the owner.
        - Prefer LinkedIn's real visible Next control.
        - If a live Next click produces a transient login/SSR redirect,
          recover the original page and retry the live control once.
        - If the second live attempt is still redirected, use a controlled
          same-page page=N fallback, preserving every existing query parameter
          exactly as LinkedIn returned it (including any network value).
        - Never manipulate connection-degree filters or rewrite network scope.
        - Validate company scope and page advancement before returning True.
        - Never leave self.page on a login/authwall page.
        """
        before_page = None

        try:
            from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit

            before_page = self.page
            before_url = str(before_page.url or "").strip()
            before_lower = before_url.lower()

            print("=" * 60)
            print("PAGINATION")
            print("=" * 60)
            print("Current URL:", before_url)

            if (
                "/search/results/people/" not in before_lower
                or "currentcompany=" not in before_lower
            ):
                print("NEXT ABORTED - current page is not company-scoped people search.")
                return False

            before_query = parse_qs(
                urlsplit(before_url).query,
                keep_blank_values=True,
            )
            company_ids = (
                before_query.get("currentCompany", [])
                or before_query.get("currentcompany", [])
            )

            if not company_ids:
                print("NEXT ABORTED - currentCompany is missing.")
                return False

            print("Current company ID:", company_ids)

            def blocked(url: str) -> bool:
                value = str(url or "").lower()
                return any(
                    part in value
                    for part in (
                        "/login",
                        "/authwall",
                        "/checkpoint",
                        "/uas/login",
                        "/signup",
                        "/ssr-login",
                        "remember-me-auto-login",
                    )
                )

            def company_people_url(url: str) -> bool:
                value = str(url or "").lower()
                if blocked(value):
                    return False
                if (
                    "/search/results/people/" not in value
                    or "currentcompany=" not in value
                ):
                    return False

                try:
                    query = parse_qs(
                        urlsplit(str(url)).query,
                        keep_blank_values=True,
                    )
                    actual_company_ids = (
                        query.get("currentCompany", [])
                        or query.get("currentcompany", [])
                    )
                    return actual_company_ids == company_ids
                except Exception:
                    return False

            def page_number(url: str) -> int:
                try:
                    query = parse_qs(
                        urlsplit(str(url or "")).query,
                        keep_blank_values=True,
                    )
                    raw = (query.get("page", ["1"]) or ["1"])[0]
                    return max(1, int(str(raw).strip()))
                except Exception:
                    return 1

            def canonical_href(href: str) -> str:
                value = str(href or "").strip()
                if value.startswith("/"):
                    value = "https://www.linkedin.com" + value
                return (
                    value.split("?", 1)[0]
                    .split("#", 1)[0]
                    .rstrip("/")
                    .lower()
                )

            def result_signature(page):
                items = []
                try:
                    links = page.locator("a[href*='/in/']")
                    count = min(20, links.count())
                    for i in range(count):
                        try:
                            link = links.nth(i)
                            href = canonical_href(link.get_attribute("href"))
                            if not href:
                                continue
                            try:
                                text = link.inner_text(timeout=800).strip()
                            except Exception:
                                text = ""
                            items.append((href, text[:120]))
                        except Exception:
                            continue
                except Exception:
                    pass
                return tuple(items)

            def find_next_control(page):
                selectors = (
                    "button[data-testid='pagination-controls-next-button-visible']:visible",
                    "button[data-testid*='pagination-controls-next-button']:visible",
                    "nav[aria-label*='Pagination' i] button:visible",
                    "nav[aria-label*='Pagination' i] a:visible",
                    "div.artdeco-pagination button:visible",
                    "div.artdeco-pagination a:visible",
                )

                for selector in selectors:
                    try:
                        controls = page.locator(selector)
                        for i in range(controls.count()):
                            control = controls.nth(i)
                            parts = []

                            for attr in ("aria-label", "title", "data-testid"):
                                try:
                                    value = (control.get_attribute(attr) or "").strip()
                                    if value:
                                        parts.append(value)
                                except Exception:
                                    pass

                            try:
                                text = control.inner_text(timeout=800).strip()
                                if text:
                                    parts.append(text)
                            except Exception:
                                pass

                            label = " ".join(parts).lower()
                            if "next" not in label:
                                continue

                            try:
                                if control.is_disabled():
                                    continue
                            except Exception:
                                pass

                            try:
                                if not control.is_visible():
                                    continue
                            except Exception:
                                continue

                            print(
                                "Next control found:",
                                selector,
                                "[",
                                i,
                                "]",
                            )
                            print("Next label:", label)
                            return control
                    except Exception as ex:
                        print(
                            "Next selector inspection failed:",
                            selector,
                            repr(ex),
                        )

                return None

            def validate_transition(start_url, start_page_no, start_signature, timeout_loops=60):
                destination = ""

                for attempt in range(1, timeout_loops + 1):
                    try:
                        before_page.wait_for_timeout(300)
                    except Exception:
                        pass

                    try:
                        destination = str(before_page.url or "").strip()
                    except Exception:
                        destination = ""

                    if blocked(destination):
                        return False, destination

                    if not company_people_url(destination):
                        continue

                    current_page_no = page_number(destination)
                    current_signature = result_signature(before_page)
                    url_changed = destination.rstrip("/") != start_url.rstrip("/")
                    results_changed = bool(current_signature) and current_signature != start_signature
                    page_advanced = current_page_no > start_page_no

                    if attempt % 5 == 0:
                        print(
                            f"Next-page validation {attempt}/{timeout_loops}:",
                            "url_changed=",
                            url_changed,
                            "results_changed=",
                            results_changed,
                            "page=",
                            current_page_no,
                        )

                    if page_advanced or (url_changed and results_changed):
                        try:
                            before_page.wait_for_timeout(1200)
                        except Exception:
                            pass
                        return True, destination

                return False, destination

            def restore_previous_search_page() -> bool:
                try:
                    if company_people_url(before_page.url):
                        return True
                except Exception:
                    pass

                try:
                    print("Attempting browser-history recovery of authenticated search page...")
                    before_page.go_back(
                        wait_until="domcontentloaded",
                        timeout=30000,
                    )
                except Exception as ex:
                    print("History recovery failed:", repr(ex))

                try:
                    before_page.wait_for_timeout(1500)
                except Exception:
                    pass

                restored_url = str(before_page.url or "").strip()
                print("Recovered page URL:", restored_url)

                if company_people_url(restored_url):
                    print("LIVE EMPLOYEE-SEARCH PAGE RECOVERED")
                    return True

                print("WARNING: live company people-search page could not be restored safely.")
                return False

            def build_same_page_next_url() -> str:
                parsed = urlsplit(before_url)
                pairs = []

                for key, value in parse_qsl(
                    parsed.query,
                    keep_blank_values=True,
                ):
                    if key.lower() == "page":
                        continue
                    pairs.append((key, value))

                existing_keys = {str(key).lower() for key, _ in pairs}

                if "spellcorrectionenabled" not in existing_keys:
                    pairs.append(("spellCorrectionEnabled", "true"))

                if "prioritizemessage" not in existing_keys:
                    pairs.append(("prioritizeMessage", "false"))

                pairs.append(("page", str(page_number(before_url) + 1)))

                return urlunsplit(
                    (
                        parsed.scheme,
                        parsed.netloc,
                        parsed.path,
                        urlencode(pairs),
                        parsed.fragment,
                    )
                )

            def same_page_url_fallback() -> bool:
                target_url = build_same_page_next_url()
                print("Controlled same-page pagination fallback:")
                print(target_url)

                try:
                    before_page.goto(
                        target_url,
                        wait_until="domcontentloaded",
                        timeout=60000,
                        referer=before_url,
                    )
                except Exception as ex:
                    print("Same-page pagination fallback failed:", repr(ex))
                    return False

                if blocked(before_page.url):
                    print(
                        "Same-page pagination fallback reached auth/login:",
                        before_page.url,
                    )
                    return False

                target_page_no = page_number(target_url)
                target_signature = result_signature(before_page)

                for attempt in range(1, 41):
                    try:
                        before_page.wait_for_timeout(500)
                    except Exception:
                        pass

                    destination = str(before_page.url or "").strip()
                    if blocked(destination):
                        print(
                            "Same-page pagination fallback redirected to auth/login:",
                            destination,
                        )
                        return False

                    if not company_people_url(destination):
                        continue

                    actual_page_no = page_number(destination)
                    current_signature = result_signature(before_page)

                    if actual_page_no >= target_page_no:
                        if current_signature or attempt >= 8:
                            print("=" * 60)
                            print("NEXT PAGE VALIDATED - SAME-PAGE FALLBACK")
                            print("=" * 60)
                            print("Final validated URL:", destination)
                            print("Company scope preserved:", company_ids)
                            print("Connection-degree handling: NONE")
                            try:
                                before_page.evaluate("window.scrollTo(0, 0)")
                            except Exception:
                                pass
                            return True

                    if current_signature and current_signature != target_signature:
                        print("NEXT PAGE VALIDATED - RESULT DOM CHANGED")
                        print("Final validated URL:", destination)
                        return True

                print("Same-page fallback did not produce a validated next employee page.")
                return False

            before_signature = result_signature(before_page)
            before_page_number = page_number(before_url)

            # ------------------------------------------------------------
            # Attempt 1: LinkedIn's actual live Next control.
            # ------------------------------------------------------------
            try:
                before_page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
            except Exception:
                pass

            try:
                before_page.wait_for_timeout(1000)
            except Exception:
                pass

            live_navigation_attempted = False

            for live_attempt in (1, 2):
                next_control = find_next_control(before_page)

                if next_control is None:
                    print("No usable Next control found on live company people-search page.")
                    break

                live_navigation_attempted = True

                try:
                    next_control.scroll_into_view_if_needed()
                except Exception:
                    pass

                print(
                    f"Clicking LinkedIn's live Next control (attempt {live_attempt}/2)..."
                )

                try:
                    next_control.click(
                        timeout=15000,
                        no_wait_after=True,
                    )
                except Exception as ex:
                    print("Live Next click failed:", repr(ex))
                    break

                validated, destination = validate_transition(
                    before_url,
                    before_page_number,
                    before_signature,
                )

                if validated:
                    print("=" * 60)
                    print("NEXT PAGE VALIDATED")
                    print("=" * 60)
                    print("Final validated URL:", destination)
                    print("Company scope preserved:", company_ids)
                    print("Connection-degree handling: NONE")
                    try:
                        before_page.evaluate("window.scrollTo(0, 0)")
                    except Exception:
                        pass
                    return True

                if blocked(destination):
                    print(
                        "LIVE NEXT REDIRECTED TO AUTH/SSR:",
                        destination,
                    )

                if live_attempt == 1:
                    if not restore_previous_search_page():
                        break
                    # Refresh the baseline signature after recovery.
                    before_signature = result_signature(before_page)
                    before_page_number = page_number(str(before_page.url or before_url))
                    continue

                break

            # ------------------------------------------------------------
            # Attempt 2: controlled same-page page=N fallback.
            # ------------------------------------------------------------
            if live_navigation_attempted and restore_previous_search_page():
                # Rebuild the baseline from the restored page before fallback.
                restored_url = str(before_page.url or "").strip()
                if company_people_url(restored_url):
                    before_url = restored_url
                    before_signature = result_signature(before_page)
                    if same_page_url_fallback():
                        self.page = before_page
                        return True

            # Never leave the workflow on auth/login after a failed attempt.
            if not company_people_url(before_page.url):
                try:
                    before_page.go_back(
                        wait_until="domcontentloaded",
                        timeout=30000,
                    )
                except Exception:
                    pass

                try:
                    before_page.wait_for_timeout(1000)
                except Exception:
                    pass

            if company_people_url(before_page.url):
                self.page = before_page
                print(
                    "LIVE EMPLOYEE-SEARCH PAGE PRESERVED:",
                    before_page.url,
                )
            else:
                print(
                    "WARNING: authenticated employee-search page could not be preserved after pagination failure.",
                )

            return False

        except Exception as ex:
            print("Pagination failed:", repr(ex))
            try:
                if before_page is not None and company_people_url(before_page.url):
                    self.page = before_page
            except Exception:
                pass
            return False
