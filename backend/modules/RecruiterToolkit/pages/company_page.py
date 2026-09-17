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
        LinkedIn sometimes exposes the employee search as a canned URL
        containing network=["F"]. That is a first-degree network filter.

        We preserve currentCompany but remove the canned network/origin
        parameters so the company search is not restricted to first-degree
        connections.

        We NEVER construct a generic people search.
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

        def is_bad_url(url):
            if not url:
                return True

            lower = url.lower()

            if is_people_url(url):
                return False

            bad_parts = (
                "/login",
                "/authwall",
                "/checkpoint",
                "/uas/login",
                "/signup",
                "/ssr-login",
            )

            if any(part in lower for part in bad_parts):
                return True

            return True

        def company_ids(url):
            try:
                from urllib.parse import urlsplit, parse_qs

                parsed = urlsplit(url)

                query = parse_qs(
                    parsed.query,
                    keep_blank_values=True
                )

                return query.get(
                    "currentCompany",
                    []
                )

            except Exception:
                return []

        def clean_people_search_url(url):
            """
            Preserve:
                currentCompany

            Remove canned search restrictions:
                network
                origin
                spellCorrectionEnabled
                prioritizeMessage

            Preserve other LinkedIn search parameters when present.
            """

            from urllib.parse import (
                urlsplit,
                urlunsplit,
                parse_qsl,
                urlencode,
            )

            parsed = urlsplit(url)

            pairs = parse_qsl(
                parsed.query,
                keep_blank_values=True
            )

            blocked = {
                "network",
                "origin",
                "spellCorrectionEnabled",
                "prioritizeMessage",
            }

            cleaned_pairs = [
                (key, value)
                for key, value in pairs
                if key not in blocked
            ]

            # currentCompany is mandatory.
            has_company = any(
                key.lower() == "currentcompany"
                for key, _ in cleaned_pairs
            )

            if not has_company:
                return ""

            query = urlencode(
                cleaned_pairs,
                doseq=True
            )

            return urlunsplit(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    query,
                    parsed.fragment,
                )
            )

        # --------------------------------------------------------
        # CASE 1:
        # The company click already landed directly on the people
        # search page.
        # --------------------------------------------------------

        if is_people_url(current_url):

            ids = company_ids(current_url)

            print("=" * 60)
            print("COMPANY PEOPLE-SEARCH PAGE ALREADY OPEN")
            print("=" * 60)

            print("Company scope:", ids)

            clean_url = clean_people_search_url(
                current_url
            )

            if not clean_url:
                print(
                    "ERROR: Could not safely normalize company "
                    "people-search URL."
                )
                return False

            print("Original people-search URL:")
            print(current_url)

            print("Normalized people-search URL:")
            print(clean_url)

            if clean_url != current_url:
                print(
                    "Removing LinkedIn canned first-degree "
                    "network/origin filters."
                )

                try:
                    self.page.goto(
                        clean_url,
                        wait_until="domcontentloaded",
                        timeout=60000,
                    )

                    self.page.wait_for_timeout(
                        5000
                    )

                except Exception as ex:
                    print(
                        "Normalized people-search navigation failed:",
                        repr(ex)
                    )

                    # Safe fallback:
                    # change the browser URL without constructing a
                    # different search.
                    try:
                        self.page.evaluate(
                            """
                            (url) => {
                                window.history.replaceState(
                                    {},
                                    '',
                                    url
                                );
                            }
                            """,
                            clean_url,
                        )

                        self.page.reload(
                            wait_until="domcontentloaded",
                            timeout=60000,
                        )

                        self.page.wait_for_timeout(
                            5000
                        )

                    except Exception as fallback_ex:
                        print(
                            "Normalized people-search fallback failed:",
                            repr(fallback_ex)
                        )
                        return False

            final_url = str(
                self.page.url or ""
            ).strip()

            print(
                "Final employee-search URL:",
                final_url
            )

            if not is_people_url(final_url):
                print(
                    "ERROR: Normalized URL did not remain "
                    "company-scoped people search."
                )
                return False

            final_ids = company_ids(
                final_url
            )

            if ids and final_ids != ids:
                print(
                    "ERROR: currentCompany changed during normalization."
                )
                print(
                    "Expected:",
                    ids
                )
                print(
                    "Actual:",
                    final_ids
                )
                return False

            print("=" * 60)
            print("COMPANY PEOPLE SEARCH READY")
            print("=" * 60)

            print(
                "Connection-degree filter:",
                "NOT APPLIED"
            )

            print(
                "Company scope preserved:",
                final_ids
            )

            return True

        # --------------------------------------------------------
        # CASE 2:
        # We are still on the company page.
        #
        # Find LinkedIn's own currentCompany people-search link.
        # --------------------------------------------------------

        links = self.page.locator(
            "a[href*='/search/results/people/']"
        )

        count = links.count()

        print(
            "People-search links found:",
            count
        )

        selected = None
        selected_href = ""

        selected_company_ids = company_ids(
            current_url
        )

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

                print(
                    "Selected LinkedIn employee-search link:"
                )
                print(
                    selected_href
                )

                break

            except Exception as ex:
                print(
                    "Employee-search link inspection failed:",
                    repr(ex)
                )

        if selected is None:
            print(
                "No valid LinkedIn currentCompany "
                "employee-search link found."
            )

            return False

        # --------------------------------------------------------
        # Normalize the LinkedIn-provided href before clicking.
        # --------------------------------------------------------

        normalized_href = clean_people_search_url(
            selected_href
        )

        if not normalized_href:
            print(
                "ERROR: Employee link could not be safely normalized."
            )
            return False

        print(
            "Normalized employee-search href:"
        )
        print(
            normalized_href
        )

        try:
            selected.evaluate(
                """
                (el, url) => {
                    el.setAttribute('href', url);
                }
                """,
                normalized_href,
            )

            selected.click(
                timeout=15000
            )

            self.page.wait_for_timeout(
                5000
            )

        except Exception as ex:
            print(
                "Employee-search click failed:",
                repr(ex)
            )
            return False

        final_url = str(
            self.page.url or ""
        ).strip()

        print(
            "URL after employee-search click:",
            final_url
        )

        if not is_people_url(final_url):
            print(
                "Employee-search navigation did not produce "
                "a valid company-scoped people search."
            )

            return False

        final_ids = company_ids(
            final_url
        )

        if (
            selected_company_ids
            and final_ids != selected_company_ids
        ):
            print(
                "ERROR: Company scope changed."
            )

            return False

        # If LinkedIn reinserted network=F after the click,
        # normalize the resulting URL one more time.
        final_clean = clean_people_search_url(
            final_url
        )

        if (
            final_clean
            and final_clean != final_url
        ):

            print(
                "LinkedIn restored canned network/origin parameters."
            )

            print(
                "Removing them from final URL."
            )

            try:
                self.page.goto(
                    final_clean,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

                self.page.wait_for_timeout(
                    5000
                )

            except Exception as ex:
                print(
                    "Final URL normalization failed:",
                    repr(ex)
                )
                return False

        final_url = str(
            self.page.url or ""
        ).strip()

        if not is_people_url(final_url):
            print(
                "ERROR: Final page is no longer company-scoped people search."
            )
            return False

        print("=" * 60)
        print("COMPANY PEOPLE SEARCH READY")
        print("=" * 60)

        print(
            "Final URL:",
            final_url
        )

        print(
            "Connection-degree filter:",
            "NOT APPLIED"
        )

        print(
            "Company scope:",
            company_ids(final_url)
        )

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
        Extract employee result cards from the current company-scoped
        LinkedIn people-search page.

        Rules:

        1. Company scope is inherited from currentCompany.
        2. Requested location is a hard result-card filter.
        3. 1st/2nd/3rd connection degree is NOT inspected.
        4. Mutual-connection /in/ links are not independently treated
           as employees when a result-card container is available.
        5. If LinkedIn changes its result-card DOM, use a broader
           location-aware fallback.
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

        def normalize_text(value):
            if not value:
                return ""

            value = (
                str(value)
                .replace("\xa0", " ")
                .replace("\n", " ")
                .replace("\r", " ")
            )

            return re.sub(
                r"\s+",
                " ",
                value
            ).strip().lower()

        def canonical_profile_url(href):
            if not href:
                return ""

            value = str(
                href
            ).strip()

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
        )

        location_tokens = [
            token
            for token in re.findall(
                r"[a-z0-9]+",
                requested_location
            )
            if len(token) >= 3
        ]

        # --------------------------------------------------------
        # Wait for LinkedIn's current result DOM.
        # --------------------------------------------------------

        try:
            self.page.wait_for_timeout(
                2500
            )
        except Exception:
            pass

        # --------------------------------------------------------
        # Scroll the search result area once.
        #
        # This helps LinkedIn finish rendering virtualized results.
        # --------------------------------------------------------

        try:
            self.page.mouse.wheel(
                0,
                1200
            )

            self.page.wait_for_timeout(
                1500
            )

        except Exception:
            pass

        # --------------------------------------------------------
        # Determine the result area.
        # --------------------------------------------------------

        search_area = None

        search_area_selectors = (
            "main:visible",
            "div.scaffold-finite-scroll__content:visible",
            "div.search-results-container:visible",
            "div[role='main']:visible",
        )

        for selector in search_area_selectors:

            try:
                candidate = (
                    self.page
                    .locator(selector)
                    .first
                )

                if (
                    candidate.count()
                    and candidate.is_visible()
                ):

                    search_area = candidate

                    print(
                        "Using employee search area:",
                        selector
                    )

                    break

            except Exception as ex:
                print(
                    "Search-area inspection failed:",
                    selector,
                    repr(ex)
                )

        link_scope = (
            search_area
            if search_area is not None
            else self.page
        )

        # --------------------------------------------------------
        # Get visible profile links.
        # --------------------------------------------------------

        try:
            links = link_scope.locator(
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

            # One additional render retry.
            try:
                self.page.wait_for_timeout(
                    5000
                )

                links = link_scope.locator(
                    "a[href*='/in/']:visible"
                )

                total_links = links.count()

                print(
                    "Visible /in/ links after render retry:",
                    total_links
                )

            except Exception as ex:
                print(
                    "Profile-link render retry failed:",
                    repr(ex)
                )

        if total_links == 0:
            print(
                "No visible employee profile links "
                "on this page."
            )

            return profiles

        # --------------------------------------------------------
        # Candidate records.
        # --------------------------------------------------------

        cards = {}
        fallback = []

        for index in range(total_links):

            try:

                link = links.nth(index)

                href = canonical_profile_url(
                    link.get_attribute("href")
                )

                if not href:
                    continue

                anchor_text = ""

                try:
                    anchor_text = (
                        link
                        .inner_text(timeout=2000)
                        .strip()
                    )
                except Exception:
                    pass

                info = link.evaluate(
                    """
                    (el) => {

                        function meaningfulContainer(node) {

                            if (!node) {
                                return false;
                            }

                            const tag =
                                (node.tagName || '').toLowerCase();

                            const cls =
                                (node.className || '')
                                .toString()
                                .toLowerCase();

                            const id =
                                (node.id || '')
                                .toString()
                                .toLowerCase();

                            return (
                                tag === 'li' ||
                                cls.includes('entity-result') ||
                                cls.includes('reusable-search__result') ||
                                cls.includes('search-result') ||
                                cls.includes('search-results__result') ||
                                id.includes('search-result')
                            );
                        }

                        let node = el;
                        let container = null;

                        for (
                            let i = 0;
                            i < 12 && node;
                            i++,
                            node = node.parentElement
                        ) {

                            if (
                                meaningfulContainer(node)
                            ) {

                                container = node;
                                break;
                            }
                        }

                        if (!container) {

                            // Broader fallback:
                            // find an ancestor whose rendered text
                            // is substantially larger than the name
                            // and therefore likely represents a card.

                            node = el;

                            for (
                                let i = 0;
                                i < 10 && node;
                                i++,
                                node = node.parentElement
                            ) {

                                const text =
                                    (node.innerText || '')
                                    .trim();

                                if (
                                    text.length >= 80 &&
                                    text.length <= 5000
                                ) {

                                    container = node;
                                    break;
                                }
                            }
                        }

                        if (!container) {

                            return {
                                has_container: false,
                                container_key: '',
                                container_text:
                                    el.innerText || '',
                                anchor_index: -1
                            };
                        }

                        const visibleAnchors =
                            Array.from(
                                container.querySelectorAll(
                                    "a[href*='/in/']"
                                )
                            ).filter(a => {

                                const r =
                                    a.getBoundingClientRect();

                                return (
                                    r.width > 0 &&
                                    r.height > 0
                                );
                            });

                        const anchorIndex =
                            visibleAnchors.indexOf(el);

                        const key =
                            container.getAttribute(
                                'data-chameleon-result-urn'
                            ) ||
                            container.getAttribute(
                                'data-view-name'
                            ) ||
                            container.getAttribute(
                                'data-id'
                            ) ||
                            (
                                'container:' +
                                Array.from(
                                    document.querySelectorAll(
                                        'li, div'
                                    )
                                ).indexOf(container)
                            );

                        return {
                            has_container: true,
                            container_key: key,
                            container_text:
                                container.innerText || '',
                            anchor_index:
                                anchorIndex
                        };
                    }
                    """
                )

                card_text = str(
                    info.get("container_text")
                    or anchor_text
                    or ""
                ).strip()

                normalized_card_text = normalize_text(
                    card_text
                )

                # ------------------------------------------------
                # HARD LOCATION FILTER
                # ------------------------------------------------

                location_match = False

                if requested_location:

                    if (
                        requested_location
                        in normalized_card_text
                    ):
                        location_match = True

                    elif location_tokens:

                        location_match = all(
                            token in normalized_card_text
                            for token in location_tokens
                        )

                if not location_match:

                    print(
                        "SKIP outside requested location:",
                        href,
                        "| location:",
                        location,
                        "| text:",
                        card_text[:250],
                    )

                    continue

                record = {
                    "url": href,
                    "anchor_text": anchor_text,
                    "card_text": card_text,
                    "anchor_index": int(
                        info.get(
                            "anchor_index",
                            -1
                        )
                    ),
                    "dom_index": index,
                }

                if info.get(
                    "has_container"
                ):

                    key = str(
                        info.get(
                            "container_key",
                            ""
                        )
                    )

                    if key:

                        existing = cards.get(
                            key
                        )

                        if (
                            existing is None
                            or record["anchor_index"]
                            < existing["anchor_index"]
                        ):

                            cards[key] = record

                else:

                    fallback.append(
                        record
                    )

            except Exception as ex:

                print(
                    "Profile-card inspection failed:",
                    repr(ex)
                )

        selected = list(
            cards.values()
        )

        # --------------------------------------------------------
        # Broad fallback.
        #
        # If LinkedIn does not expose recognizable result-card
        # containers, use location-aware ancestor text.
        #
        # We still reject bare name-only links.
        # --------------------------------------------------------

        if not selected:

            print(
                "No recognizable result-card containers found."
            )

            print(
                "Using broader location-aware fallback."
            )

            selected = []

            seen = set()

            for record in fallback:

                url = record["url"]

                if url in seen:
                    continue

                text = normalize_text(
                    record["card_text"]
                )

                if len(text) < 40:
                    continue

                if (
                    requested_location
                    and requested_location
                    not in text
                ):

                    if not (
                        location_tokens
                        and all(
                            token in text
                            for token in location_tokens
                        )
                    ):
                        continue

                seen.add(
                    url
                )

                selected.append(
                    record
                )

        # --------------------------------------------------------
        # Deduplicate.
        # --------------------------------------------------------

        unique = []

        seen_urls = set()

        for record in sorted(
            selected,
            key=lambda item: item["dom_index"]
        ):

            url = record["url"]

            if url in seen_urls:
                continue

            seen_urls.add(
                url
            )

            unique.append(
                record
            )

        print("=" * 60)
        print(
            "UNIQUE LOCATION-MATCHING EMPLOYEE CANDIDATES:",
            len(unique)
        )
        print("=" * 60)

        for record in unique:

            profiles.append(
                {
                    "full_name": (
                        record["anchor_text"]
                        or record["card_text"]
                    ),
                    "profile_url": record["url"],
                    "company": company,
                    "location": location,
                    "search_result_text": record["card_text"],
                }
            )

            print("-" * 60)

            print(
                "EMPLOYEE CANDIDATE:",
                record["url"]
            )

            print(
                "Primary anchor:",
                record["anchor_text"][:200]
            )

            print(
                "Result card:",
                record["card_text"][:500]
            )

            print(
                "Connection degree:",
                "IGNORED"
            )

        print(
            "EMPLOYEE PROFILES EXTRACTED:",
            len(profiles)
        )

        return profiles


    def next_page(self):
        """
        Move to the next company-scoped LinkedIn people-search page.

        Success requires:

        1. Current page is company-scoped people search.
        2. A real Next control exists.
        3. Next changes the search state.
        4. LinkedIn remains on the same currentCompany.
        5. The new page has rendered employee-result content.

        IMPORTANT:
        We never click Next again merely because the previous page
        had zero candidates.

        This prevents the workflow from clicking Next from an
        SSR/login page.
        """

        try:

            from urllib.parse import (
                urlsplit,
                parse_qs,
            )

            before_url = str(
                self.page.url or ""
            ).strip()

            before_lower = before_url.lower()

            print("=" * 60)
            print("PAGINATION")
            print("=" * 60)

            print(
                "Current URL:",
                before_url
            )

            if (
                "/search/results/people/"
                not in before_lower
                or "currentcompany="
                not in before_lower
            ):

                print(
                    "NEXT ABORTED - current page is not "
                    "company-scoped people search."
                )

                return False

            before_query = parse_qs(
                urlsplit(before_url).query
            )

            company_ids = (
                before_query.get(
                    "currentCompany",
                    []
                )
                or before_query.get(
                    "currentcompany",
                    []
                )
            )

            print(
                "Current company ID:",
                company_ids
            )

            # ----------------------------------------------------
            # Locate actual Next button.
            # ----------------------------------------------------

            next_control = None

            selectors = (
                "button[data-testid='pagination-controls-next-button-visible']:visible",
                "nav[aria-label*='Pagination' i] button:visible",
                "nav[aria-label*='Pagination' i] a:visible",
                "div.artdeco-pagination button:visible",
                "div.artdeco-pagination a:visible",
            )

            for selector in selectors:

                try:

                    controls = self.page.locator(
                        selector
                    )

                    count = controls.count()

                    for i in range(count):

                        control = controls.nth(i)

                        try:
                            text = (
                                control
                                .inner_text(
                                    timeout=1000
                                )
                                .strip()
                            )
                        except Exception:
                            text = ""

                        try:
                            aria = (
                                control
                                .get_attribute(
                                    "aria-label"
                                )
                                or ""
                            ).strip()
                        except Exception:
                            aria = ""

                        try:
                            title = (
                                control
                                .get_attribute(
                                    "title"
                                )
                                or ""
                            ).strip()
                        except Exception:
                            title = ""

                        label = " ".join(
                            x
                            for x in (
                                text,
                                aria,
                                title,
                            )
                            if x
                        ).lower()

                        if "next" not in label:
                            continue

                        try:
                            if control.is_disabled():
                                continue
                        except Exception:
                            pass

                        if not control.is_visible():
                            continue

                        next_control = control

                        print(
                            "Next control found:",
                            selector,
                            "[",
                            i,
                            "]"
                        )

                        print(
                            "Next text:",
                            text
                        )

                        print(
                            "Next aria:",
                            aria
                        )

                        break

                    if next_control is not None:
                        break

                except Exception as ex:

                    print(
                        "Next selector inspection failed:",
                        selector,
                        repr(ex)
                    )

            if next_control is None:

                print(
                    "No usable Next control found."
                )

                return False

            # ----------------------------------------------------
            # Snapshot current result state.
            # ----------------------------------------------------

            before_links = set()

            try:

                links = self.page.locator(
                    "a[href*='/in/']:visible"
                )

                for i in range(
                    min(
                        links.count(),
                        200
                    )
                ):

                    href = (
                        links
                        .nth(i)
                        .get_attribute("href")
                    )

                    if href and "/in/" in href.lower():

                        canonical = (
                            str(href)
                            .split("?", 1)[0]
                            .split("#", 1)[0]
                            .rstrip("/")
                            .lower()
                        )

                        before_links.add(
                            canonical
                        )

            except Exception as ex:

                print(
                    "Pre-next profile snapshot failed:",
                    repr(ex)
                )

            print(
                "Profiles before Next:",
                len(before_links)
            )

            # ----------------------------------------------------
            # Click Next.
            # ----------------------------------------------------

            try:

                next_control.scroll_into_view_if_needed()

            except Exception:
                pass

            try:

                next_control.click(
                    timeout=15000
                )

            except Exception as ex:

                print(
                    "Next click failed:",
                    repr(ex)
                )

                return False

            # ----------------------------------------------------
            # Wait for LinkedIn to change the URL.
            # ----------------------------------------------------

            changed_url = False

            for _ in range(40):

                self.page.wait_for_timeout(
                    250
                )

                current_url = str(
                    self.page.url or ""
                ).strip()

                if current_url != before_url:

                    changed_url = True
                    break

            current_url = str(
                self.page.url or ""
            ).strip()

            print(
                "URL after Next:",
                current_url
            )

            if not changed_url:

                print(
                    "NEXT FAILED - URL did not change."
                )

                return False

            current_lower = current_url.lower()

            # ----------------------------------------------------
            # Never accept login/authwall/SSR navigation.
            # ----------------------------------------------------

            bad_parts = (
                "/login",
                "/authwall",
                "/checkpoint",
                "/uas/login",
                "/signup",
                "/ssr-login",
            )

            if any(
                part in current_lower
                for part in bad_parts
            ):

                print(
                    "NEXT FAILED - LinkedIn redirected "
                    "to authentication/SSR page."
                )

                print(
                    "Authentication URL:",
                    current_url
                )

                return False

            # ----------------------------------------------------
            # Validate company people-search scope.
            # ----------------------------------------------------

            if (
                "/search/results/people/"
                not in current_lower
                or "currentcompany="
                not in current_lower
            ):

                print(
                    "NEXT FAILED - navigation left "
                    "company people-search."
                )

                return False

            current_query = parse_qs(
                urlsplit(current_url).query
            )

            current_company_ids = (
                current_query.get(
                    "currentCompany",
                    []
                )
                or current_query.get(
                    "currentcompany",
                    []
                )
            )

            if (
                company_ids
                and current_company_ids != company_ids
            ):

                print(
                    "NEXT FAILED - currentCompany changed."
                )

                print(
                    "Before:",
                    company_ids
                )

                print(
                    "After:",
                    current_company_ids
                )

                return False

            print(
                "Company scope preserved."
            )

            # ----------------------------------------------------
            # CRITICAL:
            #
            # URL change is NOT enough.
            #
            # Wait for actual employee result DOM.
            # ----------------------------------------------------

            rendered_profiles = 0

            for attempt in range(1, 21):

                try:

                    self.page.wait_for_timeout(
                        500
                    )

                    visible_links = self.page.locator(
                        "a[href*='/in/']:visible"
                    )

                    rendered_profiles = (
                        visible_links.count()
                    )

                except Exception:
                    rendered_profiles = 0

                print(
                    f"Result DOM wait {attempt}/20:",
                    rendered_profiles,
                    "visible /in/ links"
                )

                if rendered_profiles > 0:
                    break

                # Give LinkedIn a chance to finish virtualized rendering.
                try:

                    self.page.mouse.wheel(
                        0,
                        1200
                    )

                except Exception:
                    pass

            # ----------------------------------------------------
            # Page changed but no employee result DOM appeared.
            #
            # Do NOT treat it as a valid page and do NOT allow
            # another pagination click.
            # ----------------------------------------------------

            if rendered_profiles == 0:

                print(
                    "=" * 60
                )

                print(
                    "NEXT REJECTED"
                )

                print(
                    "URL changed but LinkedIn did not "
                    "render employee profile results."
                )

                print(
                    "Current URL:",
                    current_url
                )

                try:

                    body_text = (
                        self.page
                        .locator("body")
                        .inner_text()
                    )

                    print(
                        "Current page text length:",
                        len(body_text)
                    )

                    print(
                        "Current page text preview:",
                        body_text[:1000]
                    )

                except Exception as ex:

                    print(
                        "Could not inspect empty result page:",
                        repr(ex)
                    )

                return False

            # ----------------------------------------------------
            # Check whether the result set actually changed.
            #
            # Do NOT require every profile to be new because LinkedIn
            # may preserve a small amount of DOM during rendering.
            # The presence of a rendered result set is the important
            # condition.
            # ----------------------------------------------------

            after_links = set()

            try:

                visible_links = self.page.locator(
                    "a[href*='/in/']:visible"
                )

                for i in range(
                    min(
                        visible_links.count(),
                        200
                    )
                ):

                    href = (
                        visible_links
                        .nth(i)
                        .get_attribute("href")
                    )

                    if href and "/in/" in href.lower():

                        canonical = (
                            str(href)
                            .split("?", 1)[0]
                            .split("#", 1)[0]
                            .rstrip("/")
                            .lower()
                        )

                        after_links.add(
                            canonical
                        )

            except Exception:
                pass

            print(
                "Profiles after Next:",
                len(after_links)
            )

            print(
                "New profile URLs:",
                len(
                    after_links - before_links
                )
            )

            print("=" * 60)
            print(
                "NEXT PAGE VALIDATED"
            )
            print("=" * 60)

            print(
                "Same company people-search:",
                True
            )

            print(
                "Rendered employee results:",
                rendered_profiles
            )

            return True

        except Exception as ex:

            print(
                "Pagination failed:",
                repr(ex)
            )

            return False

