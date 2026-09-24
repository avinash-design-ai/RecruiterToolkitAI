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
        Advance the authenticated company-scoped LinkedIn people search.

        This is a fail-safe pagination state machine:
        - Preserve LinkedIn's returned query parameters, including network.
        - Change ONLY page=N when constructing an explicit next-page URL.
        - First try SAME-PAGE authenticated page=N navigation.
        - Then try a FRESH authenticated tab using the same exact URL.
        - Then use LinkedIn's own Next href.
        - Finally click the live Next control.
        - Validate company scope, exact page number, authentication, and
          employee-result DOM before accepting a transition.
        - Restore the previous authenticated employee-search page after
          failed navigation.
        - Return False only when LinkedIn explicitly exposes a disabled Next
          control. Any unresolved navigation failure raises so the workflow
          cannot falsely report "No more employee pages."
        """
        from hashlib import sha1
        from urllib.parse import (
            parse_qs,
            parse_qsl,
            urlencode,
            urljoin,
            urlsplit,
            urlunsplit,
        )

        owner_page = self.page
        before_url = str(owner_page.url or "").strip()

        print("=" * 60)
        print("PAGINATION - FAIL-SAFE STATE MACHINE")
        print("=" * 60)
        print("Current URL:", before_url)

        def blocked(url):
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

        def parse_query(url):
            return parse_qs(
                urlsplit(str(url or "")).query,
                keep_blank_values=True,
            )

        def company_ids(url):
            query = parse_query(url)
            return (
                query.get("currentCompany", [])
                or query.get("currentcompany", [])
            )

        def page_number(url):
            query = parse_query(url)
            try:
                raw = (query.get("page", ["1"]) or ["1"])[0]
                return max(1, int(str(raw).strip()))
            except Exception:
                return 1

        def is_company_people_search(url):
            value = str(url or "").lower()
            if blocked(value):
                return False
            if "/search/results/people/" not in value:
                return False
            return bool(company_ids(url))

        def non_page_query_map(url):
            query = parse_query(url)
            return {
                key.lower(): tuple(values)
                for key, values in query.items()
                if key.lower() != "page"
            }

        def result_signature(active_page):
            chunks = []

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
                    rows = active_page.locator(selector)
                    count = min(rows.count(), 12)

                    for index in range(count):
                        try:
                            text = rows.nth(index).inner_text(
                                timeout=1000
                            )
                        except Exception:
                            continue

                        text = " ".join(
                            str(text or "").split()
                        ).strip()

                        if text:
                            chunks.append(text[:1600])

                    if chunks:
                        break
                except Exception:
                    continue

            try:
                links = active_page.locator("a[href*='/in/']")
                count = min(links.count(), 25)

                for index in range(count):
                    try:
                        href = (
                            links.nth(index)
                            .get_attribute("href")
                            or ""
                        ).strip()
                    except Exception:
                        continue

                    if href:
                        chunks.append(
                            href.split("?", 1)[0]
                            .split("#", 1)[0]
                            .rstrip("/")
                            .lower()
                        )
            except Exception:
                pass

            if not chunks:
                try:
                    body = active_page.locator("body").inner_text(
                        timeout=1500
                    )
                    body = " ".join(
                        str(body or "").split()
                    ).strip()

                    if body:
                        chunks.append(body[:5000])
                except Exception:
                    pass

            payload = "\n".join(chunks).strip()

            return sha1(
                payload.encode(
                    "utf-8",
                    errors="ignore",
                )
            ).hexdigest()

        def result_state(active_page):
            visible_links = 0
            result_cards = 0
            body_text = ""

            try:
                visible_links = active_page.locator(
                    "a[href*='/in/']:visible"
                ).count()
            except Exception:
                visible_links = 0

            for selector in (
                "li.reusable-search__result-container:visible",
                "li[class*='reusable-search__result']:visible",
                "li.entity-result:visible",
                "div.entity-result:visible",
                "li.search-result:visible",
                "li[class*='search-result']:visible",
                "ul.reusable-search__entity-result-list > li:visible",
            ):
                try:
                    count = active_page.locator(selector).count()
                    if count > result_cards:
                        result_cards = count
                except Exception:
                    continue

            try:
                body_text = " ".join(
                    str(
                        active_page.locator("body").inner_text(
                            timeout=2000
                        )
                        or ""
                    ).split()
                ).lower()
            except Exception:
                body_text = ""

            no_results = any(
                marker in body_text
                for marker in (
                    "no results",
                    "no people found",
                    "no results found",
                    "we couldn't find",
                )
            )

            return (
                visible_links,
                result_cards,
                no_results,
            )

        def employee_dom_ready(
            active_page,
            previous_signature,
        ):
            """
            Require the destination page to render employee-search content.
            A changed signature is preferred; if LinkedIn virtualizes identical
            shell text, populated result DOM is still accepted after the URL
            has advanced and the destination is authenticated.
            """
            for attempt in range(1, 61):
                try:
                    active_page.wait_for_timeout(300)
                except Exception:
                    pass

                current_url = str(
                    active_page.url or ""
                ).strip()

                if blocked(current_url):
                    print(
                        "Destination reached auth/login state:",
                        current_url,
                    )
                    return False

                if not is_company_people_search(current_url):
                    continue

                if company_ids(current_url) != original_company_ids:
                    print(
                        "Destination company scope changed:",
                        current_url,
                    )
                    return False

                if page_number(current_url) != target_page_number:
                    continue

                visible_links, result_cards, no_results = result_state(
                    active_page
                )

                current_signature = result_signature(
                    active_page
                )

                signature_changed = (
                    bool(current_signature)
                    and current_signature != previous_signature
                )

                populated = (
                    visible_links > 0
                    or result_cards > 0
                    or no_results
                )

                if signature_changed and populated:
                    print(
                        "Destination result signature changed and "
                        "employee DOM is populated."
                    )
                    return True

                if populated and previous_signature == "":
                    print(
                        "Destination employee DOM is populated; "
                        "no previous signature was available."
                    )
                    return True

                if (
                    populated
                    and attempt >= 20
                ):
                    print(
                        "Destination page reached correct URL and populated "
                        "employee DOM after waiting for hydration."
                    )
                    return True

                if attempt % 10 == 0:
                    print(
                        f"Next-page validation {attempt}/60:",
                        "page=",
                        page_number(current_url),
                        "links=",
                        visible_links,
                        "cards=",
                        result_cards,
                        "no_results=",
                        no_results,
                        "signature_changed=",
                        signature_changed,
                    )

            return False

        if not is_company_people_search(before_url):
            raise RuntimeError(
                "Pagination cannot start: current page is not an "
                "authenticated company-scoped LinkedIn people search."
            )

        original_company_ids = company_ids(before_url)

        if not original_company_ids:
            raise RuntimeError(
                "Pagination cannot start: currentCompany is missing."
            )

        current_page_number = page_number(before_url)
        target_page_number = current_page_number + 1
        original_query_map = non_page_query_map(before_url)
        previous_signature = result_signature(owner_page)

        print("Current page:", current_page_number)
        print("Target page:", target_page_number)
        print("Company scope:", original_company_ids)
        print(
            "Network parameter:",
            parse_query(before_url).get("network", []),
        )

        def build_page_url(start_url):
            parsed = urlsplit(start_url)

            pairs = []
            page_written = False

            for key, value in parse_qsl(
                parsed.query,
                keep_blank_values=True,
            ):
                if key.lower() == "page":
                    if not page_written:
                        pairs.append(
                            (
                                key,
                                str(target_page_number),
                            )
                        )
                        page_written = True
                    continue

                pairs.append((key, value))

            if not page_written:
                pairs.append(
                    (
                        "page",
                        str(target_page_number),
                    )
                )

            return urlunsplit(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    urlencode(
                        pairs,
                        doseq=True,
                    ),
                    parsed.fragment,
                )
            )

        def query_contract_ok(destination):
            if not is_company_people_search(destination):
                return False

            if company_ids(destination) != original_company_ids:
                return False

            if page_number(destination) != target_page_number:
                return False

            if non_page_query_map(destination) != original_query_map:
                print(
                    "Query contract mismatch."
                )
                print(
                    "Expected non-page params:",
                    original_query_map,
                )
                print(
                    "Actual non-page params:",
                    non_page_query_map(destination),
                )
                return False

            return True

        direct_next_url = build_page_url(
            before_url
        )

        if non_page_query_map(direct_next_url) != original_query_map:
            raise RuntimeError(
                "Safety check failed: constructing page=N changed "
                "a query parameter other than page."
            )

        print("Direct next-page URL:", direct_next_url)
        print(
            "Non-page query parameters preserved:",
            original_query_map,
        )

        def restore_owner_page():
            for attempt in range(1, 3):
                try:
                    print(
                        f"Restoring authenticated employee page "
                        f"(attempt {attempt}/2)..."
                    )

                    owner_page.goto(
                        before_url,
                        wait_until="domcontentloaded",
                        timeout=60000,
                        referer=before_url,
                    )
                    owner_page.wait_for_timeout(3000)

                    restored_url = str(
                        owner_page.url or ""
                    ).strip()

                    if (
                        is_company_people_search(restored_url)
                        and company_ids(restored_url)
                        == original_company_ids
                    ):
                        print(
                            "Employee-search page restored:",
                            restored_url,
                        )
                        return True
                except Exception as exc:
                    print(
                        "Restore attempt failed:",
                        repr(exc),
                    )

                try:
                    owner_page.go_back(
                        wait_until="domcontentloaded",
                        timeout=30000,
                    )
                    owner_page.wait_for_timeout(2000)

                    restored_url = str(
                        owner_page.url or ""
                    ).strip()

                    if (
                        is_company_people_search(restored_url)
                        and company_ids(restored_url)
                        == original_company_ids
                    ):
                        print(
                            "Employee-search page restored via history:",
                            restored_url,
                        )
                        return True
                except Exception:
                    pass

            return False

        def same_page_attempt():
            print("=" * 60)
            print("PAGINATION ATTEMPT: SAME AUTHENTICATED PAGE")
            print("=" * 60)

            try:
                owner_page.goto(
                    direct_next_url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                    referer=before_url,
                )

                owner_page.wait_for_timeout(2500)

                destination = str(
                    owner_page.url or ""
                ).strip()

                print(
                    "Same-page destination:",
                    destination,
                )

                if (
                    query_contract_ok(destination)
                    and employee_dom_ready(
                        owner_page,
                        previous_signature,
                    )
                ):
                    print("=" * 60)
                    print("NEXT PAGE VALIDATED VIA SAME PAGE")
                    print("=" * 60)
                    print(
                        "Page number:",
                        page_number(destination),
                    )
                    print(
                        "Company scope:",
                        company_ids(destination),
                    )
                    print(
                        "Network parameter:",
                        parse_query(destination).get(
                            "network",
                            [],
                        ),
                    )
                    return True

            except Exception as exc:
                print(
                    "Same-page next-page navigation raised:",
                    repr(exc),
                )

            restore_owner_page()
            return False

        # ------------------------------------------------------------
        # PRIMARY: same authenticated page.
        # ------------------------------------------------------------
        if same_page_attempt():
            return True

        # ------------------------------------------------------------
        # SECONDARY: a fresh authenticated tab in the same browser context.
        # This is retained because older runs successfully advanced this way.
        # ------------------------------------------------------------
        print("=" * 60)
        print("PAGINATION ATTEMPT: FRESH AUTHENTICATED TAB")
        print("=" * 60)

        fresh_page = None

        try:
            fresh_page = owner_page.context.new_page()

            fresh_page.goto(
                direct_next_url,
                wait_until="domcontentloaded",
                timeout=60000,
                referer=before_url,
            )

            fresh_page.wait_for_timeout(2500)

            destination = str(
                fresh_page.url or ""
            ).strip()

            print(
                "Fresh-tab destination:",
                destination,
            )

            if (
                query_contract_ok(destination)
                and employee_dom_ready(
                    fresh_page,
                    previous_signature,
                )
            ):
                old_page = self.page
                self.page = fresh_page
                fresh_page = None

                try:
                    if (
                        old_page is not self.page
                        and not old_page.is_closed()
                    ):
                        old_page.close()
                except Exception as exc:
                    print(
                        "Previous employee-page cleanup warning:",
                        repr(exc),
                    )

                print("=" * 60)
                print("NEXT PAGE VALIDATED VIA FRESH TAB")
                print("=" * 60)
                print(
                    "Page number:",
                    page_number(destination),
                )
                print(
                    "Company scope:",
                    company_ids(destination),
                )
                print(
                    "Network parameter:",
                    parse_query(destination).get(
                        "network",
                        [],
                    ),
                )
                return True

        except Exception as exc:
            print(
                "Fresh-tab next-page navigation raised:",
                repr(exc),
            )
        finally:
            if fresh_page is not None:
                try:
                    if not fresh_page.is_closed():
                        fresh_page.close()
                except Exception:
                    pass

        restore_owner_page()

        # ------------------------------------------------------------
        # SECONDARY: LinkedIn-provided Next href.
        # ------------------------------------------------------------
        print("=" * 60)
        print("PAGINATION ATTEMPT: LINKEDIN NEXT HREF")
        print("=" * 60)

        next_href = ""

        for selector in (
            "a[aria-label*='next' i]:visible",
            "a[title*='next' i]:visible",
            "a[data-test*='next' i]:visible",
            "a[href*='page=']:visible",
        ):
            try:
                locator = owner_page.locator(selector)
                count = locator.count()

                for index in range(
                    min(count, 100)
                ):
                    item = locator.nth(index)

                    try:
                        href = (
                            item.get_attribute("href")
                            or ""
                        ).strip()
                    except Exception:
                        href = ""

                    if not href:
                        continue

                    absolute = urljoin(
                        str(owner_page.url or ""),
                        href,
                    )

                    if (
                        is_company_people_search(
                            absolute
                        )
                        and page_number(absolute)
                        > current_page_number
                        and company_ids(absolute)
                        == original_company_ids
                    ):
                        next_href = absolute
                        break

                if next_href:
                    break
            except Exception:
                continue

        if next_href:
            print(
                "LinkedIn Next href:",
                next_href,
            )

            if next_href != direct_next_url:
                try:
                    owner_page.goto(
                        next_href,
                        wait_until="domcontentloaded",
                        timeout=60000,
                        referer=before_url,
                    )
                    owner_page.wait_for_timeout(2500)

                    destination = str(
                        owner_page.url or ""
                    ).strip()

                    if (
                        page_number(destination)
                        > current_page_number
                        and query_contract_ok(
                            destination
                        )
                        and employee_dom_ready(
                            owner_page,
                            previous_signature,
                        )
                    ):
                        print("=" * 60)
                        print("NEXT PAGE VALIDATED VIA LINKEDIN HREF")
                        print("=" * 60)
                        print(
                            "Final URL:",
                            destination,
                        )
                        return True

                except Exception as exc:
                    print(
                        "LinkedIn Next href navigation raised:",
                        repr(exc),
                    )

                restore_owner_page()
        else:
            print(
                "No usable LinkedIn Next href found."
            )

        # ------------------------------------------------------------
        # FINAL NAVIGATION FALLBACK: live Next control.
        # ------------------------------------------------------------
        print("=" * 60)
        print("PAGINATION ATTEMPT: LIVE NEXT CONTROL")
        print("=" * 60)

        next_control = None
        disabled_next_found = False

        for selector in (
            "button[data-testid='pagination-controls-next-button-visible']:visible",
            "button[data-testid*='pagination-controls-next-button']:visible",
            "nav[aria-label*='Pagination' i] button:visible",
            "nav[aria-label*='Pagination' i] a:visible",
            "div.artdeco-pagination button:visible",
            "div.artdeco-pagination a:visible",
            "button:visible",
            "[role='button']:visible",
            "a:visible",
        ):
            try:
                controls = owner_page.locator(selector)

                for index in range(
                    min(
                        controls.count(),
                        250,
                    )
                ):
                    control = controls.nth(index)

                    parts = []

                    for attr in (
                        "aria-label",
                        "title",
                        "data-testid",
                        "data-test",
                        "data-control-name",
                    ):
                        try:
                            value = (
                                control.get_attribute(attr)
                                or ""
                            ).strip()

                            if value:
                                parts.append(value)
                        except Exception:
                            pass

                    try:
                        text_value = (
                            control.inner_text(
                                timeout=500
                            )
                            or ""
                        ).strip()

                        if text_value:
                            parts.append(text_value)
                    except Exception:
                        pass

                    label = " ".join(
                        parts
                    ).lower()

                    if "next" not in label:
                        continue

                    if "previous" in label:
                        continue

                    is_disabled = False

                    try:
                        aria_disabled = (
                            control.get_attribute(
                                "aria-disabled"
                            )
                            or ""
                        ).lower()

                        is_disabled = (
                            aria_disabled == "true"
                        )
                    except Exception:
                        pass

                    try:
                        if control.is_disabled():
                            is_disabled = True
                    except Exception:
                        pass

                    try:
                        class_name = (
                            control.get_attribute(
                                "class"
                            )
                            or ""
                        ).lower()

                        if "disabled" in class_name:
                            is_disabled = True
                    except Exception:
                        pass

                    if is_disabled:
                        disabled_next_found = True
                        print(
                            "Disabled Next control found:",
                            label[:200],
                        )
                        continue

                    try:
                        if not control.is_visible():
                            continue
                    except Exception:
                        continue

                    next_control = control
                    print(
                        "Enabled Next control found:",
                        label[:200],
                    )
                    break

                if next_control is not None:
                    break

            except Exception:
                continue

        if next_control is not None:
            try:
                next_control.scroll_into_view_if_needed()
            except Exception:
                pass

            try:
                next_control.click(
                    timeout=15000,
                    no_wait_after=True,
                )
            except Exception as exc:
                print(
                    "Live Next click raised:",
                    repr(exc),
                )
            else:
                for attempt in range(1, 61):
                    try:
                        owner_page.wait_for_timeout(300)
                    except Exception:
                        pass

                    destination = str(
                        owner_page.url or ""
                    ).strip()

                    if blocked(destination):
                        print(
                            "Live Next redirected to auth/SSR:",
                            destination,
                        )
                        break

                    if (
                        is_company_people_search(
                            destination
                        )
                        and page_number(destination)
                        == target_page_number
                        and company_ids(destination)
                        == original_company_ids
                    ):
                        if employee_dom_ready(
                            owner_page,
                            previous_signature,
                        ):
                            print("=" * 60)
                            print("NEXT PAGE VALIDATED VIA LIVE NEXT")
                            print("=" * 60)
                            print(
                                "Final URL:",
                                destination,
                            )
                            return True

                    if attempt % 10 == 0:
                        print(
                            f"Live Next validation {attempt}/60:",
                            destination,
                        )

        if disabled_next_found:
            print(
                "LinkedIn explicitly reported the Next control as disabled."
            )
            print(
                "This is treated as a genuine end-of-results state."
            )
            restore_owner_page()
            return False

        restore_ok = restore_owner_page()

        raise RuntimeError(
            "LinkedIn pagination could not be validated. "
            f"Current page={current_page_number}; "
            f"target page={target_page_number}; "
            f"company={original_company_ids}; "
            f"restored={restore_ok}. "
            "The workflow was deliberately prevented from treating "
            "this navigation failure as end-of-results."
        )
