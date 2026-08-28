import re

from pages.base_page import BasePage
from urllib.parse import urlparse, parse_qs

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

        print("Company links found:", count)

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

        exact_match.click()

        self.page.wait_for_timeout(
            5000
        )

        print(
            "After click URL:",
            self.page.url
        )

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

        print("Current URL:")
        print(self.page.url)

        # --------------------------------------------------------
        # 1. First inspect all links for an existing people search
        # --------------------------------------------------------

        print("Looking for existing employee search URL...")

        links = self.page.locator("a")

        count = links.count()

        candidate_urls = []

        for i in range(count):

            try:

                href = links.nth(i).get_attribute(
                    "href"
                )

                if not href:
                    continue

                href = href.strip()

                if "/search/results/people/" in href:

                    candidate_urls.append(href)

                    print(
                        "Candidate employee URL:",
                        href
                    )

            except Exception:
                pass

        # --------------------------------------------------------
        # 2. Prefer currentCompany people-search URL
        # --------------------------------------------------------

        best_url = None

        for url in candidate_urls:

            if "currentCompany" in url:

                best_url = url

                print(
                    "Selected existing currentCompany URL:"
                )

                print(best_url)

                break

        if not best_url and candidate_urls:

            best_url = candidate_urls[0]

            print(
                "Selected existing people-search URL:"
            )

            print(best_url)

        # --------------------------------------------------------
        # 3. If LinkedIn does not expose the URL, get company ID
        # --------------------------------------------------------

        if not best_url:

            print(
                "No employee search URL exposed by LinkedIn."
            )

            print(
                "Attempting to determine company ID..."
            )

            company_id = None

            # ----------------------------------------------------
            # Inspect current company URL
            # ----------------------------------------------------

            current_url = self.page.url

            print(
                "Company page URL:",
                current_url
            )

            parsed = urlparse(
                current_url
            )

            path_parts = [
                part
                for part in parsed.path.split("/")
                if part
            ]

            # Typical:
            # /company/company-name/
            #
            # Company numeric ID may not always be in URL,
            # so this is only a first attempt.

            # ----------------------------------------------------
            # Look for currentCompany anywhere in href attributes
            # ----------------------------------------------------

            for i in range(count):

                try:

                    href = links.nth(i).get_attribute(
                        "href"
                    )

                    if not href:
                        continue

                    if "currentCompany" in href:

                        parsed_href = urlparse(
                            href
                        )

                        params = parse_qs(
                            parsed_href.query
                        )

                        values = params.get(
                            "currentCompany"
                        )

                        if values:

                            company_id = (
                                values[0]
                            )

                            print(
                                "Company ID found:",
                                company_id
                            )

                            break

                except Exception:
                    pass

            # ----------------------------------------------------
            # Search page HTML for currentCompany
            # ----------------------------------------------------

            if not company_id:

                print(
                    "Searching page HTML for company ID..."
                )

                try:

                    html = self.page.content()

                    import re

                    patterns = [

                        r'currentCompany[^0-9]{0,50}([0-9]{3,20})',

                        r'"companyId"\s*:\s*"([0-9]{3,20})"',

                        r'"companyId"\s*:\s*([0-9]{3,20})',

                        r'urn:li:fsd_company:([0-9]{3,20})',

                        r'urn:li:organization:([0-9]{3,20})',

                    ]

                    for pattern in patterns:

                        match = re.search(
                            pattern,
                            html,
                            re.IGNORECASE
                        )

                        if match:

                            company_id = (
                                match.group(1)
                            )

                            print(
                                "Company ID extracted from page:"
                            )

                            print(company_id)

                            break

                except Exception as ex:

                    print(
                        "Company ID HTML search failed:",
                        repr(ex)
                    )

            # ----------------------------------------------------
            # 4. Construct LinkedIn employee search URL
            # ----------------------------------------------------

            if company_id:

                best_url = (
                    "https://www.linkedin.com/"
                    "search/results/people/"
                    f"?currentCompany=%5B%22{company_id}%22%5D"
                )

                print(
                    "Constructed employee search URL:"
                )

                print(best_url)

        # --------------------------------------------------------
        # 5. Last fallback: click People / employees UI
        # --------------------------------------------------------

        if not best_url:

            print(
                "Trying visible People / employees controls..."
            )

            possible_texts = [
                "People",
                "employees",
                "See all employees",
                "See all people",
                "View all employees",
                "View all people",
            ]

            for text in possible_texts:

                try:

                    locator = self.page.get_by_text(
                        text,
                        exact=False
                    ).first

                    if locator.count() == 0:
                        continue

                    if not locator.is_visible():
                        continue

                    print(
                        "Clicking employee control:",
                        text
                    )

                    locator.click()

                    self.page.wait_for_timeout(
                        5000
                    )

                    print(
                        "URL after employee control:",
                        self.page.url
                    )

                    if (
                        "/search/results/people/"
                        in self.page.url
                    ):

                        print(
                            "Employee search page opened."
                        )

                        return True

                except Exception as ex:

                    print(
                        "Employee control attempt failed:",
                        repr(ex)
                    )

        # --------------------------------------------------------
        # 6. Nothing worked
        # --------------------------------------------------------

        if not best_url:

            print(
                "Employee search URL could not be determined."
            )

            return False

        # --------------------------------------------------------
        # 7. Navigate to employee search
        # --------------------------------------------------------

        print("=" * 60)
        print("NAVIGATING TO EMPLOYEE SEARCH")
        print("=" * 60)

        print(
            "Using URL:"
        )

        print(
            best_url
        )

        try:

            self.page.goto(
                best_url,
                wait_until="domcontentloaded",
                timeout=60000
            )

        except Exception as ex:

            print(
                "Employee search navigation failed:",
                repr(ex)
            )

            return False

        self.page.wait_for_timeout(
            5000
        )

        print(
            "Employee page loaded:"
        )

        print(
            self.page.url
        )

        # --------------------------------------------------------
        # Validate
        # --------------------------------------------------------

        current_url = self.page.url.lower()

        if "/search/results/people/" not in current_url:

            print(
                "WARNING: LinkedIn did not open people search."
            )

            return False

        print(
            "Employee search page confirmed."
        )

        return True

    def apply_location(self, location):

        print(
            f"Applying location: {location}"
        )

        self.page.get_by_text(
            "Locations",
            exact=False
        ).first.click()

        self.page.wait_for_timeout(2000)

        location_box = self.page.locator(
            "input"
        ).last

        location_box.fill(location)

        self.page.wait_for_timeout(2000)

        self.page.keyboard.press(
            "ArrowDown"
        )

        self.page.keyboard.press(
            "Enter"
        )

        self.page.wait_for_timeout(1000)

        try:

            self.page.get_by_text(
                "Show results",
                exact=False
            ).first.click()

        except Exception:

            pass

        self.page.wait_for_timeout(
            5000
        )

        return True

    def get_profiles(self):

        profiles = []

        print("=" * 60)
        print("EXTRACTING COMPANY-MATCHED PROFILES")
        print("=" * 60)

        # --------------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT scan every visible /in/ link on the page.
        #
        # LinkedIn can expose /in/ links belonging to:
        #
        #   - recommendations
        #   - connections
        #   - sidebar content
        #   - other visible components
        #   - unrelated people
        #
        # We therefore restrict extraction to LinkedIn search
        # result cards and validate the company text contained
        # inside each result card.
        # --------------------------------------------------------

        # --------------------------------------------------------
        # Possible search-result card selectors used by LinkedIn.
        #
        # The first selector normally identifies the actual
        # people-search result list.
        # --------------------------------------------------------

        card_selectors = [

            "li.reusable-search__result-container",

            "li[class*='reusable-search__result-container']",

            "div[data-view-name='search-entity-result-universal-template']",

            "div[class*='search-entity-result']",

            "li[class*='search-result']",

        ]

        cards = None

        for selector in card_selectors:

            try:

                candidate = self.page.locator(
                    selector
                )

                count = candidate.count()

                print(
                    f"Result-card selector: {selector} -> {count}"
                )

                if count > 0:

                    cards = candidate

                    print(
                        "Using result-card selector:",
                        selector
                    )

                    break

            except Exception as ex:

                print(
                    "Selector inspection failed:",
                    selector,
                    repr(ex)
                )

        if cards is None:

            print("=" * 60)
            print("NO SEARCH RESULT CARDS FOUND")
            print("=" * 60)

            print(
                "IMPORTANT: No /in/ links will be scanned as a "
                "fallback because that could collect unrelated "
                "profiles."
            )

            return profiles


        # --------------------------------------------------------
        # Determine the company being searched.
        #
        # SearchWorkflowV2 creates CompanyPage and calls
        # search_company(company).
        #
        # We support both the new stored value and the existing
        # page-derived company value where possible.
        # --------------------------------------------------------

        search_company = getattr(
            self,
            "_search_company",
            ""
        )

        search_company = (
            search_company or ""
        ).strip()

        print(
            "Expected company:",
            search_company
        )


        # --------------------------------------------------------
        # If the CompanyPage does not yet have the company value,
        # attempt to determine it from the current URL/page.
        #
        # This is only secondary protection.
        # --------------------------------------------------------

        if not search_company:

            try:

                # Search for a visible company heading/link on
                # the current people-search page.
                company_candidates = self.page.locator(
                    "a[href*='/company/']"
                )

                company_count = company_candidates.count()

                for i in range(company_count):

                    try:

                        candidate_text = (
                            company_candidates
                            .nth(i)
                            .inner_text()
                            .strip()
                        )

                        if candidate_text:

                            first_line = (
                                candidate_text
                                .split("\n")[0]
                                .strip()
                            )

                            if first_line:

                                search_company = (
                                    first_line
                                )

                                break

                    except Exception:
                        pass

            except Exception:
                pass


        if not search_company:

            print("=" * 60)
            print("COMPANY VALIDATION VALUE NOT AVAILABLE")
            print("=" * 60)

            print(
                "No company name is available for validation."
            )

            print(
                "NO PROFILES WILL BE EXTRACTED."
            )

            return profiles


        # --------------------------------------------------------
        # Normalize company names for comparison.
        #
        # We intentionally do NOT perform fuzzy matching here.
        # A profile should only pass when LinkedIn's result card
        # explicitly contains the requested company.
        # --------------------------------------------------------

        def normalize_company(value):

            value = (
                value or ""
            ).strip().lower()

            value = re.sub(
                r"\s+",
                " ",
                value
            )

            value = value.replace(
                "’",
                "'"
            )

            return value


        expected_company = normalize_company(
            search_company
        )

        print(
            "Normalized expected company:",
            expected_company
        )


        # --------------------------------------------------------
        # Process ONLY result cards.
        # --------------------------------------------------------

        seen = set()

        card_count = cards.count()

        print(
            "Search result cards:",
            card_count
        )


        for i in range(card_count):

            try:

                card = cards.nth(i)

                if not card.is_visible():

                    continue


                # ------------------------------------------------
                # Read complete result-card text.
                #
                # This is used ONLY to verify the company.
                # ------------------------------------------------

                card_text = (
                    card.inner_text()
                    .strip()
                )

                if not card_text:

                    continue


                print("=" * 50)
                print(
                    f"RESULT CARD {i + 1}"
                )
                print("=" * 50)

                print(
                    card_text[:1000]
                )


                # ------------------------------------------------
                # Find company information inside this card.
                #
                # Prefer explicit company-related elements rather
                # than blindly treating every line as company.
                # ------------------------------------------------

                company_texts = []


                company_selectors = [

                    "a[href*='/company/']",

                    "a[data-field='experience_company']",

                    "span[aria-label*='company' i]",

                    "div[class*='entity-result__primary-subtitle']",

                    "div[class*='primary-subtitle']",

                    "div[class*='secondary-subtitle']",

                    "p[class*='subline']",

                ]


                for company_selector in company_selectors:

                    try:

                        company_nodes = card.locator(
                            company_selector
                        )

                        company_node_count = (
                            company_nodes.count()
                        )

                        for j in range(
                            company_node_count
                        ):

                            try:

                                value = (
                                    company_nodes
                                    .nth(j)
                                    .inner_text()
                                    .strip()
                                )

                                if value:

                                    company_texts.append(
                                        value
                                    )

                            except Exception:
                                pass

                    except Exception:
                        pass


                # ------------------------------------------------
                # Remove duplicates while preserving order.
                # ------------------------------------------------

                unique_company_texts = []

                seen_company_texts = set()

                for value in company_texts:

                    normalized_value = normalize_company(
                        value
                    )

                    if not normalized_value:
                        continue

                    if normalized_value in seen_company_texts:
                        continue

                    seen_company_texts.add(
                        normalized_value
                    )

                    unique_company_texts.append(
                        value
                    )


                print(
                    "Company candidates:",
                    unique_company_texts
                )


                # ------------------------------------------------
                # STRICT COMPANY MATCH
                # ------------------------------------------------

                company_matches = False

                for company_value in unique_company_texts:

                    normalized_company_value = (
                        normalize_company(
                            company_value
                        )
                    )

                    if (
                        normalized_company_value
                        == expected_company
                    ):

                        company_matches = True

                        print(
                            "COMPANY MATCH:",
                            company_value
                        )

                        break


                if not company_matches:

                    print(
                        "SKIPPED: result card does not "
                        "explicitly match requested company."
                    )

                    continue


                # ------------------------------------------------
                # Find profile link ONLY inside this validated card.
                # ------------------------------------------------

                profile_links = card.locator(
                    "a[href*='/in/']"
                )

                profile_count = (
                    profile_links.count()
                )

                print(
                    "Profile links inside validated card:",
                    profile_count
                )


                selected_link = None


                for j in range(profile_count):

                    try:

                        link = (
                            profile_links
                            .nth(j)
                        )

                        href = (
                            link.get_attribute(
                                "href"
                            )
                        )

                        if not href:
                            continue

                        href = href.strip()

                        clean_url = (
                            href.split("?")[0]
                            .split("#")[0]
                        )

                        if not clean_url.startswith(
                            "http"
                        ):

                            clean_url = (
                                "https://www.linkedin.com"
                                + clean_url
                            )

                        if not clean_url.startswith(
                            "https://www.linkedin.com/in/"
                        ):

                            continue

                        selected_link = link

                        break

                    except Exception:
                        pass


                if selected_link is None:

                    print(
                        "SKIPPED: validated company card "
                        "contains no profile URL."
                    )

                    continue


                # ------------------------------------------------
                # Extract profile URL.
                # ------------------------------------------------

                href = (
                    selected_link
                    .get_attribute(
                        "href"
                    )
                )

                if not href:

                    continue

                clean_url = (
                    href.split("?")[0]
                    .split("#")[0]
                )

                if not clean_url.startswith(
                    "http"
                ):

                    clean_url = (
                        "https://www.linkedin.com"
                        + clean_url
                    )


                if clean_url in seen:

                    continue


                # ------------------------------------------------
                # Extract name from the profile link itself.
                # ------------------------------------------------

                name = (
                    selected_link
                    .inner_text()
                    .strip()
                )


                if not name:

                    # Try common LinkedIn result name selectors.
                    name_selectors = [

                        "span[aria-hidden='true']",

                        "a[data-control-name='search_srp_result']",

                        "span[class*='entity-result__title-text']",

                        "div[class*='entity-result__title-text']",

                    ]

                    for name_selector in name_selectors:

                        try:

                            name_node = (
                                card
                                .locator(
                                    name_selector
                                )
                                .first
                            )

                            if name_node.count() > 0:

                                candidate_name = (
                                    name_node
                                    .inner_text()
                                    .strip()
                                )

                                if candidate_name:

                                    name = candidate_name

                                    break

                        except Exception:
                            pass


                if not name:

                    print(
                        "SKIPPED: profile name unavailable."
                    )

                    continue


                # ------------------------------------------------
                # Keep the existing simple name safety checks.
                # ------------------------------------------------

                if "\n" in name:

                    continue

                if len(name) > 80:

                    continue


                seen.add(
                    clean_url
                )


                # ------------------------------------------------
                # Extract headline/location where available.
                # These are still from the SAME validated card.
                # ------------------------------------------------

                headline = ""
                result_location = ""


                try:

                    subtitle_nodes = card.locator(
                        "div[class*='entity-result__primary-subtitle'], "
                        "div[class*='primary-subtitle']"
                    )

                    subtitle_count = (
                        subtitle_nodes.count()
                    )

                    if subtitle_count > 0:

                        headline = (
                            subtitle_nodes
                            .first
                            .inner_text()
                            .strip()
                        )

                except Exception:
                    pass


                try:

                    secondary_nodes = card.locator(
                        "div[class*='entity-result__secondary-subtitle'], "
                        "div[class*='secondary-subtitle']"
                    )

                    secondary_count = (
                        secondary_nodes.count()
                    )

                    if secondary_count > 0:

                        result_location = (
                            secondary_nodes
                            .first
                            .inner_text()
                            .strip()
                        )

                except Exception:
                    pass


                profiles.append(
                    {
                        "full_name": name,
                        "headline": headline,
                        "location": result_location,
                        "company": search_company,
                        "profile_url": clean_url,
                    }
                )


                print("=" * 50)
                print("PROFILE ACCEPTED")
                print("=" * 50)

                print(
                    "Name:",
                    name
                )

                print(
                    "Company:",
                    search_company
                )

                print(
                    "Profile URL:",
                    clean_url
                )


            except Exception as ex:

                print(
                    "Result-card processing failed:",
                    repr(ex)
                )


        print("=" * 60)
        print(
            f"Company-matched profiles extracted: "
            f"{len(profiles)}"
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