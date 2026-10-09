from pages.base_page import BasePage
from urllib.parse import urlparse, parse_qs


import re
class CompanyPage(BasePage):

    def __init__(self, page):
        super().__init__(page)

    def search_company(self, company):
        """
        Search LinkedIn using its current global-search control.

        LinkedIn changes the input placeholder and can collapse the input into
        a Search button. Resolve the live input dynamically, and fail clearly
        instead of waiting 30 seconds on one obsolete selector.
        """
        import re

        company = str(company or "").strip()
        if not company:
            raise ValueError("Company name must not be empty.")

        self._search_company = company

        print("=" * 60)
        print("SEARCHING LINKEDIN COMPANY")
        print("=" * 60)
        print("Requested company:", company)

        try:
            print("Current URL:", self.page.url)
            print("Current title:", self.page.title())
        except Exception as ex:
            print("Could not read current page state:", repr(ex))

        input_selectors = (
            "input.search-global-typeahead__input",
            "input[data-test-global-search-input]",
            "input[placeholder*='Search' i]",
            "input[aria-label*='Search' i]",
            "input[placeholder*='looking' i]",
            "input[type='search']",
            "input[role='combobox']",
        )

        def find_visible_search_input():
            for selector in input_selectors:
                try:
                    matches = self.page.locator(selector)
                    for index in range(matches.count()):
                        candidate = matches.nth(index)
                        try:
                            if not candidate.is_visible() or not candidate.is_enabled():
                                continue
                            attrs = " ".join(
                                str(candidate.get_attribute(name) or "")
                                for name in (
                                    "placeholder", "aria-label", "name",
                                    "class", "data-test-global-search-input",
                                )
                            )
                            dedicated = (
                                "search-global-typeahead__input" in selector
                                or "data-test-global-search-input" in selector
                                or "role='combobox'" in selector
                                or "type='search'" in selector
                            )
                            if dedicated or re.search(r"search|looking for", attrs, re.I):
                                print("LinkedIn search box found using selector:", selector)
                                print("Search input attributes:", repr(attrs[:250]))
                                return candidate
                        except Exception:
                            continue
                except Exception as ex:
                    print("Search selector inspection failed:", selector, repr(ex))

            # Accessibility fallback; do not select an arbitrary textbox.
            try:
                matches = self.page.get_by_role("combobox")
                for index in range(matches.count()):
                    candidate = matches.nth(index)
                    try:
                        if not candidate.is_visible() or not candidate.is_enabled():
                            continue
                        attrs = " ".join(
                            str(candidate.get_attribute(name) or "")
                            for name in ("placeholder", "aria-label", "name", "class")
                        )
                        if re.search(r"search|looking for", attrs, re.I):
                            print("LinkedIn search box found using role=combobox.")
                            return candidate
                    except Exception:
                        continue
            except Exception as ex:
                print("Combobox fallback failed:", repr(ex))

            # Last fallback: only visible inputs identifying themselves as search.
            try:
                visible_inputs = self.page.locator("input:visible")
                count = visible_inputs.count()
                print("Visible input count:", count)
                for index in range(count):
                    candidate = visible_inputs.nth(index)
                    try:
                        attrs = " ".join(
                            str(candidate.get_attribute(name) or "")
                            for name in ("placeholder", "aria-label", "name", "class", "type")
                        )
                        print(f"Visible input #{index + 1} attributes:", repr(attrs[:250]))
                        if candidate.is_enabled() and re.search(
                            r"search|looking for|global-typeahead", attrs, re.I
                        ):
                            print("Selected visible input as LinkedIn search box.")
                            return candidate
                    except Exception:
                        continue
            except Exception as ex:
                print("Visible-input fallback failed:", repr(ex))

            return None

        try:
            self.page.wait_for_timeout(1000)
        except Exception:
            pass

        search_box = find_visible_search_input()

        # In some LinkedIn layouts the input is collapsed behind a button/icon.
        # Click only an explicitly search-labelled opener, then reacquire the input.
        if search_box is None:
            opener_selectors = (
                "button.search-global-typeahead__collapsed-search-button",
                ".search-global-typeahead__collapsed-search-button",
                "button[aria-label*='Search' i]",
                "[role='button'][aria-label*='Search' i]",
                "button[title*='Search' i]",
                "[role='button'][title*='Search' i]",
            )

            for selector in opener_selectors:
                try:
                    controls = self.page.locator(selector)
                    for index in range(controls.count()):
                        control = controls.nth(index)
                        try:
                            if not control.is_visible() or not control.is_enabled():
                                continue
                            label = " ".join(
                                str(control.get_attribute(name) or "")
                                for name in ("aria-label", "title", "class", "data-control-name")
                            )
                            text_value = ""
                            try:
                                text_value = control.inner_text(timeout=1000)
                            except Exception:
                                pass
                            if (
                                "collapsed-search-button" not in label
                                and not re.search(r"\bsearch\b", label + " " + text_value, re.I)
                            ):
                                continue

                            print("Opening LinkedIn global search using:", selector, repr(label or text_value))
                            control.click(timeout=4000)
                            self.page.wait_for_timeout(500)
                            search_box = find_visible_search_input()
                            if search_box is not None:
                                break
                        except Exception as ex:
                            print("Search opener attempt failed:", selector, repr(ex))
                    if search_box is not None:
                        break
                except Exception as ex:
                    print("Search opener selector unavailable:", selector, repr(ex))

        if search_box is None:
            try:
                controls = self.page.get_by_role(
                    "button",
                    name=re.compile(r"^\s*search(\s+linkedin)?\s*$", re.I),
                )
                for index in range(controls.count()):
                    control = controls.nth(index)
                    try:
                        if control.is_visible() and control.is_enabled():
                            print("Opening LinkedIn global search using accessible Search button.")
                            control.click(timeout=4000)
                            self.page.wait_for_timeout(500)
                            search_box = find_visible_search_input()
                            if search_box is not None:
                                break
                    except Exception as ex:
                        print("Accessible Search-button attempt failed:", repr(ex))
            except Exception as ex:
                print("Accessible Search-button lookup failed:", repr(ex))

        if search_box is None:
            try:
                print("Final URL:", self.page.url)
                print("Final title:", self.page.title())
            except Exception:
                pass
            raise RuntimeError(
                "LinkedIn global search control was not found after checking "
                "visible inputs and the collapsed Search control."
            )

        print("Entering company into LinkedIn search:", company)
        try:
            search_box.click(timeout=10000)
            search_box.fill(company, timeout=10000)
            search_box.press("Enter", timeout=10000)
        except Exception as ex:
            raise RuntimeError(
                f"Could not submit company '{company}' through LinkedIn global search: {ex!r}"
            ) from ex

        print("Company search submitted.")
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
        Establish a company-scoped LinkedIn people search without touching
        connection-degree UI or synthesizing any search URL.

        LinkedIn can expose the employee-search link on a company page but
        redirect a same-page Playwright click to https://www.linkedin.com/.
        Therefore:
          1. preserve the company page;
          2. collect only genuine LinkedIn people-search hrefs containing
             currentCompany;
          3. open each exact LinkedIn-supplied href in an isolated tab;
          4. validate the resulting tab before making it the workflow owner;
          5. leave the company page untouched when a candidate fails.

        The exact href is always taken from LinkedIn's DOM. No query string is
        invented or rewritten here.
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
            lower = str(url).lower()
            return (
                "/search/results/people/" in lower
                and "currentcompany=" in lower
            )

        def is_blocked_url(url):
            lower = str(url or "").lower()
            return (not lower) or any(
                marker in lower
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

        def company_ids(url):
            try:
                from urllib.parse import parse_qs, urlsplit
                query = parse_qs(
                    urlsplit(str(url or "")).query,
                    keep_blank_values=True,
                )
                return (
                    query.get("currentCompany", [])
                    or query.get("currentcompany", [])
                )
            except Exception:
                return []

        def candidate_score(href):
            lower = str(href or "").lower()
            score = 0
            if "pastcompany=" not in lower:
                score += 100
            if "origin=company_page_canned_search" in lower:
                score += 50
            elif "origin=company_hires_in_company_canned_search" in lower:
                score += 45
            elif "origin=" in lower and "company" in lower:
                score += 20
            return score

        def validate_employee_page(tab, expected_ids, label):
            try:
                tab.wait_for_load_state("domcontentloaded", timeout=30000)
            except Exception:
                pass
            try:
                tab.wait_for_timeout(3500)
            except Exception:
                pass

            final_url = str(tab.url or "").strip()
            print(f"{label} final URL:", final_url)

            if is_blocked_url(final_url) or not is_people_url(final_url):
                print(f"{label} rejected: not an authenticated company people-search page.")
                return False

            final_ids = company_ids(final_url)
            if expected_ids and final_ids != expected_ids:
                print(f"{label} rejected: currentCompany changed.")
                print("Expected:", expected_ids)
                print("Actual:", final_ids)
                return False

            return True

        # CASE 1: company click already landed directly on company people search.
        if is_people_url(current_url) and not is_blocked_url(current_url):
            ids = company_ids(current_url)
            if not ids:
                print("ERROR: Current people-search page has no currentCompany.")
                return False

            print("=" * 60)
            print("COMPANY PEOPLE-SEARCH PAGE ALREADY OPEN")
            print("=" * 60)
            print("Company scope:", ids)
            print("Connection-degree handling: DISABLED")
            print("Preserving LinkedIn's returned people-search page.")
            print("Company scope preserved:", ids)

            self._employee_search_scope_ready = True
            return True

        # CASE 2: company page exposes LinkedIn-supplied people-search links.
        if "/company/" not in current_url.lower() or is_blocked_url(current_url):
            print("ERROR: Current page is neither company-scoped people search nor a usable company page.")
            print("Current URL:", current_url)
            return False

        links = self.page.locator("a[href*='/search/results/people/']")
        count = links.count()
        print("People-search links found:", count)

        candidates = []
        seen = set()

        for i in range(count):
            try:
                href = (links.nth(i).get_attribute("href") or "").strip()
                if not href:
                    continue
                if href.startswith("/"):
                    href = "https://www.linkedin.com" + href
                if "/search/results/people/" not in href.lower():
                    continue

                ids = company_ids(href)
                if not ids:
                    continue

                key = href.split("#", 1)[0]
                if key in seen:
                    continue

                seen.add(key)
                candidates.append((candidate_score(href), i, href, ids))
            except Exception as ex:
                print("Employee-search link inspection failed:", repr(ex))

        candidates.sort(key=lambda item: (-item[0], item[1], item[2].lower()))
        print("Validated LinkedIn people-search candidates:", len(candidates))

        if not candidates:
            print("ERROR: No genuine currentCompany LinkedIn people-search link found.")
            return False

        context = self.page.context
        company_page = self.page

        # Never navigate the company-page owner to a failing people link.
        for attempt, (_, source_index, href, expected_ids) in enumerate(candidates, start=1):
            print("-" * 60)
            print(f"EMPLOYEE SEARCH CANDIDATE {attempt}/{len(candidates)}")
            print("Source link index:", source_index)
            print("Exact LinkedIn href:", href)

            # Path A: browser-real Ctrl-click in a fresh tab.
            new_tab = None
            try:
                with context.expect_page(timeout=12000) as page_info:
                    links.nth(source_index).click(
                        modifiers=["Control"],
                        timeout=15000,
                    )
                new_tab = page_info.value

                if validate_employee_page(new_tab, expected_ids, "Ctrl-click candidate"):
                    self.page = new_tab
                    self._employee_search_scope_ready = True

                    print("=" * 60)
                    print("COMPANY PEOPLE SEARCH READY")
                    print("=" * 60)
                    print("Navigation mode: LinkedIn link -> isolated tab")
                    print("Final URL:", self.page.url)
                    print("Company scope preserved:", expected_ids)
                    return True
            except Exception as ex:
                print("Ctrl-click employee-search candidate failed:", repr(ex))

            if new_tab is not None:
                try:
                    if not new_tab.is_closed():
                        new_tab.close()
                except Exception:
                    pass

            # Path B: exact href supplied by LinkedIn, opened in an isolated tab.
            direct_tab = None
            try:
                direct_tab = context.new_page()
                print("Trying exact LinkedIn-supplied href in isolated tab...")
                direct_tab.goto(
                    href,
                    wait_until="domcontentloaded",
                    timeout=60000,
                    referer=current_url,
                )

                if validate_employee_page(direct_tab, expected_ids, "Exact-href candidate"):
                    self.page = direct_tab
                    self._employee_search_scope_ready = True

                    print("=" * 60)
                    print("COMPANY PEOPLE SEARCH READY")
                    print("=" * 60)
                    print("Navigation mode: exact LinkedIn href -> isolated tab")
                    print("Final URL:", self.page.url)
                    print("Company scope preserved:", expected_ids)
                    return True
            except Exception as ex:
                print("Exact LinkedIn employee-search href failed:", repr(ex))

            if direct_tab is not None:
                try:
                    if not direct_tab.is_closed():
                        direct_tab.close()
                except Exception:
                    pass

            try:
                if not company_page.is_closed():
                    self.page = company_page
            except Exception:
                pass

        print("=" * 60)
        print("EMPLOYEE SEARCH COULD NOT BE SAFELY OPENED")
        print("=" * 60)
        print("No LinkedIn-supplied currentCompany employee-search navigation succeeded.")
        print("Company page was preserved; generic people search was refused.")
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


