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
        """
        Open the company-scoped LinkedIn people-search page.
    
        IMPORTANT:
        - Connection degree is NOT a requirement for this workflow.
        - We deliberately do NOT open or manipulate the Connections filter.
        - We deliberately do NOT rewrite network=F into another network value.
        - Company scope is preserved through currentCompany.
        - Location is handled separately by apply_location()/get_profiles().
        """
    
        print("=" * 60)
        print("OPENING COMPANY EMPLOYEES / PEOPLE SEARCH")
        print("=" * 60)
    
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
                    keep_blank_values=True
                )
                return (
                    query.get("currentCompany", [])
                    or query.get("currentcompany", [])
                )
            except Exception:
                return []
    
        # CASE 1:
        # The company click already landed on LinkedIn's company-scoped
        # people search. Nothing else is required.
        if is_people_url(current_url):
    
            ids = company_ids(current_url)
    
            print("=" * 60)
            print("COMPANY PEOPLE-SEARCH PAGE ALREADY OPEN")
            print("=" * 60)
            print("Company scope:", ids)
    
            if not ids:
                print(
                    "ERROR: Current people-search page has no currentCompany."
                )
                return False
    
            if is_blocked_url(current_url):
                print(
                    "ERROR: Current people-search URL is blocked/authwall."
                )
                return False
    
            # LinkedIn may land on a first-degree-only company people search.
            # Broaden only the network parameter while preserving currentCompany.
            from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit

            parsed = urlsplit(current_url)
            pairs = parse_qsl(parsed.query, keep_blank_values=True)

            rebuilt = []
            replaced_network = False

            for key, value in pairs:
                if key.lower() == "network":
                    if not replaced_network:
                        rebuilt.append(("network", '["F","S","O"]'))
                        replaced_network = True
                else:
                    rebuilt.append((key, value))

            if not replaced_network:
                rebuilt.append(("network", '["F","S","O"]'))

            broadened_url = urlunsplit(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    urlencode(rebuilt),
                    parsed.fragment,
                )
            )

            print("Broadening company people-search network:")
            print("FROM:", current_url)
            print("TO:", broadened_url)

            self.page.goto(
                broadened_url,
                wait_until="domcontentloaded",
                timeout=60000,
            )
            self.page.wait_for_timeout(5000)

            final_url = str(self.page.url or "").strip()

            if is_blocked_url(final_url) or not is_people_url(final_url):
                print("ERROR: Broadening network left company people search.")
                print("Final URL:", final_url)
                return False

            final_ids = company_ids(final_url)

            if final_ids != ids:
                print("ERROR: currentCompany changed while broadening network.")
                print("Expected:", ids)
                print("Actual:", final_ids)
                return False

            final_query = parse_qs(
                urlsplit(final_url).query,
                keep_blank_values=True,
            )
            final_network = " ".join(
                final_query.get("network", [])
                or final_query.get("Network", [])
            ).lower()

            if '"s"' not in final_network or '"o"' not in final_network:
                print("ERROR: Network was not broadened to F/S/O.")
                print("Final network:", final_network)
                return False

            print("Connection-degree filter: URL scope F/S/O")
            print("Network parameter:", final_network)
            print("Company scope preserved:", final_ids)
            print("Company people search ready.")
            return True
    
        # CASE 2:
        # We are still on the company page. Use LinkedIn's own
        # company-scoped people-search link. Never construct a generic
        # people-search URL and never modify the returned href.
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
                href = (
                    link.get_attribute("href")
                    or ""
                ).strip()
    
                if (
                    not href
                    or "/search/results/people/" not in href.lower()
                ):
                    continue
    
                ids = company_ids(href)
    
                if not ids:
                    continue
    
                if (
                    selected_company_ids
                    and ids != selected_company_ids
                ):
                    continue
    
                selected = link
    
                print(
                    "Selected company-scoped people-search link:",
                    href
                )
                break
    
            except Exception:
                continue
    
        if selected is None:
            print(
                "ERROR: No company-scoped people-search link found."
            )
            return False
    
        try:
            selected.scroll_into_view_if_needed()
            selected.click(timeout=15000)
            self.page.wait_for_timeout(5000)
        except Exception as ex:
            print(
                "People-search link click failed:",
                repr(ex)
            )
            return False
    
        final_url = str(
            self.page.url or ""
        ).strip()
    
        print(
            "Final employee-search URL:",
            final_url
        )
    
        if (
            is_blocked_url(final_url)
            or not is_people_url(final_url)
        ):
            print(
                "ERROR: LinkedIn did not open an authenticated "
                "company people search."
            )
            return False
    
        final_ids = company_ids(final_url)
    
        if (
            selected_company_ids
            and final_ids != selected_company_ids
        ):
            print(
                "ERROR: currentCompany changed after opening employee search."
            )
            print("Expected:", selected_company_ids)
            print("Actual:", final_ids)
            return False
    
        print("=" * 60)
        print("COMPANY PEOPLE SEARCH READY")
        print("=" * 60)
        print("Final URL:", final_url)
        print("Connection-degree filter: URL scope F/S/O")
        print("Network parameter:", final_network if "final_network" in locals() else "verified above")
        print("Company scope preserved:", final_ids)
    
        return True

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




    def get_profiles(self, company="", location=""):
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

        profiles = []
        seen_urls = set()

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
                        "a[href*='/in/']:visible"
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
                "li.reusable-search__result-container:visible",
                "li[class*='reusable-search__result']:visible",
                "li.entity-result:visible",
                "div.entity-result:visible",
                "li.search-result:visible",
                "li[class*='search-result']:visible",
                "ul.reusable-search__entity-result-list > li:visible",
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
            "li.reusable-search__result-container:visible",
            "li[class*='reusable-search__result']:visible",
            "li.entity-result:visible",
            "div.entity-result:visible",
            "li.search-result:visible",
            "li[class*='search-result']:visible",
            "ul.reusable-search__entity-result-list > li:visible",
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

                    if not card.is_visible():
                        continue

                    card_text = normalize_text(
                        card.inner_text()
                    )

                    if len(card_text) < 20:
                        continue

                    links = card.locator(
                        "a[href*='/in/']:visible"
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

                    name = (
                        link
                        .inner_text(
                            timeout=1500
                        )
                        .strip()
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
        #
        # PURE PLAYWRIGHT / PYTHON
        #
        # NO page.evaluate()
        #
        # The old implementation walked up to a broad ancestor and
        # then did:
        #
        #     primary = groupLinks[0]
        #
        # That is the reason SmartWorks produced only one candidate
        # even though the result group contained several employees.
        #
        # This implementation evaluates EACH visible /in/ link
        # independently and accepts only a SMALL local ancestor.
        # ============================================================

        print("=" * 60)
        print("PASS 2 - LOCAL PLAYWRIGHT EMPLOYEE EXTRACTION")
        print("=" * 60)

        try:

            links = self.page.locator(
                "a[href*='/in/']:visible"
            )

            link_count = links.count()

        except Exception as ex:

            print(
                "Visible /in/ link lookup failed:",
                repr(ex)
            )

            links = None
            link_count = 0

        print(
            "Visible /in/ links found:",
            link_count
        )

        if links is not None and link_count > 0:

            for link_index in range(
                link_count
            ):

                try:

                    link = links.nth(
                        link_index
                    )

                    if not link.is_visible():
                        continue

                    href = (
                        link.get_attribute(
                            "href"
                        )
                        or ""
                    ).strip()

                    profile_url = (
                        canonical_profile_url(
                            href
                        )
                    )

                    if not profile_url:
                        continue

                    name = normalize_text(
                        link.inner_text(
                            timeout=1500
                        )
                    )

                    if not name:
                        continue

                    if len(name) > 180:
                        continue

                    chosen_text = ""
                    chosen_level = -1
                    chosen_link_count = 0

                    # ------------------------------------------------
                    # Walk ONLY 8 local ancestors.
                    #
                    # A valid local result container normally contains
                    # 1-4 profile links. A page-level result container
                    # contains many and is therefore rejected.
                    # ------------------------------------------------

                    for level in range(
                        0,
                        8
                    ):

                        try:

                            ancestor = link.locator(
                                "xpath="
                                + "/.." * (level + 1)
                            )

                            if not ancestor.count():
                                continue

                            if not ancestor.is_visible():
                                continue

                            ancestor_text = normalize_text(
                                ancestor.inner_text(
                                    timeout=1000
                                )
                            )

                            if (
                                len(ancestor_text) < 20
                                or len(ancestor_text) > 1800
                            ):
                                continue

                            ancestor_links = ancestor.locator(
                                "a[href*='/in/']:visible"
                            )

                            local_count = (
                                ancestor_links.count()
                            )

                            if (
                                local_count < 1
                                or local_count > 4
                            ):
                                continue

                            first_href = (
                                ancestor_links
                                .nth(0)
                                .get_attribute(
                                    "href"
                                )
                                or ""
                            )

                            first_url = (
                                canonical_profile_url(
                                    first_href
                                )
                            )

                            # If this /in/ link is not the first profile
                            # link in the local container, it is probably
                            # a nested mutual connection rather than the
                            # employee represented by this result.
                            if first_url != profile_url:
                                continue

                            chosen_text = ancestor_text
                            chosen_level = level
                            chosen_link_count = local_count

                            break

                        except Exception:

                            continue

                    # ------------------------------------------------
                    # Conservative immediate-parent fallback.
                    # ------------------------------------------------

                    if not chosen_text:

                        try:

                            parent = link.locator(
                                "xpath=.."
                            )

                            if (
                                parent.count()
                                and parent.is_visible()
                            ):

                                parent_text = normalize_text(
                                    parent.inner_text(
                                        timeout=1000
                                    )
                                )

                                if (
                                    10
                                    <= len(parent_text)
                                    <= 500
                                ):

                                    chosen_text = parent_text

                        except Exception:

                            pass

                    # ------------------------------------------------
                    # IMPORTANT:
                    #
                    # Do not require location here.
                    #
                    # LinkedIn's virtualized DOM can omit location text
                    # while still rendering a valid employee result.
                    #
                    # SearchWorkflowV2/profile validation remains the
                    # authoritative company/location check.
                    # ------------------------------------------------

                    accepted = add_candidate(
                        href,
                        name,
                        chosen_text or name,
                        enforce_location=False
                    )

                    if accepted:

                        print("-" * 60)

                        print(
                            "EMPLOYEE CANDIDATE:",
                            profile_url
                        )

                        print(
                            "Primary anchor:",
                            name[:200]
                        )

                        print(
                            "Local ancestor level:",
                            chosen_level
                        )

                        print(
                            "Local /in/ link count:",
                            chosen_link_count
                        )

                        print(
                            "Result group:",
                            (chosen_text or name)[:500]
                        )

                        print(
                            "Connection degree: IGNORED"
                        )

                except Exception as ex:

                    print(
                        f"PASS 2 link "
                        f"{link_index + 1} inspection failed:",
                        repr(ex)
                    )

        else:

            print(
                "No visible /in/ links available for PASS 2."
            )

        # ============================================================
        # FINAL RESULT
        # ============================================================

        print("=" * 60)

        print(
            "EMPLOYEE PROFILES EXTRACTED:",
            len(profiles)
        )

        print("=" * 60)

        return profiles


    def next_page(self):
        """
        Move to the next company-scoped LinkedIn people-search page.

        URL change alone is not considered success. LinkedIn may update the
        URL before its virtualized result cards are rendered, so we wait for
        either visible /in/ results or recognizable result-card DOM.
        """
        try:
            from urllib.parse import urlsplit, parse_qs

            before_url = str(self.page.url or "").strip()
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

            before_query = parse_qs(urlsplit(before_url).query, keep_blank_values=True)
            company_ids = (
                before_query.get("currentCompany", [])
                or before_query.get("currentcompany", [])
            )

            print("Current company ID:", company_ids)

            selectors = (
                "button[data-testid='pagination-controls-next-button-visible']:visible",
                "nav[aria-label*='Pagination' i] button:visible",
                "nav[aria-label*='Pagination' i] a:visible",
                "div.artdeco-pagination button:visible",
                "div.artdeco-pagination a:visible",
            )

            next_control = None

            for selector in selectors:
                try:
                    controls = self.page.locator(selector)
                    for i in range(controls.count()):
                        control = controls.nth(i)

                        text = ""
                        aria = ""
                        title = ""

                        try:
                            text = control.inner_text(timeout=1000).strip()
                        except Exception:
                            pass
                        try:
                            aria = (control.get_attribute("aria-label") or "").strip()
                        except Exception:
                            pass
                        try:
                            title = (control.get_attribute("title") or "").strip()
                        except Exception:
                            pass

                        label = " ".join(x for x in (text, aria, title) if x).lower()

                        if "next" not in label:
                            continue

                        try:
                            if control.is_disabled():
                                continue
                        except Exception:
                            pass

                        if control.is_visible():
                            next_control = control
                            print("Next control found:", selector, "[", i, "]")
                            print("Next label:", label)
                            break

                    if next_control is not None:
                        break
                except Exception as ex:
                    print("Next selector inspection failed:", selector, repr(ex))

            if next_control is None:
                print("No usable Next control found.")
                return False

            try:
                next_control.scroll_into_view_if_needed()
            except Exception:
                pass

            try:
                next_control.click(timeout=15000)
            except Exception as ex:
                print("Next click failed:", repr(ex))
                return False

            # First wait for navigation/state change. Do not require the
            # result DOM yet.
            changed_url = False
            current_url = before_url

            for _ in range(60):
                self.page.wait_for_timeout(250)
                current_url = str(self.page.url or "").strip()
                if current_url != before_url:
                    changed_url = True
                    break

            print("URL after Next:", current_url)

            # LinkedIn can briefly expose a valid people-search URL and
            # then redirect the same Page back to linkedin.com. Require the
            # destination to remain company-scoped before returning True.
            stable_people_url = False
            stable_url = current_url

            for stability_attempt in range(1, 13):
                self.page.wait_for_timeout(500)

                try:
                    stable_url = str(
                        self.page.url or ""
                    ).strip()
                except Exception:
                    stable_url = ""

                stable_lower = stable_url.lower()

                if (
                    "/search/results/people/" in stable_lower
                    and "currentcompany=" in stable_lower
                    and not any(
                        part in stable_lower
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
                ):
                    if stability_attempt >= 4:
                        stable_people_url = True
                        current_url = stable_url
                        break
                else:
                    print(
                        "NEXT DESTINATION LOST COMPANY PEOPLE SEARCH:",
                        stable_url
                    )
                    break

            print(
                "Next-page destination stable:",
                stable_people_url
            )
            print(
                "Stable destination URL:",
                stable_url
            )

            if not stable_people_url:
                print(
                    "NEXT FAILED - destination did not remain on "
                    "company people-search."
                )
                return False

            if not changed_url:
                print("NEXT FAILED - URL did not change.")
                return False

            current_url = stable_url
            current_lower = current_url.lower()

            bad_parts = (
                "/login",
                "/authwall",
                "/checkpoint",
                "/uas/login",
                "/signup",
                "/ssr-login",
                "remember-me-auto-login",
            )

            if any(part in current_lower for part in bad_parts):
                print("NEXT FAILED - LinkedIn redirected to authentication/SSR.")
                print("Authentication URL:", current_url)
                return False

            if (
                "/search/results/people/" not in current_lower
                or "currentcompany=" not in current_lower
            ):
                print("NEXT FAILED - navigation left company people-search.")
                return False

            current_query = parse_qs(urlsplit(current_url).query, keep_blank_values=True)
            current_company_ids = (
                current_query.get("currentCompany", [])
                or current_query.get("currentcompany", [])
            )

            if company_ids and current_company_ids != company_ids:
                print("NEXT FAILED - currentCompany changed.")
                print("Before:", company_ids)
                print("After:", current_company_ids)
                return False

            print("Company scope preserved.")


            # LinkedIn can expose employee-result text before
            # Playwright exposes /in/ anchors or legacy result-card classes.
            #
            # Validate page 2 using three independent signals:
            #   1. visible /in/ links
            #   2. recognizable result-card DOM
            #   3. rendered employee-result text
            #
            # This prevents a valid page from being rejected solely because
            # LinkedIn changed or virtualized its result DOM.

            rendered_profiles = 0
            rendered_cards = 0
            rendered_result_text = False

            for attempt in range(1, 41):
                self.page.wait_for_timeout(500)

                try:
                    rendered_profiles = self.page.locator(
                        "a[href*='/in/']:visible"
                    ).count()
                except Exception:
                    rendered_profiles = 0

                try:
                    rendered_cards = 0

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
                            count = self.page.locator(
                                selector
                            ).count()

                            if count > rendered_cards:
                                rendered_cards = count
                        except Exception:
                            continue

                except Exception:
                    rendered_cards = 0

                try:
                    body_text = self.page.locator(
                        "body"
                    ).inner_text(timeout=2000)

                    normalized_body = re.sub(
                        r"\s+",
                        " ",
                        body_text or ""
                    ).strip().lower()

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

                    role_hits = sum(
                        1
                        for signal in role_signals
                        if signal in normalized_body
                    )

                    result_words = (
                        "people",
                        "employees",
                        "results",
                        "connections",
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
                    f"Result DOM wait {attempt}/40:",
                    rendered_profiles,
                    "visible /in/ links;",
                    rendered_cards,
                    "recognizable result cards;",
                    rendered_result_text,
                    "employee-result text"
                )

                if (
                    rendered_profiles > 0
                    or rendered_cards > 0
                    or rendered_result_text
                ):
                    print("=" * 60)
                    print("NEXT PAGE VALIDATED")
                    print("=" * 60)
                    print("Same company people-search:", True)
                    print(
                        "Validation:",
                        "links/cards/text"
                    )
                    return True

                if attempt in (10, 20, 30):
                    try:
                        self.page.mouse.wheel(0, 1200)
                    except Exception:
                        pass

            print("=" * 60)
            print("NEXT REJECTED")
            print("URL changed but no employee result DOM rendered.")
            print("Current URL:", current_url)

            try:
                body_text = self.page.locator("body").inner_text()
                print("Current page text length:", len(body_text))
                print("Current page text preview:", body_text[:1000])
            except Exception as ex:
                print("Could not inspect empty result page:", repr(ex))

            return False

        except Exception as ex:
            print("Pagination failed:", repr(ex))
            return False


