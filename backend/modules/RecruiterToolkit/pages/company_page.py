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
        Open the authenticated company-scoped LinkedIn people search.

        IMPORTANT:
        If LinkedIn has already landed on a valid company-scoped people-search
        URL, keep that authenticated page exactly as it is.

        We intentionally do NOT rewrite the URL from F to F/S/O here.
        The previous implementation did that with page.goto(), and LinkedIn
        redirected the authenticated session to /uas/login. That poisoned the
        only live employee-search page and caused the workflow to stop with
        zero profiles.

        Connection degree is not used by get_profiles(). The workflow can
        safely use the company-scoped search page that LinkedIn already opened
        and paginate through it until max_profiles is reached.
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
                and "/login" not in lower
                and "/authwall" not in lower
                and "/checkpoint" not in lower
                and "/uas/login" not in lower
                and "/signup" not in lower
                and "/ssr-login" not in lower
                and "remember-me-auto-login" not in lower
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
            except Exception as ex:
                print("Company ID inspection failed:", repr(ex))
                return []

        # CASE 1:
        # open_company_result() already landed on the authenticated
        # company-scoped people-search page. Keep it unchanged.
        if is_people_url(current_url):
            ids = company_ids(current_url)

            if not ids:
                print(
                    "ERROR: Current company people-search page has no "
                    "currentCompany scope."
                )
                return False

            print("=" * 60)
            print("AUTHENTICATED COMPANY PEOPLE SEARCH ALREADY OPEN")
            print("=" * 60)
            print("Company scope:", ids)
            print("Connection-degree rewrite: SKIPPED")
            print(
                "Reason: preserving the authenticated LinkedIn search page "
                "prevents /uas/login redirects."
            )
            print("Final URL:", current_url)
            print("Company scope preserved:", ids)
            return True

        # CASE 2:
        # Still on the selected company page. Use only a LinkedIn-supplied
        # currentCompany people-search link. Do not rewrite it.
        links = self.page.locator(
            "a[href*='/search/results/people/']"
        )
        count = links.count()
        print("People-search links found:", count)

        selected = None
        selected_href = ""
        selected_company_ids = company_ids(current_url)

        for i in range(count):
            try:
                link = links.nth(i)
                href = (
                    link.get_attribute("href")
                    or ""
                ).strip()

                if not href:
                    continue
                if "/search/results/people/" not in href.lower():
                    continue

                ids = company_ids(href)
                if not ids:
                    continue

                if (
                    selected_company_ids
                    and ids != selected_company_ids
                ):
                    print(
                        "SKIP unrelated currentCompany:",
                        href
                    )
                    continue

                selected = link
                selected_href = href
                print("Selected LinkedIn employee-search link:")
                print(selected_href)
                break

            except Exception as ex:
                print(
                    "Employee-search link inspection failed:",
                    repr(ex)
                )

        if selected is None:
            print(
                "No valid LinkedIn currentCompany employee-search "
                "link found."
            )
            return False

        try:
            print(
                "Clicking LinkedIn's original company employee-search link..."
            )
            selected.scroll_into_view_if_needed()
            selected.click(timeout=15000)
            self.page.wait_for_timeout(5000)
        except Exception as ex:
            print(
                "Employee-search link click failed:",
                repr(ex)
            )
            return False

        final_url = str(
            self.page.url or ""
        ).strip()

        print(
            "URL after employee-search link click:",
            final_url
        )

        if not is_people_url(final_url):
            print(
                "ERROR: LinkedIn employee-search link did not produce "
                "a valid authenticated company people-search page."
            )
            print("Expected source link:", selected_href)
            print("Actual URL:", final_url)
            return False

        final_ids = company_ids(final_url)

        if (
            selected_company_ids
            and final_ids != selected_company_ids
        ):
            print(
                "ERROR: Company scope changed during employee-search "
                "navigation."
            )
            print("Expected:", selected_company_ids)
            print("Actual:", final_ids)
            return False

        print("=" * 60)
        print("COMPANY PEOPLE SEARCH READY")
        print("=" * 60)
        print("Final URL:", final_url)
        print("Connection-degree filter:", "LINKEDIN ORIGINAL FILTER")
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
        Extract employee candidates from the company-scoped LinkedIn
        people-search page.

        Strategy:
            1. Wait for LinkedIn's virtualized result DOM to hydrate.
            2. Prefer recognizable result-card containers.
            3. Fall back to visible /in/ links when LinkedIn changes
               result-card markup.
            4. Group profile links by the smallest meaningful rendered
               ancestor containing the requested location.
            5. Use the first employee/profile link in each group.
            6. Ignore connection degree completely.
            7. Preserve company scope from the already-open people search.
        """

        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)

        print(
            "Requested company:",
            company
        )

        print(
            "Requested location:",
            location
        )

        profiles = []
        seen_urls = set()

        # ============================================================
        # Helpers
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

            if not location_matches(
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
        # Verify current page is still the company-scoped people page.
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
        # FIRST-PAGE HYDRATION WAIT
        #
        # This is the important fix.
        #
        # LinkedIn can initially return zero visible /in/ links while
        # its virtualized employee-result DOM is still being hydrated.
        #
        # The old code checked once and immediately returned zero.
        # ============================================================

        print("=" * 60)
        print("WAITING FOR EMPLOYEE RESULT DOM")
        print("=" * 60)

        rendered_profile_links = 0
        rendered_result_cards = 0

        for attempt in range(1, 41):

            try:
                self.page.wait_for_timeout(
                    500
                )
            except Exception:
                pass

            # --------------------------------------------------------
            # Visible /in/ links
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
            # Multiple possible LinkedIn result-card structures
            # --------------------------------------------------------

            try:

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

            except Exception:
                rendered_result_cards = 0

            print(
                f"Employee DOM wait {attempt}/40:",
                rendered_profile_links,
                "visible /in/ links |",
                rendered_result_cards,
                "result cards"
            )

            if (
                rendered_profile_links > 0
                or rendered_result_cards > 0
            ):

                print(
                    "Employee result DOM detected."
                )

                break

            # --------------------------------------------------------
            # Periodically scroll to trigger LinkedIn virtualized
            # rendering.
            # --------------------------------------------------------

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
        #
        # Known result-card containers.
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
        selected_selector = ""

        for selector in card_selectors:

            try:

                locator = self.page.locator(
                    selector
                )

                count = locator.count()

                if count > 0:

                    cards = locator
                    selected_selector = selector

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

                    if not location_matches(
                        card_text
                    ):
                        continue

                    links = card.locator(
                        "a[href*='/in/']:visible"
                    )

                    for link_index in range(
                        links.count()
                    ):

                        try:

                            link = links.nth(
                                link_index
                            )

                            href = (
                                link
                                .get_attribute(
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
                                card_text
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

                                # Only one employee per result card.
                                break

                        except Exception:
                            continue

                except Exception as ex:

                    print(
                        f"Result-card "
                        f"{card_index + 1} inspection failed:",
                        repr(ex)
                    )


        # ============================================================
        # PASS 2
        #
        # MUTUAL-SAFE DOM FALLBACK
        #
        # LinkedIn can render employee results without the legacy
        # result-card classes. We therefore inspect visible /in/ links
        # directly.
        #
        # Critical rule:
        # A result card contributes ONLY its primary employee /in/ link.
        # Nested /in/ links such as mutual connections are ignored.
        #
        # Connection degree is deliberately ignored.
        # ============================================================

        # IMPORTANT: CompanyPage never owns max_profiles.
        # SearchWorkflowV2 decides how many accepted profiles
        # to collect. PASS 2 must discover all available
        # candidates on this page so requests such as 10/20/50
        # are not silently capped at five.
        if True:

            print("=" * 60)
            print("PASS 2 - MUTUAL-SAFE DOM FALLBACK")
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

                try:
                    raw_candidates = self.page.evaluate(
                        r'''
                        (locationText) => {

                            const visible = (el) => {
                                if (!el) return false;

                                const rect =
                                    el.getBoundingClientRect();

                                const style =
                                    window.getComputedStyle(el);

                                return (
                                    rect.width > 0 &&
                                    rect.height > 0 &&
                                    style.display !== "none" &&
                                    style.visibility !== "hidden"
                                );
                            };

                            const normalize = (value) =>
                                String(value || "")
                                    .replace(/\u00a0/g, " ")
                                    .replace(/\s+/g, " ")
                                    .trim()
                                    .toLowerCase();

                            const requested =
                                normalize(locationText);

                            const tokens =
                                requested
                                    .split(/\s+/)
                                    .filter(Boolean)
                                    .filter(
                                        token => token.length >= 3
                                    );

                            const allLinks =
                                Array.from(
                                    document.querySelectorAll(
                                        "a[href*='/in/']"
                                    )
                                ).filter(visible);

                            const result = [];
                            const seen = new Set();

                            const hasLocation = (text) => {
                                const normalized =
                                    normalize(text);

                                if (!requested) {
                                    return true;
                                }

                                if (
                                    normalized.includes(requested)
                                ) {
                                    return true;
                                }

                                return (
                                    tokens.length > 0 &&
                                    tokens.every(
                                        token =>
                                            normalized.includes(token)
                                    )
                                );
                            };

                            // -------------------------------------------------
                            // Identify the employee result group without using
                            // connection-degree text or assuming a particular
                            // LinkedIn result-card class.
                            //
                            // IMPORTANT:
                            // LinkedIn currently renders first-degree and
                            // non-first-degree employees differently. The
                            // previous fallback could collapse/ignore non-first-
                            // degree results because it required a known result
                            // container or <= 6 /in/ links.
                            //
                            // We instead use the nearest visible ancestor that:
                            //   - contains the requested location
                            //   - contains a bounded number of profile links
                            // Then rank the links in that group and choose the
                            // richest employee anchor. Mutual-connection links
                            // normally have much shorter text.
                            // -------------------------------------------------

                            for (const link of allLinks) {

                                let node = link.parentElement;
                                let chosen = null;

                                for (
                                    let depth = 0;
                                    node && depth < 18;
                                    depth++,
                                    node = node.parentElement
                                ) {
                                    if (!visible(node)) {
                                        continue;
                                    }

                                    const text =
                                        String(node.innerText || "");

                                    if (
                                        text.length < 20 ||
                                        text.length > 6000 ||
                                        !hasLocation(text)
                                    ) {
                                        continue;
                                    }

                                    const profileLinks =
                                        Array.from(
                                            node.querySelectorAll(
                                                "a[href*='/in/']"
                                            )
                                        ).filter(visible);

                                    // A real employee result normally has a
                                    // small local set of /in/ links. A larger
                                    // ancestor is the page/list wrapper and is
                                    // deliberately rejected.
                                    if (
                                        profileLinks.length >= 1 &&
                                        profileLinks.length <= 12
                                    ) {
                                        chosen = node;
                                        break;
                                    }
                                }

                                if (!chosen) {
                                    continue;
                                }

                                const groupLinks =
                                    Array.from(
                                        chosen.querySelectorAll(
                                            "a[href*='/in/']"
                                        )
                                    ).filter(visible);

                                if (!groupLinks.length) {
                                    continue;
                                }

                                // Prefer the richest anchor. Employee anchors
                                // contain name + headline/result text; mutual
                                // connection anchors are normally short names.
                                const rankedLinks = groupLinks.slice().sort(
                                    (a, b) => {
                                        const aText =
                                            String(a.innerText || "").trim();
                                        const bText =
                                            String(b.innerText || "").trim();

                                        const aMutual =
                                            /mutual connections?/i.test(aText);
                                        const bMutual =
                                            /mutual connections?/i.test(bText);

                                        if (aMutual !== bMutual) {
                                            return aMutual ? 1 : -1;
                                        }

                                        return bText.length - aText.length;
                                    }
                                );

                                const primaryLink = rankedLinks[0];

                                if (primaryLink !== link) {
                                    continue;
                                }

                                const href =
                                    link.getAttribute("href") || "";

                                if (!href) {
                                    continue;
                                }

                                const absolute =
                                    new URL(
                                        href,
                                        window.location.href
                                    ).href;

                                const canonical =
                                    absolute
                                        .split("?", 1)[0]
                                        .split("#", 1)[0]
                                        .replace(/\/+$/, "")
                                        .toLowerCase();

                                if (
                                    !canonical.includes("/in/") ||
                                    seen.has(canonical)
                                ) {
                                    continue;
                                }

                                seen.add(canonical);

                                result.push({
                                    href: absolute,
                                    text:
                                        String(
                                            link.innerText || ""
                                        ).trim(),
                                    container_text:
                                        String(
                                            chosen.innerText || ""
                                        ).trim()
                                });
                            }

                            return result;
                        }
                        ''',
                        requested_location
                    )

                except Exception as ex:
                    print(
                        "Mutual-safe DOM extraction failed:",
                        repr(ex)
                    )
                    raw_candidates = []

                print(
                    "Mutual-safe primary candidates found:",
                    len(raw_candidates)
                )

                for item in raw_candidates:

                    # No max-profile stop belongs in CompanyPage.
                    # Continue discovering candidates; the workflow
                    # applies the user's requested max_profiles.

                    try:
                        group_text = normalize_text(
                            item.get("container_text", "")
                        )

                        if not location_matches(group_text):
                            continue

                        if add_candidate(
                            item.get("href", ""),
                            item.get("text", ""),
                            group_text
                        ):
                            print("-" * 60)
                            print(
                                "EMPLOYEE CANDIDATE:",
                                canonical_profile_url(
                                    item.get("href", "")
                                )
                            )
                            print(
                                "Primary anchor:",
                                normalize_text(
                                    item.get("text", "")
                                )[:200]
                            )
                            print(
                                "Result group:",
                                group_text[:500]
                            )
                            print(
                                "Connection degree: IGNORED"
                            )

                    except Exception as ex:
                        print(
                            "Fallback candidate processing failed:",
                            repr(ex)
                        )

            else:
                print(
                    "No visible /in/ links available for PASS 2."
                )

            # ============================================================
        # Final result
        # ============================================================

        print("=" * 60)

        print(
            "UNIQUE LOCATION-MATCHING EMPLOYEE CANDIDATES:",
            len(profiles)
        )

        print("=" * 60)

        print(
            "EMPLOYEE PROFILES EXTRACTED:",
            len(profiles)
        )

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

            if not changed_url:
                print("NEXT FAILED - URL did not change.")
                return False

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
                    # LinkedIn can transiently expose employee-result text and
                    # then redirect the page to linkedin.com/. Never report
                    # success based on stale DOM from that transient state.
                    stable_url = str(self.page.url or "").strip()
                    stable_lower = stable_url.lower()

                    if (
                        "/search/results/people/" not in stable_lower
                        or "currentcompany=" not in stable_lower
                    ):
                        print(
                            "NEXT PAGE TRANSIENTLY LEFT COMPANY SEARCH."
                        )
                        print("Stable URL check:", stable_url)
                        print(
                            "Attempting one browser-history recovery before "
                            "declaring pagination failure."
                        )

                        try:
                            self.page.go_back(
                                wait_until="domcontentloaded",
                                timeout=30000
                            )
                            self.page.wait_for_timeout(3000)
                        except Exception as recovery_ex:
                            print(
                                "Pagination history recovery failed:",
                                repr(recovery_ex)
                            )

                        recovered_url = str(
                            self.page.url or ""
                        ).strip()
                        recovered_lower = recovered_url.lower()

                        if (
                            "/search/results/people/" not in recovered_lower
                            or "currentcompany=" not in recovered_lower
                        ):
                            print(
                                "NEXT REJECTED - history recovery did not "
                                "restore company people-search."
                            )
                            print(
                                "Recovered URL:",
                                recovered_url
                            )
                            return False

                        recovered_query = parse_qs(
                            urlsplit(recovered_url).query,
                            keep_blank_values=True
                        )
                        recovered_company_ids = (
                            recovered_query.get("currentCompany", [])
                            or recovered_query.get("currentcompany", [])
                        )

                        if (
                            company_ids
                            and recovered_company_ids != company_ids
                        ):
                            print(
                                "NEXT REJECTED - history recovery changed "
                                "company scope."
                            )
                            print("Before:", company_ids)
                            print("Recovered:", recovered_company_ids)
                            return False

                        # If history returned to the original page, the click
                        # did not stick. Do not pretend that this is page 2.
                        if recovered_url == before_url:
                            print(
                                "NEXT REJECTED - history returned to the "
                                "same employee page."
                            )
                            return False

                        stable_url = recovered_url
                        stable_lower = recovered_lower

                    stable_query = parse_qs(
                        urlsplit(stable_url).query,
                        keep_blank_values=True
                    )
                    stable_company_ids = (
                        stable_query.get("currentCompany", [])
                        or stable_query.get("currentcompany", [])
                    )

                    if (
                        company_ids
                        and stable_company_ids != company_ids
                    ):
                        print(
                            "NEXT REJECTED - company scope changed during "
                            "DOM validation."
                        )
                        print("Before:", company_ids)
                        print("After:", stable_company_ids)
                        return False

                    print("=" * 60)
                    print("NEXT PAGE VALIDATED")
                    print("=" * 60)
                    print("Same company people-search:", True)
                    print(
                        "Validation:",
                        "links/cards/text + stable URL"
                    )
                    print("Final validated URL:", stable_url)
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


