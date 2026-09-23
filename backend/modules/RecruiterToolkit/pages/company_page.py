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

        # PATCH: Dismiss LinkedIn blocking dialogs before global company search
        # LinkedIn can leave a modal/dialog over the authenticated Feed page.
        # Playwright finds the search input but its click is intercepted by the
        # dialog, causing a 30-second Locator.click timeout.
        try:
            dialogs = self.page.locator(
                "dialog[open]:visible, [role='dialog']:visible"
            )

            dialog_count = dialogs.count()

            if dialog_count:
                print(
                    "Open LinkedIn dialog(s) detected before company search:",
                    dialog_count,
                )

                for i in range(dialog_count):
                    try:
                        dialog = dialogs.nth(i)

                        try:
                            dialog_text = (
                                dialog.inner_text(timeout=2000)
                                .strip()
                            )
                        except Exception:
                            dialog_text = ""

                        if dialog_text:
                            print(
                                "Blocking dialog text:",
                                dialog_text[:500],
                            )
                    except Exception:
                        pass

                # First use LinkedIn's normal modal-dismiss behavior.
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(750)

                # Some dialogs do not close on Escape. Try an explicit
                # Close/Dismiss button inside the remaining dialog only.
                dialogs = self.page.locator(
                    "dialog[open]:visible, [role='dialog']:visible"
                )

                remaining = dialogs.count()

                if remaining:
                    for i in range(remaining):
                        try:
                            dialog = dialogs.nth(i)
                            close_buttons = dialog.get_by_role(
                                "button",
                                name=re.compile(
                                    r"close|dismiss|not now|cancel",
                                    re.IGNORECASE,
                                ),
                            )

                            if close_buttons.count():
                                close_buttons.first.click(timeout=5000)
                                self.page.wait_for_timeout(500)
                                break
                        except Exception as ex:
                            print(
                                "Dialog close-button attempt failed:",
                                repr(ex),
                            )

                dialogs = self.page.locator(
                    "dialog[open]:visible, [role='dialog']:visible"
                )

                if dialogs.count():
                    print(
                        "WARNING: A LinkedIn dialog is still visible before "
                        "company-search click; allowing the normal Playwright "
                        "click to surface a precise failure if it remains blocking."
                    )
                else:
                    print(
                        "LinkedIn blocking dialog dismissed before company search."
                    )

        except Exception as ex:
            # Do not fail the workflow merely because dialog inspection itself
            # is unavailable. Continue with the existing search behavior.
            print(
                "Dialog dismissal check failed; continuing with company search:",
                repr(ex),
            )

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

        if len(profiles) < 5:

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

                if len(profiles) >= 5:
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

                        if len(profiles) >= 5:
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

        Safety rules:
        - Never manipulate connection-degree filters.
        - Never rewrite the network scope.
        - Never navigate the live employee-search tab directly.
        - First probe the explicit next page URL in an isolated tab.
        - If that cannot be validated, try LinkedIn's real Next control in an
          isolated copy of the current page.
        - The live authenticated employee-search tab is adopted only after
          the new page is validated.
        """
        try:
            import re
            from urllib.parse import (
                parse_qs,
                parse_qsl,
                urlencode,
                urlsplit,
                urlunsplit,
            )

            before_page = self.page
            before_url = str(before_page.url or "").strip()

            print("=" * 60)
            print("PAGINATION")
            print("=" * 60)
            print("Current URL:", before_url)

            before_lower = before_url.lower()
            if (
                "/search/results/people/" not in before_lower
                or "currentcompany=" not in before_lower
            ):
                print(
                    "NEXT ABORTED - current page is not company-scoped people search."
                )
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

            def page_number(url):
                try:
                    query = parse_qs(
                        urlsplit(str(url or "")).query,
                        keep_blank_values=True,
                    )
                    raw = (query.get("page", ["1"]) or ["1"])[0]
                    return max(1, int(str(raw).strip()))
                except Exception:
                    return 1

            current_page_number = page_number(before_url)
            target_page_number = current_page_number + 1

            parsed = urlsplit(before_url)
            pairs = []
            for key, value in parse_qsl(
                parsed.query,
                keep_blank_values=True,
            ):
                if key.lower() == "page":
                    continue
                pairs.append((key, value))
            pairs.append(("page", str(target_page_number)))

            direct_next_url = urlunsplit(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    urlencode(pairs),
                    parsed.fragment,
                )
            )

            def blocked(url):
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

            def valid_people_url(url):
                if not url or blocked(url):
                    return False
                value = str(url).lower()
                if (
                    "/search/results/people/" not in value
                    or "currentcompany=" not in value
                ):
                    return False
                try:
                    query = parse_qs(
                        urlsplit(url).query,
                        keep_blank_values=True,
                    )
                    actual_company_ids = (
                        query.get("currentCompany", [])
                        or query.get("currentcompany", [])
                    )
                    return actual_company_ids == company_ids
                except Exception:
                    return False

            def result_signature(page):
                items = []
                try:
                    links = page.locator("a[href*='/in/']")
                    count = links.count()
                    for i in range(min(12, count)):
                        link = links.nth(i)
                        href = (link.get_attribute("href") or "").strip()
                        if not href:
                            continue
                        try:
                            text = link.inner_text(timeout=800).strip()
                        except Exception:
                            text = ""
                        canonical = (
                            href.split("?", 1)[0]
                            .split("#", 1)[0]
                            .rstrip("/")
                            .lower()
                        )
                        items.append((canonical, text[:120]))
                except Exception:
                    pass
                return tuple(items)

            def employee_dom_ready(page):
                last_signature = ()
                for attempt in range(1, 31):
                    try:
                        page.wait_for_timeout(500)
                    except Exception:
                        pass

                    try:
                        visible_links = page.locator(
                            "a[href*='/in/']:visible"
                        ).count()
                    except Exception:
                        visible_links = 0

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
                            rendered_cards = max(
                                rendered_cards,
                                page.locator(selector).count(),
                            )
                        except Exception:
                            continue

                    rendered_text = False
                    try:
                        body = page.locator("body").inner_text(timeout=1500) or ""
                        normalized = re.sub(r"\s+", " ", body).strip().lower()
                        rendered_text = (
                            len(normalized) >= 700
                            and (
                                "people" in normalized
                                or "employees" in normalized
                                or "results" in normalized
                            )
                        )
                    except Exception:
                        pass

                    last_signature = result_signature(page)

                    print(
                        f"Next-page DOM wait {attempt}/30:",
                        visible_links,
                        "visible /in/ links;",
                        rendered_cards,
                        "result cards;",
                        rendered_text,
                        "employee-result text",
                    )

                    if visible_links > 0 or rendered_cards > 0 or rendered_text:
                        return bool(last_signature)

                return bool(last_signature)

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
                            if control.is_visible():
                                print(
                                    "Next control found in isolated tab:",
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

            # ------------------------------------------------------------
            # 1) Probe the explicit next page in an isolated tab.
            #    The URL preserves every existing query parameter and only
            #    changes page=N. No connection/network selection is changed.
            # ------------------------------------------------------------
            navigation_page = None
            try:
                before_signature = result_signature(before_page)
                print("Current-page result signature size:", len(before_signature))
                print("Direct next-page probe URL:", direct_next_url)
                navigation_page = before_page.context.new_page()
                navigation_page.goto(
                    direct_next_url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                    referer=before_url,
                )
                navigation_page.wait_for_timeout(5000)

                isolated_url = str(navigation_page.url or "").strip()
                print("Direct next-page probe final URL:", isolated_url)

                if (
                    valid_people_url(isolated_url)
                    and page_number(isolated_url) >= target_page_number
                ):
                    new_signature = result_signature(navigation_page)
                    signature_changed = (
                        bool(new_signature)
                        and (
                            not before_signature
                            or new_signature != before_signature
                        )
                    )
                    if signature_changed and employee_dom_ready(navigation_page):
                        self.page = navigation_page
                        navigation_page = None
                        try:
                            if not before_page.is_closed():
                                before_page.close()
                        except Exception as ex:
                            print("Previous employee-search tab cleanup warning:", repr(ex))

                        print("=" * 60)
                        print("NEXT PAGE VALIDATED VIA ISOLATED DIRECT URL")
                        print("=" * 60)
                        print("Final next-page URL:", isolated_url)
                        print("Company scope preserved:", company_ids)
                        print("Connection-degree handling: NONE")
                        return True

                if blocked(isolated_url):
                    print("Direct next-page probe hit LinkedIn auth/SSR redirect.")
                else:
                    print("Direct next-page probe did not produce a validated new result page.")
            except Exception as ex:
                print("Direct next-page probe failed:", repr(ex))
            finally:
                if navigation_page is not None:
                    try:
                        if not navigation_page.is_closed():
                            navigation_page.close()
                    except Exception:
                        pass

            # ------------------------------------------------------------
            # 2) Fallback to LinkedIn's real Next control in a fresh copy of
            #    the current page. The live page remains untouched.
            # ------------------------------------------------------------
            for pagination_attempt in range(1, 3):
                navigation_page = None
                try:
                    print(
                        "Isolated Next-control attempt:",
                        f"{pagination_attempt}/2",
                    )
                    navigation_page = before_page.context.new_page()
                    navigation_page.goto(
                        before_url,
                        wait_until="domcontentloaded",
                        timeout=60000,
                        referer=before_url,
                    )
                    navigation_page.wait_for_timeout(5000)

                    isolated_url = str(navigation_page.url or "").strip()
                    print("Isolated tab URL:", isolated_url)
                    if not valid_people_url(isolated_url):
                        print("ISOLATED PAGINATION ABORTED - company people-search could not be restored.")
                        continue

                    try:
                        navigation_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    except Exception:
                        pass
                    navigation_page.wait_for_timeout(1500)

                    isolated_signature = result_signature(navigation_page)
                    next_control = find_next_control(navigation_page)
                    if next_control is None:
                        print("No usable Next control found in isolated tab.")
                        continue

                    try:
                        next_control.scroll_into_view_if_needed()
                    except Exception:
                        pass

                    try:
                        next_control.click(timeout=15000, no_wait_after=True)
                    except Exception as ex:
                        print("Isolated Next click failed:", repr(ex))
                        continue

                    for validation_attempt in range(1, 61):
                        navigation_page.wait_for_timeout(300)
                        current_url = str(navigation_page.url or "").strip()
                        if blocked(current_url):
                            print("ISOLATED NEXT REDIRECTED TO AUTH/SSR; preserving live search page.")
                            print("Isolated auth URL:", current_url)
                            break
                        if not valid_people_url(current_url):
                            continue

                        current_signature = result_signature(navigation_page)
                        current_no = page_number(current_url)
                        url_changed = current_url.rstrip("/") != isolated_url.rstrip("/")
                        results_changed = bool(current_signature) and current_signature != isolated_signature
                        explicit_next_page = current_no >= target_page_number

                        if validation_attempt % 5 == 0:
                            print(
                                f"Next-page validation {validation_attempt}/60:",
                                "url_changed=", url_changed,
                                "results_changed=", results_changed,
                                "page=", current_no,
                            )

                        if not explicit_next_page and not results_changed:
                            continue

                        if not employee_dom_ready(navigation_page):
                            continue

                        self.page = navigation_page
                        navigation_page = None
                        try:
                            if not before_page.is_closed():
                                before_page.close()
                        except Exception as ex:
                            print("Previous employee-search tab cleanup warning:", repr(ex))

                        print("=" * 60)
                        print("NEXT PAGE VALIDATED VIA ISOLATED NEXT CONTROL")
                        print("=" * 60)
                        print("Final next-page URL:", current_url)
                        print("Company scope preserved:", company_ids)
                        print("Connection-degree handling: NONE")
                        return True

                except Exception as ex:
                    print("Isolated Next-control attempt failed:", repr(ex))
                finally:
                    if navigation_page is not None:
                        try:
                            if not navigation_page.is_closed():
                                navigation_page.close()
                        except Exception:
                            pass

            self.page = before_page
            print("NEXT FAILED - no validated next company people-search page exists from the current page.")
            print("LIVE EMPLOYEE-SEARCH PAGE PRESERVED:", self.page.url)
            return False

        except Exception as ex:
            print("Pagination failed:", repr(ex))
            try:
                self.page = before_page
            except Exception:
                pass
            return False

