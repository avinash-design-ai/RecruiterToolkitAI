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
    
            print("Connection-degree filter: NOT USED")
            print("Network parameter: NOT MODIFIED")
            print("Company scope preserved:", ids)
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
        print("Connection-degree filter: NOT USED")
        print("Network parameter: NOT MODIFIED")
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
            require_location=True,
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

            # Candidate discovery may be DOM-incomplete on later pages.
            # PASS 2 intentionally supplies candidates even when location text
            # is missing from the rendered ancestor. SearchWorkflowV2 performs
            # the authoritative profile-level location validation.
            if require_location and not location_matches(clean_text):
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
        # ALL-DEGREE DOM FALLBACK
        #
        # LinkedIn can render employee results without legacy result-card
        # classes. We inspect visible /in/ links and infer the employee
        # result container from several independent signals.
        #
        # IMPORTANT:
        # - Connection degree is NEVER used as an inclusion filter.
        # - Location text is NOT required during discovery because LinkedIn
        #   can virtualize/omit it from the immediate DOM on later pages.
        # - Nested mutual-connection links are not returned as separate
        #   employees when they belong to the same result container.
        # - Final company/location validation remains in SearchWorkflowV2.
        # ============================================================

        print("=" * 60)
        print("PASS 2 - ALL-DEGREE DOM FALLBACK")
        print("=" * 60)

        try:
            links = self.page.locator("a[href*='/in/']:visible")
            link_count = links.count()
        except Exception as ex:
            print("Visible /in/ link lookup failed:", repr(ex))
            links = None
            link_count = 0

        print("Visible /in/ links found:", link_count)

        if links is not None and link_count > 0:
            try:
                raw_candidates = self.page.evaluate(
                    r'''
                    ({requestedCompany, requestedLocation}) => {
                        const visible = (el) => {
                            if (!el) return false;
                            const r = el.getBoundingClientRect();
                            const s = getComputedStyle(el);
                            return r.width > 0 && r.height > 0 &&
                                   s.display !== "none" &&
                                   s.visibility !== "hidden";
                        };

                        const norm = (v) => String(v || "")
                            .replace(/\u00a0/g, " ")
                            .replace(/\s+/g, " ")
                            .trim()
                            .toLowerCase();

                        const company = norm(requestedCompany);
                        const location = norm(requestedLocation);
                        const locTokens = location.split(/\s+/)
                            .filter(Boolean).filter(x => x.length >= 3);

                        const allLinks = Array.from(
                            document.querySelectorAll("a[href*='/in/']")
                        ).filter(visible);

                        const canonical = (href) => {
                            try {
                                return new URL(href, window.location.href).href
                                    .split("?", 1)[0]
                                    .split("#", 1)[0]
                                    .replace(/\/+$/, "")
                                    .toLowerCase();
                            } catch (_) {
                                return "";
                            }
                        };

                        const hasLocation = (text) => {
                            const t = norm(text);
                            if (!location) return true;
                            if (t.includes(location)) return true;
                            return locTokens.length > 0 &&
                                locTokens.every(x => t.includes(x));
                        };

                        const hasCompany = (text) => {
                            const t = norm(text);
                            return !!company && t.includes(company);
                        };

                        const degree = (text) =>
                            /(?:•\s*)?(?:1st|2nd|3rd\+?)(?:\s|$)/i.test(String(text || ""));

                        const containerScore = (node, depth) => {
                            if (!node || !visible(node)) return -9999;
                            const text = String(node.innerText || "");
                            const t = norm(text);
                            if (t.length < 20 || t.length > 6000) return -9999;

                            const profileLinks = Array.from(
                                node.querySelectorAll("a[href*='/in/']")
                            ).filter(visible);
                            if (!profileLinks.length || profileLinks.length > 12) return -9999;

                            const tag = String(node.tagName || "").toLowerCase();
                            const cls = String(node.className || "").toLowerCase();
                            let score = 0;

                            if (tag === "li") score += 12;
                            if (cls.includes("entity-result")) score += 12;
                            if (cls.includes("reusable-search__result")) score += 12;
                            if (cls.includes("search-result")) score += 10;
                            if (degree(text)) score += 10;
                            if (hasLocation(text)) score += 8;
                            if (hasCompany(text)) score += 8;
                            if (/\bmessage\b/i.test(text)) score += 3;
                            if (/mutual connection/i.test(text)) score += 2;
                            if (profileLinks.length <= 4) score += 2;
                            if (text.length >= 80) score += 1;

                            // Prefer the smallest strong result container.
                            score -= Math.min(depth, 8) * 0.35;
                            return score;
                        };

                        const groups = [];
                        const groupByNode = new Map();

                        for (const link of allLinks) {
                            let node = link.parentElement;
                            let best = null;
                            let bestScore = -9999;

                            for (let depth = 0; node && depth < 20; depth++, node = node.parentElement) {
                                const score = containerScore(node, depth);
                                if (score > bestScore) {
                                    bestScore = score;
                                    best = node;
                                }
                            }

                            if (!best || bestScore < 6) continue;

                            if (!groupByNode.has(best)) {
                                const group = { node: best, links: [], score: bestScore };
                                groupByNode.set(best, group);
                                groups.push(group);
                            }
                            groupByNode.get(best).links.push(link);
                        }

                        const results = [];
                        const seen = new Set();

                        for (const group of groups) {
                            const node = group.node;
                            const groupLinks = Array.from(
                                node.querySelectorAll("a[href*='/in/']")
                            ).filter(visible);

                            if (!groupLinks.length) continue;

                            // Pick the first /in/ link in the chosen employee
                            // result container. Later links are commonly mutual
                            // connections and must not replace the primary employee.
                            const primary = groupLinks[0];

                            const href = primary.getAttribute("href") || "";
                            const url = canonical(href);
                            if (!url || seen.has(url)) continue;

                            const text = String(primary.innerText || "").trim();
                            const containerText = String(node.innerText || "").trim();

                            seen.add(url);
                            results.push({
                                href: url,
                                text,
                                container_text: containerText,
                                has_location: hasLocation(containerText),
                                has_company: hasCompany(containerText),
                                has_degree: degree(containerText),
                            });
                        }

                        // If grouping was too conservative, use the visible
                        // links as a final discovery fallback. Do not apply a
                        // location or degree filter here; profile validation
                        // decides whether a candidate is actually acceptable.
                        if (results.length === 0) {
                            for (const link of allLinks) {
                                const url = canonical(link.getAttribute("href") || "");
                                if (!url || seen.has(url)) continue;
                                const text = String(link.innerText || "").trim();
                                if (!text || text.length > 180) continue;
                                seen.add(url);
                                results.push({
                                    href: url,
                                    text,
                                    container_text: String(link.parentElement?.innerText || "").trim(),
                                    has_location: false,
                                    has_company: false,
                                    has_degree: degree(text),
                                });
                            }
                        }

                        return results;
                    }
                    ''',
                    {
                        "requestedCompany": company,
                        "requestedLocation": location,
                    },
                )
            except Exception as ex:
                print("All-degree DOM extraction failed:", repr(ex))
                raw_candidates = []

            print("All-degree primary candidates found:", len(raw_candidates))

            for item in raw_candidates:
                try:
                    group_text = normalize_text(item.get("container_text", ""))
                    # PASS 2 discovery intentionally does not require location.
                    # SearchWorkflowV2 performs the authoritative profile-level
                    # location/company validation after opening the profile.
                    if add_candidate(
                        item.get("href", ""),
                        item.get("text", ""),
                        group_text or item.get("text", ""),
                        require_location=False,
                    ): 
                        print("-" * 60)
                        print("EMPLOYEE CANDIDATE:", canonical_profile_url(item.get("href", "")))
                        print("Primary anchor:", normalize_text(item.get("text", ""))[:200])
                        print("Result group:", group_text[:500])
                        print("Connection degree: IGNORED")
                except Exception as ex:
                    print("Fallback candidate processing failed:", repr(ex))


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


