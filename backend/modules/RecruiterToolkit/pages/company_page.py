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
        Extract one employee candidate per LinkedIn result card.

        The important rule is that a result card has ONE primary employee
        profile link. Mutual connections or other nested /in/ links inside
        that same card are never emitted as separate candidates.

        Connection degree is deliberately ignored.
        Location remains a hard card-level filter.
        """
        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)
        print("Requested company:", company)
        print("Requested location:", location)

        profiles = []

        def normalize_text(value):
            if not value:
                return ""
            value = str(value).replace("\xa0", " ").replace("\n", " ").replace("\r", " ")
            return re.sub(r"\s+", " ", value).strip().lower()

        def canonical_profile_url(href):
            if not href:
                return ""
            value = str(href).strip()
            if value.startswith("/"):
                value = "https://www.linkedin.com" + value
            value = value.split("?", 1)[0].split("#", 1)[0].rstrip("/")
            if "/in/" not in value.lower():
                return ""
            return value.lower()

        requested_location = normalize_text(location)
        location_tokens = [
            token for token in re.findall(r"[a-z0-9]+", requested_location)
            if len(token) >= 3
        ]

        # LinkedIn can render result cards after the URL is already stable.
        for attempt in range(1, 13):
            try:
                self.page.wait_for_timeout(500)
            except Exception:
                pass

            try:
                links = self.page.locator("main a[href*='/in/']:visible")
                count = links.count()
            except Exception:
                links = self.page.locator("a[href*='/in/']:visible")
                try:
                    count = links.count()
                except Exception:
                    count = 0

            print(f"Employee DOM wait {attempt}/12: {count} visible /in/ links")

            if count:
                break

            try:
                self.page.mouse.wheel(0, 900)
            except Exception:
                pass
        else:
            print("No visible employee profile links on this page.")
            return profiles

        candidates = []
        seen_urls = set()

        for index in range(min(count, 300)):
            try:
                link = links.nth(index)
                href = canonical_profile_url(link.get_attribute("href"))
                if not href:
                    continue

                info = link.evaluate(
                    """
                    (el) => {
                        function visible(a) {
                            const r = a.getBoundingClientRect();
                            return r.width > 0 && r.height > 0;
                        }

                        function isResultContainer(node) {
                            if (!node) return false;
                            const tag = (node.tagName || '').toLowerCase();
                            const cls = (node.className || '').toString().toLowerCase();
                            const id = (node.id || '').toString().toLowerCase();

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

                        for (let depth = 0; depth < 12 && node; depth++, node = node.parentElement) {
                            if (isResultContainer(node)) {
                                container = node;
                                break;
                            }
                        }

                        // Fallback only accepts an ancestor that has exactly
                        // one visible /in/ link. This prevents a mutual
                        // connection from becoming a second candidate.
                        if (!container) {
                            node = el.parentElement;
                            for (let depth = 0; depth < 8 && node; depth++, node = node.parentElement) {
                                const text = (node.innerText || '').trim();
                                const anchors = Array.from(
                                    node.querySelectorAll("a[href*='/in/']")
                                ).filter(visible);

                                if (
                                    text.length >= 40 &&
                                    text.length <= 2500 &&
                                    anchors.length === 1
                                ) {
                                    container = node;
                                    break;
                                }
                            }
                        }

                        if (!container) {
                            return {
                                valid: false,
                                reason: 'no-result-container'
                            };
                        }

                        const anchors = Array.from(
                            container.querySelectorAll("a[href*='/in/']")
                        ).filter(visible);

                        if (!anchors.length) {
                            return {
                                valid: false,
                                reason: 'no-visible-profile-link'
                            };
                        }

                        // FIRST /in/ link in the result card is the primary
                        // employee link. Every later /in/ link is nested
                        // content such as mutual connections.
                        const primary = anchors[0];

                        if (el !== primary) {
                            return {
                                valid: false,
                                reason: 'nested-non-primary-profile-link',
                                container_text: container.innerText || '',
                                primary_href: primary.getAttribute('href') || ''
                            };
                        }

                        return {
                            valid: true,
                            container_text: container.innerText || '',
                            anchor_text: el.innerText || '',
                            anchor_count: anchors.length
                        };
                    }
                    """
                )

                if not info.get("valid"):
                    reason = info.get("reason", "unknown")
                    if reason == "nested-non-primary-profile-link":
                        print("SKIP nested /in/ link:", href)
                    continue

                card_text = str(
                    info.get("container_text")
                    or info.get("anchor_text")
                    or ""
                ).strip()

                normalized_card = normalize_text(card_text)

                if requested_location:
                    location_match = requested_location in normalized_card
                    if not location_match and location_tokens:
                        location_match = all(
                            token in normalized_card for token in location_tokens
                        )
                    if not location_match:
                        print(
                            "SKIP outside requested location:",
                            href,
                            "| location:",
                            location
                        )
                        continue

                anchor_text = str(
                    info.get("anchor_text") or ""
                ).replace("\n", " ").strip()
                anchor_text = re.sub(r"\s+", " ", anchor_text)

                # If LinkedIn puts no text directly in the anchor, use the
                # first meaningful line from the card, but never the entire
                # card as the employee name.
                if not anchor_text:
                    for line in str(card_text).splitlines():
                        line = re.sub(r"\s+", " ", line).strip()
                        if line:
                            anchor_text = line
                            break

                if not anchor_text:
                    print("SKIP candidate with empty employee name:", href)
                    continue

                if href in seen_urls:
                    continue

                seen_urls.add(href)
                candidates.append(
                    {
                        "full_name": anchor_text,
                        "profile_url": href,
                        "company": company,
                        "location": location,
                        "search_result_text": card_text,
                        "dom_index": index,
                    }
                )

                print("-" * 60)
                print("EMPLOYEE CANDIDATE:", href)
                print("Primary anchor:", anchor_text[:200])
                print("Result card:", card_text[:500])
                print("Connection degree: IGNORED")

            except Exception as ex:
                print("Profile-card inspection failed:", repr(ex))

        candidates.sort(key=lambda item: item["dom_index"])

        for item in candidates:
            item.pop("dom_index", None)
            profiles.append(item)

        print("=" * 60)
        print("UNIQUE LOCATION-MATCHING EMPLOYEE CANDIDATES:", len(profiles))
        print("=" * 60)
        print("EMPLOYEE PROFILES EXTRACTED:", len(profiles))

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

            # LinkedIn can show zero /in/ links briefly while the new result
            # page is being hydrated. Wait up to 20 seconds.
            rendered_profiles = 0
            rendered_cards = 0

            for attempt in range(1, 41):
                self.page.wait_for_timeout(500)

                try:
                    rendered_profiles = self.page.locator(
                        "main a[href*='/in/']:visible"
                    ).count()
                except Exception:
                    try:
                        rendered_profiles = self.page.locator(
                            "a[href*='/in/']:visible"
                        ).count()
                    except Exception:
                        rendered_profiles = 0

                try:
                    rendered_cards = self.page.locator(
                        "li.entity-result, li.reusable-search__result-container, "
                        "li[class*='search-result']:visible"
                    ).count()
                except Exception:
                    rendered_cards = 0

                print(
                    f"Result DOM wait {attempt}/40:",
                    rendered_profiles,
                    "visible /in/ links;",
                    rendered_cards,
                    "recognizable result cards"
                )

                if rendered_profiles > 0 or rendered_cards > 0:
                    print("=" * 60)
                    print("NEXT PAGE VALIDATED")
                    print("=" * 60)
                    print("Same company people-search:", True)
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


