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

    def get_profiles(
        self,
        company="",
        location=""
    ):

        print("=" * 60)
        print("EXTRACTING COMPANY-MATCHED PROFILES V2")
        print("=" * 60)

        profiles = []
        seen = set()

        requested_company = (
            company
            or ""
        ).strip().lower()

        requested_location = (
            location
            or ""
        ).strip().lower()

        print(
            "Requested company:",
            company
        )

        print(
            "Requested location:",
            location
        )

        # ---------------------------------------------------------
        # IMPORTANT
        #
        # We intentionally do NOT scan every /in/ link and accept it.
        #
        # A profile is accepted only when:
        #
        #   1. The /in/ link exists.
        #   2. We can identify a meaningful parent result container.
        #   3. The SAME result container contains the requested
        #      company name.
        #
        # This prevents sidebar/friend/recommendation profiles from
        # being accepted merely because they contain /in/.
        # ---------------------------------------------------------

        profile_links = self.page.locator(
            "a[href*='/in/']:visible"
        )

        link_count = profile_links.count()

        print(
            "Visible /in/ links discovered:",
            link_count
        )

        if link_count == 0:

            print(
                "No visible profile links found."
            )

            return profiles

        for i in range(link_count):

            try:

                link = profile_links.nth(i)

                href = link.get_attribute(
                    "href"
                )

                if not href:
                    continue

                href = href.strip()

                clean_url = href.split("?")[0]

                if clean_url.startswith("/"):
                    clean_url = (
                        "https://www.linkedin.com"
                        + clean_url
                    )

                if "/in/" not in clean_url.lower():
                    continue

                # -------------------------------------------------
                # Extract candidate name from the link.
                # -------------------------------------------------

                name = (
                    link.inner_text()
                    .strip()
                )

                if not name:
                    continue

                if "\n" in name:
                    continue

                if len(name) > 80:
                    continue

                if name.count(" ") > 8:
                    continue

                # -------------------------------------------------
                # Find the SAME search-result container.
                #
                # LinkedIn changes its classes frequently, so do not
                # depend on one exact class.
                #
                # We walk upward from the /in/ link and inspect
                # ancestors for search-result characteristics.
                # -------------------------------------------------

                container = None

                try:

                    container = link.locator(
                        "xpath=ancestor::*["
                        "self::li "
                        "or "
                        "contains(@class,'search-result') "
                        "or "
                        "contains(@class,'search-entity-result') "
                        "or "
                        "contains(@class,'reusable-search') "
                        "or "
                        "contains(@data-view-name,'search-entity')"
                        "][1]"
                    ).first

                    if container.count() == 0:
                        container = None

                except Exception:
                    container = None

                # -------------------------------------------------
                # If class-based detection fails, inspect a limited
                # number of ancestors manually.
                #
                # This is NOT a global /in/ fallback.
                # The search starts from the profile link itself.
                # -------------------------------------------------

                if container is None:

                    try:

                        candidate = link.locator(
                            "xpath=.."
                        )

                        for level in range(8):

                            try:

                                if candidate.count() == 0:
                                    break

                                tag = candidate.evaluate(
                                    "(el) => el.tagName"
                                )

                                cls = candidate.get_attribute(
                                    "class"
                                ) or ""

                                data_view = (
                                    candidate.get_attribute(
                                        "data-view-name"
                                    )
                                    or ""
                                )

                                tag = (
                                    tag
                                    or ""
                                ).lower()

                                cls = (
                                    cls
                                    or ""
                                ).lower()

                                data_view = (
                                    data_view
                                    or ""
                                ).lower()

                                looks_like_result = (

                                    "search-result"
                                    in cls

                                    or
                                    "search-entity-result"
                                    in cls

                                    or
                                    "reusable-search"
                                    in cls

                                    or
                                    "search-entity"
                                    in data_view

                                    or
                                    (
                                        tag == "li"
                                        and
                                        len(
                                            candidate.inner_text(
                                                timeout=1000
                                            ).strip()
                                        ) > 20
                                    )
                                )

                                if looks_like_result:

                                    container = candidate
                                    break

                                candidate = candidate.locator(
                                    "xpath=.."
                                )

                            except Exception:

                                break

                    except Exception:

                        container = None

                # -------------------------------------------------
                # No identifiable result container.
                #
                # IMPORTANT:
                # Do NOT accept the profile.
                # -------------------------------------------------

                if container is None:

                    print(
                        "SKIP - no search-result container:",
                        name
                    )

                    continue

                # -------------------------------------------------
                # Read ONLY the text from the same result container.
                # -------------------------------------------------

                try:

                    card_text = (
                        container.inner_text(
                            timeout=3000
                        )
                        .strip()
                    )

                except Exception:

                    print(
                        "SKIP - unable to read result container:",
                        name
                    )

                    continue

                card_text_lower = (
                    card_text.lower()
                )

                # -------------------------------------------------
                # COMPANY VALIDATION
                #
                # The requested company must occur inside the same
                # result container as the profile link.
                # -------------------------------------------------

                company_match = False

                if requested_company:

                    company_match = (
                        requested_company
                        in card_text_lower
                    )

                else:

                    # If no company was supplied, never silently
                    # accept a profile.
                    company_match = False

                if not company_match:

                    print("=" * 50)
                    print(
                        "SKIP - COMPANY MISMATCH"
                    )
                    print(
                        "Profile:",
                        name
                    )
                    print(
                        "Requested company:",
                        company
                    )
                    print(
                        "Result container does not contain "
                        "requested company."
                    )
                    print("=" * 50)

                    continue

                # -------------------------------------------------
                # OPTIONAL LOCATION VALIDATION
                #
                # Location is normally already applied by
                # apply_location(). We log it here, but do not make
                # extraction dependent on exact LinkedIn location
                # wording because LinkedIn may abbreviate it.
                # -------------------------------------------------

                if requested_location:

                    print(
                        "Company matched:",
                        name,
                        "->",
                        company
                    )

                # -------------------------------------------------
                # FINAL URL DEDUPLICATION
                # -------------------------------------------------

                if clean_url in seen:

                    continue

                seen.add(
                    clean_url
                )

                profiles.append(
                    {
                        "full_name": name,
                        "profile_url": clean_url,
                        "company": company,
                        "location": location,
                    }
                )

                print("=" * 60)
                print(
                    "COMPANY-MATCHED PROFILE ACCEPTED"
                )
                print("=" * 60)

                print(
                    "Name:",
                    name
                )

                print(
                    "Company:",
                    company
                )

                print(
                    "Location filter:",
                    location
                )

                print(
                    "Profile URL:",
                    clean_url
                )

            except Exception as ex:

                print(
                    "Profile candidate processing failed:",
                    repr(ex)
                )

        print("=" * 60)
        print(
            "COMPANY-MATCHED PROFILES EXTRACTED:",
            len(profiles)
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