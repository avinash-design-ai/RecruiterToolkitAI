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

        # --------------------------------------------------------
        # IMPORTANT DESIGN RULE
        #
        # The company was already selected by open_company_result().
        #
        # We must preserve that company identity and use LinkedIn's
        # own currentCompany people-search link.
        #
        # We must NOT:
        #   - construct an unrelated company ID
        #   - choose a network=F URL
        #   - scan arbitrary /in/ links
        #   - fall back to generic people search
        # --------------------------------------------------------

        company_page_url = self.page.url

        print("Current company URL:")
        print(company_page_url)

        # --------------------------------------------------------
        # Helper: validate a people-search URL.
        # --------------------------------------------------------

        def is_valid_people_url(url):

            if not url:
                return False

            lower = url.lower()

            if "/search/results/people/" not in lower:
                return False

            if "currentcompany" not in lower:
                return False

            return True

        # --------------------------------------------------------
        # Helper: identify whether LinkedIn redirected away from
        # the requested people-search page.
        # --------------------------------------------------------

        def is_bad_navigation_url(url):

            if not url:
                return True

            lower = url.lower()

            if is_valid_people_url(url):
                return False

            bad_parts = (
                "linkedin.com/",
                "/login",
                "/authwall",
                "/checkpoint",
                "/uas/login",
                "/signup",
                "/feed",
            )

            # Root LinkedIn page must be treated as failure.
            if lower.rstrip("/") == "https://www.linkedin.com":
                return True

            if "/search/results/" not in lower:
                return True

            return False

        # --------------------------------------------------------
        # Helper: extract currentCompany IDs from a URL.
        # --------------------------------------------------------

        def current_company_values(url):

            import urllib.parse

            try:

                parsed = urllib.parse.urlparse(url)

                query = urllib.parse.parse_qs(
                    parsed.query
                )

                values = query.get(
                    "currentCompany",
                    []
                )

                return [
                    value.strip()
                    for value in values
                    if value.strip()
                ]

            except Exception:

                return []

        # --------------------------------------------------------
        # 1. Find LinkedIn's own currentCompany employee link.
        #
        # Prefer:
        #   currentCompany=...
        #
        # Reject:
        #   network=F
        #   unrelated currentCompany IDs
        # --------------------------------------------------------

        def find_employee_link():

            print("=" * 60)
            print("DISCOVERING LINKEDIN COMPANY EMPLOYEE LINK")
            print("=" * 60)

            links = self.page.locator(
                "a[href*='/search/results/people/']"
            )

            count = links.count()

            print(
                "People-search links found:",
                count
            )

            candidates = []

            for i in range(count):

                try:

                    link = links.nth(i)

                    href = link.get_attribute(
                        "href"
                    )

                    if not href:
                        continue

                    href = href.strip()

                    if "/search/results/people/" not in href:
                        continue

                    if "currentCompany" not in href:
                        continue

                    lower_href = href.lower()

                    # ------------------------------------------------
                    # Never prefer a network-filtered URL.
                    # We want the complete company employee search.
                    # ------------------------------------------------

                    if "network=" in lower_href:
                        print(
                            "SKIP network-filtered employee URL:",
                            href
                        )
                        continue

                    values = current_company_values(
                        href
                    )

                    if not values:
                        continue

                    candidates.append(
                        (
                            link,
                            href,
                            values
                        )
                    )

                except Exception as ex:

                    print(
                        "Employee-link inspection failed:",
                        repr(ex)
                    )

            print(
                "Valid company employee candidates:",
                len(candidates)
            )

            if not candidates:
                return None

            # --------------------------------------------------------
            # We normally expect exactly one clean currentCompany
            # URL on the company page.
            #
            # Select the first clean LinkedIn-provided candidate.
            # Do NOT manufacture another URL here.
            # --------------------------------------------------------

            link, href, values = candidates[0]

            print(
                "Selected LinkedIn employee link:"
            )

            print(href)

            print(
                "currentCompany values:",
                values
            )

            return link

        # --------------------------------------------------------
        # Helper: click LinkedIn's employee link and validate result.
        # --------------------------------------------------------

        def click_employee_link():

            link = find_employee_link()

            if not link:

                print(
                    "No valid currentCompany employee link found."
                )

                return False

            try:

                print("=" * 60)
                print("CLICKING LINKEDIN EMPLOYEE LINK")
                print("=" * 60)

                link.click()

                self.page.wait_for_timeout(
                    5000
                )

                current_url = self.page.url

                print(
                    "URL after employee-link click:"
                )

                print(
                    current_url
                )

                if is_valid_people_url(
                    current_url
                ):

                    print(
                        "Employee search page confirmed."
                    )

                    return True

                print(
                    "Employee link click did not produce "
                    "a valid company people-search page."
                )

                return False

            except Exception as ex:

                print(
                    "Employee-link click failed:",
                    repr(ex)
                )

                return False

        # --------------------------------------------------------
        # 2. FIRST AND PREFERRED METHOD
        #
        # Click the exact employee-search link LinkedIn exposed
        # on the selected company page.
        # --------------------------------------------------------

        if click_employee_link():

            return True

        # --------------------------------------------------------
        # 3. CONTROLLED RECOVERY
        #
        # If LinkedIn redirected to / or another invalid page,
        # restore the authenticated feed.
        #
        # We do NOT attempt generic people search.
        # --------------------------------------------------------

        print("=" * 60)
        print("EMPLOYEE SEARCH NAVIGATION RECOVERY")
        print("=" * 60)

        print(
            "Navigation failed. Current URL:",
            self.page.url
        )

        try:

            print(
                "Returning to authenticated LinkedIn feed..."
            )

            self.page.goto(
                "https://www.linkedin.com/feed/",
                wait_until="domcontentloaded",
                timeout=60000
            )

            self.page.wait_for_timeout(
                3000
            )

            feed_url = self.page.url

            print(
                "Recovery feed URL:",
                feed_url
            )

            if (
                "/feed" not in feed_url.lower()
                or "/login" in feed_url.lower()
                or "/authwall" in feed_url.lower()
                or "/checkpoint" in feed_url.lower()
            ):

                print(
                    "Authenticated feed recovery failed."
                )

                return False

            print(
                "Authenticated feed recovered."
            )

        except Exception as ex:

            print(
                "Feed recovery failed:",
                repr(ex)
            )

            return False

        # --------------------------------------------------------
        # 4. Re-open the SAME company.
        #
        # We intentionally use the existing company URL captured
        # before employee navigation when possible.
        #
        # If LinkedIn no longer accepts it, use the existing
        # company search workflow instead of guessing.
        # --------------------------------------------------------

        company_reopened = False

        try:

            if (
                company_page_url
                and "/company/" in company_page_url.lower()
            ):

                print(
                    "Re-opening previously selected company:"
                )

                print(
                    company_page_url
                )

                self.page.goto(
                    company_page_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                self.page.wait_for_timeout(
                    3000
                )

                reopened_url = self.page.url

                print(
                    "Company recovery URL:",
                    reopened_url
                )

                if "/company/" in reopened_url.lower():

                    company_reopened = True

        except Exception as ex:

            print(
                "Direct company recovery failed:",
                repr(ex)
            )

        # --------------------------------------------------------
        # 5. If direct company recovery failed, re-run the existing
        # company search.
        #
        # IMPORTANT:
        # This uses the existing search_company() and
        # open_company_result() methods.
        #
        # Therefore company matching remains exactly as before.
        # --------------------------------------------------------

        if not company_reopened:

            print(
                "Re-running existing company search recovery..."
            )

            try:

                # The original company name is not stored as an
                # attribute, so derive it only from the existing
                # selected company page when possible.
                #
                # We refuse to guess a company name.
                #
                # Search for a visible h1 first.

                company_name = ""

                try:

                    heading = self.page.locator(
                        "h1"
                    ).first

                    if heading.count():

                        text = (
                            heading.inner_text()
                            .strip()
                        )

                        if text:

                            company_name = text

                except Exception:
                    pass

                if not company_name:

                    print(
                        "Could not safely recover company name."
                    )

                    print(
                        "Refusing generic people search."
                    )

                    return False

                print(
                    "Recovered company name:",
                    company_name
                )

                self.search_company(
                    company_name
                )

                found = (
                    self.open_company_result(
                        company_name
                    )
                )

                if not found:

                    print(
                        "Company recovery search failed."
                    )

                    return False

                company_reopened = True

            except Exception as ex:

                print(
                    "Company search recovery failed:",
                    repr(ex)
                )

                return False

        # --------------------------------------------------------
        # 6. Re-discover and CLICK the employee link.
        #
        # We deliberately do NOT use page.goto(best_url) here.
        # --------------------------------------------------------

        if company_reopened:

            print(
                "Company page recovered."
            )

            if click_employee_link():

                return True

        # --------------------------------------------------------
        # 7. Last controlled fallback:
        #
        # Re-scan the current company page for the employee link.
        # If LinkedIn exposes nothing, fail safely.
        #
        # Never construct generic people search.
        # Never scan /in/ links.
        # --------------------------------------------------------

        print("=" * 60)
        print("EMPLOYEE SEARCH COULD NOT BE SAFELY OPENED")
        print("=" * 60)

        print(
            "No valid LinkedIn currentCompany employee "
            "navigation succeeded."
        )

        print(
            "Refusing generic people search to prevent "
            "unrelated profiles."
        )

        return False

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
        Extract employee profiles from LinkedIn's people-search
        result area.

        Company comparison is normalized so punctuation,
        capitalization and separators do not cause false rejection.

        Examples:

            SmartWorks, LLC
            SmartWorks LLC
            SMARTWORKS, LLC
            SmartWorks - LLC

        all normalize to:

            smartworks llc

        A candidate is still required to have the requested
        company inside a bounded result container/ancestor.
        """

        print("=" * 60)
        print("EXTRACTING COMPANY-MATCHED PROFILES V4")
        print("=" * 60)

        print(
            "Requested company:",
            company
        )

        print(
            "Requested location:",
            location
        )

        # --------------------------------------------------------
        # Company normalization
        # --------------------------------------------------------

        def normalize_company(value):

            if not value:
                return ""

            value = (
                str(value)
                .replace("\xa0", " ")
                .strip()
                .lower()
            )

            value = re.sub(
                r"[^a-z0-9]+",
                " ",
                value
            )

            return " ".join(
                value.split()
            )

        requested_company = normalize_company(
            company
        )

        requested_location = normalize_company(
            location
        )

        profiles = []
        seen = set()

        # --------------------------------------------------------
        # Candidate /in/ links
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # Identify result container
        # --------------------------------------------------------

        def looks_like_result_container(
            element
        ):

            try:

                tag = (
                    element.evaluate(
                        "(el) => el.tagName.toLowerCase()"
                    )
                    or ""
                )

                classes = normalize_company(
                    element.get_attribute(
                        "class"
                    )
                    or ""
                )

                data_view = normalize_company(
                    element.get_attribute(
                        "data-view-name"
                    )
                    or ""
                )

                role = normalize_company(
                    element.get_attribute(
                        "role"
                    )
                    or ""
                )

                aria = normalize_company(
                    element.get_attribute(
                        "aria-label"
                    )
                    or ""
                )

                # Known LinkedIn result patterns.

                if (
                    "search-result" in classes
                    or
                    "search-entity-result" in classes
                    or
                    "reusable-search" in classes
                    or
                    "entity-result" in classes
                ):

                    return True

                if (
                    "search-entity-result" in data_view
                    or
                    "universal-template" in data_view
                ):

                    return True

                if (
                    tag == "li"
                    and
                    (
                        "result" in classes
                        or
                        "search" in classes
                    )
                ):

                    return True

                if (
                    tag == "article"
                    and
                    (
                        "result" in classes
                        or
                        "search" in classes
                        or
                        role == "article"
                    )
                ):

                    return True

                if role in (
                    "listitem",
                    "option",
                    "article"
                ):

                    return True

                if (
                    "search result" in aria
                ):

                    return True

            except Exception:

                pass

            return False

        # --------------------------------------------------------
        # Walk upward from candidate link
        # --------------------------------------------------------

        def find_result_container(
            link
        ):

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

        # --------------------------------------------------------
        # Controlled bounded fallback
        # --------------------------------------------------------

        def find_company_matching_ancestor(
            link
        ):

            current = link

            for depth in range(1, 9):

                try:

                    current = current.locator(
                        ".."
                    )

                    if current.count() == 0:

                        return None

                    tag = (
                        current.evaluate(
                            "(el) => el.tagName.toLowerCase()"
                        )
                        or ""
                    ).lower()

                    if tag in (
                        "body",
                        "html",
                        "main"
                    ):

                        return None

                    text = normalize_company(
                        current.inner_text(
                            timeout=2000
                        )
                    )

                    if not text:

                        continue

                    # Prevent page-level containers.

                    if len(text) > 5000:

                        continue

                    if (
                        requested_company
                        and
                        requested_company in text
                    ):

                        return current

                except Exception:

                    continue

            return None

        # --------------------------------------------------------
        # Process candidates
        # --------------------------------------------------------

        for i in range(count):

            try:

                link = links.nth(i)

                raw_name = (
                    link
                    .inner_text(
                        timeout=2000
                    )
                    .strip()
                )

                if not raw_name:

                    continue

                # Avoid navigation/multi-line links.

                if "\n" in raw_name:

                    continue

                href = link.get_attribute(
                    "href"
                )

                if not href:

                    continue

                clean_url = (
                    href
                    .split("?")[0]
                    .rstrip("/")
                )

                if not clean_url.startswith(
                    "http"
                ):

                    clean_url = (
                        "https://www.linkedin.com"
                        + clean_url
                    )

                if (
                    "/in/"
                    not in clean_url.lower()
                ):

                    continue

                if clean_url in seen:

                    continue

                print(
                    "-" * 60
                )

                print(
                    "Candidate:",
                    raw_name
                )

                print(
                    "Candidate URL:",
                    clean_url
                )

                matched = False

                # ------------------------------------------------
                # First: explicit LinkedIn result container
                # ------------------------------------------------

                container = (
                    find_result_container(
                        link
                    )
                )

                if container:

                    try:

                        container_text = (
                            container
                            .inner_text(
                                timeout=2000
                            )
                        )

                    except Exception:

                        container_text = ""

                    normalized_container = (
                        normalize_company(
                            container_text
                        )
                    )

                    print(
                        "Normalized requested company:",
                        requested_company
                    )

                    if (
                        requested_company
                        and
                        requested_company
                        in normalized_container
                    ):

                        matched = True

                        print(
                            "Company match found "
                            "in result container."
                        )

                    else:

                        print(
                            "Company NOT found "
                            "in normalized result container."
                        )

                # ------------------------------------------------
                # Second: bounded ancestor fallback
                # ------------------------------------------------

                if not matched:

                    fallback_container = (
                        find_company_matching_ancestor(
                            link
                        )
                    )

                    if fallback_container:

                        matched = True

                        print(
                            "Company match found "
                            "in bounded ancestor."
                        )

                # ------------------------------------------------
                # Reject if company was not validated
                # ------------------------------------------------

                if not matched:

                    print(
                        "REJECT - company not found "
                        "inside bounded result area:",
                        raw_name
                    )

                    continue

                # ------------------------------------------------
                # Accept candidate
                # ------------------------------------------------

                seen.add(
                    clean_url
                )

                profiles.append(
                    {
                        "full_name": raw_name,
                        "profile_url": clean_url,
                        "company": company,
                        "location": location,
                    }
                )

                print(
                    "ACCEPT - company validated:",
                    raw_name
                )

            except Exception as ex:

                print(
                    "Profile candidate processing failed:",
                    repr(ex)
                )

        # --------------------------------------------------------
        # Final output
        # --------------------------------------------------------

        print("=" * 60)

        print(
            "COMPANY-MATCHED PROFILES EXTRACTED:",
            len(profiles)
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
