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
        """
        Extract employee profiles ONLY from LinkedIn's actual
        people-search result area.

        IMPORTANT SAFETY RULE:

        We must never scan arbitrary visible /in/ links and accept
        them merely because they are present on the page.

        LinkedIn pages can contain /in/ links from:
            - search results
            - recommendations
            - friends/network suggestions
            - sidebar content
            - navigation
            - other unrelated modules

        Therefore every candidate profile must first be associated
        with a nearby result container and that SAME container must
        contain the requested company name.

        The current LinkedIn DOM does not always expose the old
        reusable-search__result-container selectors, so this version
        discovers the container by walking upward from each /in/ link.
        """

        print("=" * 60)
        print("EXTRACTING COMPANY-MATCHED PROFILES V3")
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
        seen = set()

        requested_company = (
            (company or "")
            .strip()
            .lower()
        )

        requested_location = (
            (location or "")
            .strip()
            .lower()
        )

        # ---------------------------------------------------------
        # Candidate profile links
        #
        # We inspect /in/ links only as CANDIDATES.
        #
        # A /in/ link is NOT automatically accepted.
        # ---------------------------------------------------------

        links = self.page.locator(
            "a[href*='/in/']:visible"
        )

        try:
            count = links.count()
        except Exception:
            count = 0

        print(
            "Visible /in/ links discovered:",
            count
        )

        if not count:

            print(
                "No visible profile links found."
            )

            print(
                "Profiles extracted: 0"
            )

            return profiles

        # ---------------------------------------------------------
        # Helper: normalize text
        # ---------------------------------------------------------

        def normalize(value):
            if not value:
                return ""

            return " ".join(
                str(value)
                .replace("\xa0", " ")
                .split()
            ).strip().lower()

        # ---------------------------------------------------------
        # Helper: determine whether a DOM node looks like a
        # LinkedIn search result container.
        #
        # We intentionally do NOT depend on one exact class name.
        # ---------------------------------------------------------

        def looks_like_result_container(element):
            try:

                tag = element.evaluate(
                    "(el) => el.tagName.toLowerCase()"
                )

                classes = element.get_attribute(
                    "class"
                ) or ""

                data_view = (
                    element.get_attribute(
                        "data-view-name"
                    )
                    or ""
                )

                role = (
                    element.get_attribute(
                        "role"
                    )
                    or ""
                )

                aria = (
                    element.get_attribute(
                        "aria-label"
                    )
                    or ""
                )

                class_text = normalize(classes)

                data_text = normalize(data_view)

                role_text = normalize(role)

                aria_text = normalize(aria)

                # Known LinkedIn result patterns.
                if (
                    "search-result" in class_text
                    or "search-entity-result" in class_text
                    or "reusable-search" in class_text
                    or "entity-result" in class_text
                ):
                    return True

                if (
                    "search-entity-result" in data_text
                    or "universal-template" in data_text
                ):
                    return True

                # LinkedIn sometimes exposes result items as list items.
                if (
                    tag == "li"
                    and (
                        "result" in class_text
                        or "search" in class_text
                    )
                ):
                    return True

                # Some versions use article-like result containers.
                if (
                    tag == "article"
                    and (
                        "result" in class_text
                        or "search" in class_text
                        or role_text == "article"
                    )
                ):
                    return True

                # Explicit result roles are useful when available.
                if role_text in (
                    "listitem",
                    "option",
                    "article",
                ):
                    return True

                # aria labels containing result/search wording.
                if (
                    "search result" in aria_text
                    or "search result" in class_text
                ):
                    return True

            except Exception:
                pass

            return False

        # ---------------------------------------------------------
        # Helper: find the nearest plausible result container.
        #
        # We walk upward from the profile link instead of searching
        # globally for one particular selector.
        #
        # Maximum depth prevents accidentally reaching <body>/<html>
        # and treating the entire page as one result.
        # ---------------------------------------------------------

        def find_result_container(link):
            current = link

            for depth in range(1, 9):

                try:

                    current = current.locator(
                        ".."
                    )

                    if current.count() == 0:
                        return None

                    if looks_like_result_container(
                        current
                    ):

                        return current

                except Exception:

                    return None

            return None

        # ---------------------------------------------------------
        # Helper: fallback structural container.
        #
        # If LinkedIn has removed recognizable class names entirely,
        # use a bounded ancestor that:
        #
        #   1. contains the candidate /in/ link
        #   2. has enough text to represent a result
        #   3. contains the requested company
        #
        # We never use body/html/document as a container.
        # ---------------------------------------------------------

        def find_company_matching_ancestor(link):

            current = link

            for depth in range(1, 9):

                try:

                    current = current.locator(
                        ".."
                    )

                    if current.count() == 0:
                        return None

                    tag = current.evaluate(
                        "(el) => el.tagName.toLowerCase()"
                    )

                    if tag in (
                        "body",
                        "html",
                        "main",
                    ):
                        return None

                    text = normalize(
                        current.inner_text(
                            timeout=2000
                        )
                    )

                    if not text:
                        continue

                    # Prevent accepting an enormous page-level container.
                    if len(text) > 5000:
                        continue

                    if (
                        requested_company
                        and requested_company in text
                    ):

                        return current

                except Exception:

                    continue

            return None

        # ---------------------------------------------------------
        # Process candidates
        # ---------------------------------------------------------

        for i in range(count):

            try:

                link = links.nth(i)

                name = normalize(
                    link.inner_text(
                        timeout=2000
                    )
                )

                if not name:
                    continue

                # Avoid accepting obvious multi-line/navigation text.
                if "\n" in (
                    link.inner_text(
                        timeout=2000
                    )
                ):
                    continue

                href = link.get_attribute(
                    "href"
                )

                if not href:
                    continue

                href = href.strip()

                # -------------------------------------------------
                # Normalize profile URL.
                # -------------------------------------------------

                clean_url = href.split(
                    "?"
                )[0].rstrip("/")

                if not clean_url.startswith(
                    "http"
                ):

                    clean_url = (
                        "https://www.linkedin.com"
                        + clean_url
                    )

                # Must actually be a LinkedIn profile URL.
                if "/in/" not in clean_url.lower():
                    continue

                if clean_url in seen:
                    continue

                print(
                    "-" * 60
                )

                print(
                    "Candidate:",
                    name
                )

                print(
                    "Candidate URL:",
                    clean_url
                )

                # -------------------------------------------------
                # FIRST: look for an explicit LinkedIn result
                # container.
                # -------------------------------------------------

                container = (
                    find_result_container(
                        link
                    )
                )

                if container:

                    try:

                        container_text = normalize(
                            container.inner_text(
                                timeout=2000
                            )
                        )

                    except Exception:

                        container_text = ""

                    if (
                        requested_company
                        and requested_company not in container_text
                    ):

                        print(
                            "REJECT - company not found "
                            "inside result container:",
                            name
                        )

                        continue

                    if not requested_company:

                        print(
                            "REJECT - requested company "
                            "is empty."
                        )

                        continue

                    # -------------------------------------------------
                    # Optional location validation.
                    #
                    # Do NOT reject solely because LinkedIn omits
                    # location text from a result card. The actual
                    # people-search URL already carries the location
                    # filter applied by the workflow.
                    #
                    # We therefore log location information but make
                    # company membership the mandatory DOM validation.
                    # -------------------------------------------------

                    if (
                        requested_location
                        and requested_location in container_text
                    ):

                        print(
                            "Location match found in result."
                        )

                    else:

                        print(
                            "Location text not explicitly present "
                            "in result; relying on LinkedIn location "
                            "filter."
                        )

                    seen.add(
                        clean_url
                    )

                    profiles.append(
                        {
                            "full_name": (
                                link.inner_text()
                                .strip()
                            ),
                            "profile_url": clean_url,
                            "company": company,
                            "location": location,
                        }
                    )

                    print(
                        "ACCEPT - company validated:",
                        name
                    )

                    continue

                # -------------------------------------------------
                # SECOND: structural fallback.
                #
                # We still require the requested company to exist
                # inside the SAME bounded ancestor.
                #
                # This is NOT a global page scan.
                # -------------------------------------------------

                fallback_container = (
                    find_company_matching_ancestor(
                        link
                    )
                )

                if not fallback_container:

                    print(
                        "REJECT - no bounded result container "
                        "with company match:",
                        name
                    )

                    continue

                try:

                    fallback_text = normalize(
                        fallback_container.inner_text(
                            timeout=2000
                        )
                    )

                except Exception:

                    fallback_text = ""

                if (
                    not requested_company
                    or requested_company not in fallback_text
                ):

                    print(
                        "REJECT - company validation failed:",
                        name
                    )

                    continue

                seen.add(
                    clean_url
                )

                profiles.append(
                    {
                        "full_name": (
                            link.inner_text()
                            .strip()
                        ),
                        "profile_url": clean_url,
                        "company": company,
                        "location": location,
                    }
                )

                print(
                    "ACCEPT - bounded ancestor company match:",
                    name
                )

            except Exception as ex:

                print(
                    "Profile candidate processing failed:",
                    repr(ex)
                )

        # ---------------------------------------------------------
        # Final output
        # ---------------------------------------------------------

        print("=" * 60)
        print(
            "COMPANY-MATCHED PROFILES EXTRACTED:"
            f" {len(profiles)}"
        )
        print("=" * 60)

        for profile in profiles:

            print(
                profile.get(
                    "full_name",
                    ""
                ),
                "->",
                profile.get(
                    "profile_url",
                    ""
                )
            )

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