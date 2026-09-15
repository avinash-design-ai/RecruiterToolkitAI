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
        # IMPORTANT:
        # The exact company-result click can land directly on the
        # company's LinkedIn people-search page.
        #
        # If that happens, employee navigation is ALREADY complete.
        # Do not try to rediscover or click another employee link.
        # --------------------------------------------------------

        current_url_lower = company_page_url.lower()

        if (
            "/search/results/people/" in current_url_lower
            and "currentcompany=" in current_url_lower
        ):
            print("=" * 60)
            print("COMPANY PEOPLE-SEARCH PAGE ALREADY OPEN")
            print("=" * 60)
            print("Current URL:")
            print(company_page_url)
            print("Valid currentCompany people-search URL confirmed.")
            print("Skipping employee-link discovery.")
            return True

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
                    # IMPORTANT:
                    #
                    # LinkedIn may expose the company employee search as
                    # a canned search containing network/origin filters.
                    #
                    # Do NOT reject that LinkedIn-provided link.
                    #
                    # Instead, preserve the same currentCompany URL and
                    # remove only the canned-search filters before click.
                    # ------------------------------------------------

                    values = current_company_values(
                        href
                    )

                    if not values:
                        continue

                    # ------------------------------------------------
                    # Safety check:
                    #
                    # If the selected company URL contains a
                    # currentCompany value, require the employee
                    # link to use the SAME company value.
                    #
                    # This prevents unrelated company people-search
                    # URLs from being accepted.
                    # ------------------------------------------------

                    selected_company_values = current_company_values(
                        company_page_url
                    )

                    if (
                        selected_company_values
                        and values != selected_company_values
                    ):
                        print(
                            "SKIP unrelated currentCompany URL:",
                            href
                        )
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

                # ------------------------------------------------
                # Clean LinkedIn canned-search filters while
                # preserving the exact currentCompany value.
                #
                # We modify the href of the LinkedIn-provided
                # employee link and then click that same link.
                # ------------------------------------------------

                print(
                    "Clicking LinkedIn employee search option..."
                )

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

        # --------------------------------------------------------
        # CONTROLLED EMPLOYEE NAVIGATION RECOVERY
        #
        # IMPORTANT:
        # Do not make /feed/ the required recovery checkpoint.
        #
        # LinkedIn can redirect the employee-search click through
        # /login/, /ssr-login/ or remember-me-auto-login even when
        # the original authenticated company page is still usable.
        #
        # The selected company URL was captured before navigation.
        # Recover the SAME company directly and rediscover LinkedIn's
        # own currentCompany employee link.
        # --------------------------------------------------------

        print("=" * 60)
        print("DIRECT COMPANY EMPLOYEE NAVIGATION RECOVERY")
        print("=" * 60)

        company_reopened = False

        try:

            if (
                company_page_url
                and "/company/" in company_page_url.lower()
            ):

                print(
                    "Re-opening previously selected company directly:"
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

                if (
                    "/company/" in reopened_url.lower()
                    and "/login" not in reopened_url.lower()
                    and "/authwall" not in reopened_url.lower()
                    and "/checkpoint" not in reopened_url.lower()
                ):

                    company_reopened = True

                    print(
                        "Selected company page recovered."
                    )

        except Exception as ex:

            print(
                "Direct company recovery failed:",
                repr(ex)
            )

        # --------------------------------------------------------
        # If the exact company URL cannot be reopened, use the
        # existing company-search recovery.
        #
        # We deliberately do NOT use generic people search.
        # --------------------------------------------------------


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

                # ------------------------------------------------
                # IMPORTANT:
                #
                # search_company() already stores the exact company
                # requested by the workflow in self._search_company.
                #
                # Do NOT attempt to recover the company name from
                # the current page because LinkedIn may have redirected
                # the browser to /login/, /authwall/ or another page.
                #
                # The stored company name is the authoritative value.
                # ------------------------------------------------

                company_name = getattr(
                    self,
                    "_search_company",
                    ""
                )

                company_name = (
                    company_name.strip()
                    if company_name
                    else ""
                )

                if not company_name:

                    print(
                        "ERROR: Previously selected company name "
                        "is not available."
                    )

                    print(
                        "Refusing generic people search."
                    )

                    return False

                print(
                    "Recovered company name from workflow state:",
                    company_name
                )

                # ------------------------------------------------
                # Re-run the EXISTING company search.
                #
                # This preserves the existing exact-company matching
                # behavior in search_company() + open_company_result().
                # ------------------------------------------------

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

                print(
                    "Selected company recovered through "
                    "existing company search."
                )

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

        print("=" * 60)
        print("APPLYING LOCATION FILTER")
        print("=" * 60)
        print("Requested location:", location)

        before_url = self.page.url
        print("URL before location filter:", before_url)

        def valid_people_url(url):
            if not url:
                return False
            lower = url.lower()
            return (
                "/search/results/people/" in lower
                and "currentcompany=" in lower
            )

        def bad_navigation(url):
            if not url:
                return True

            lower = url.lower()

            if lower.rstrip("/") == "https://www.linkedin.com":
                return True

            bad = (
                "/login",
                "/authwall",
                "/checkpoint",
                "/uas/login",
                "/signup",
            )

            return any(x in lower for x in bad)

        if not valid_people_url(before_url):
            print(
                "[LOCATION ERROR] Current page is not a valid "
                "company People-search page."
            )
            return False

        # ------------------------------------------------------------
        # 1. Open Locations
        # ------------------------------------------------------------
        try:
            locations = self.page.get_by_text(
                "Locations",
                exact=True,
            )

            count = locations.count()

            print("Exact Locations matches:", count)

            clicked = False

            for i in range(count):
                item = locations.nth(i)

                try:
                    if not item.is_visible():
                        continue

                    item.click(timeout=10000)
                    print(
                        f"Clicked Locations match #{i + 1}"
                    )
                    clicked = True
                    break

                except Exception as ex:
                    print(
                        f"Locations click #{i + 1} failed:",
                        repr(ex),
                    )

            if not clicked:
                print(
                    "[LOCATION ERROR] Locations control not found."
                )
                return False

            self.page.wait_for_timeout(1500)

            print(
                "URL after opening Locations:",
                self.page.url,
            )

            if bad_navigation(self.page.url):
                print(
                    "[LOCATION ERROR] Opening Locations caused "
                    "bad navigation."
                )
                return False

            if not valid_people_url(self.page.url):
                print(
                    "[LOCATION ERROR] Opening Locations changed "
                    "the company People-search URL."
                )
                return False

        except Exception as ex:
            print(
                "[LOCATION ERROR] Opening Locations failed:",
                repr(ex),
            )
            return False

        # ------------------------------------------------------------
        # 2. Identify active filter UI
        # ------------------------------------------------------------
        try:
            dialogs = self.page.locator(
                "[role='dialog']:visible"
            )

            dialog_count = dialogs.count()

            print(
                "Visible dialogs:",
                dialog_count,
            )

            if dialog_count:
                panel = dialogs.last
                print(
                    "Using active visible dialog."
                )
            else:
                panel = self.page
                print(
                    "No dialog detected; using page as fallback scope."
                )

        except Exception as ex:
            print(
                "[LOCATION ERROR] Filter panel detection failed:",
                repr(ex),
            )
            return False

        # ------------------------------------------------------------
        # 3. Locate location input
        # ------------------------------------------------------------
        try:
            inputs = panel.locator(
                "input:visible"
            )

            input_count = inputs.count()

            print(
                "Visible inputs in filter scope:",
                input_count,
            )

            if not input_count:
                print(
                    "[LOCATION ERROR] No visible location input."
                )
                return False

            location_box = None

            for i in range(input_count):
                item = inputs.nth(i)

                try:
                    placeholder = (
                        item.get_attribute("placeholder")
                        or ""
                    )

                    aria = (
                        item.get_attribute("aria-label")
                        or ""
                    )

                    name = (
                        item.get_attribute("name")
                        or ""
                    )

                    metadata = (
                        placeholder
                        + " "
                        + aria
                        + " "
                        + name
                    )

                    print(
                        f"Input #{i + 1}:",
                        repr(metadata),
                    )

                    if re.search(
                        r"location|city|state|place",
                        metadata,
                        re.IGNORECASE,
                    ):
                        location_box = item
                        break

                except Exception:
                    pass

            if location_box is None:
                location_box = inputs.last

                print(
                    "Using last visible input within filter scope."
                )

            location_box.click(
                timeout=10000
            )

            location_box.fill(
                location
            )

            print(
                "Entered location:",
                location,
            )

            self.page.wait_for_timeout(2000)

            print(
                "URL after entering location:",
                self.page.url,
            )

            if bad_navigation(self.page.url):
                print(
                    "[LOCATION ERROR] Typing location caused "
                    "bad navigation."
                )
                return False

            if not valid_people_url(self.page.url):
                print(
                    "[LOCATION ERROR] Typing location changed "
                    "the company People-search URL."
                )
                return False

        except Exception as ex:
            print(
                "[LOCATION ERROR] Location input failed:",
                repr(ex),
            )
            return False

        # ------------------------------------------------------------
        # 4. Select location suggestion
        #
        # DO NOT use ArrowDown + Enter.
        # ------------------------------------------------------------
        try:
            print(
                "-" * 60
            )
            print(
                "SELECTING LOCATION SUGGESTION"
            )

            suggestion = None

            options = self.page.locator(
                "[role='option']:visible"
            )

            option_count = options.count()

            print(
                "Visible options:",
                option_count,
            )

            for i in range(option_count):
                item = options.nth(i)

                try:
                    text = item.inner_text().strip()

                    print(
                        f"Option #{i + 1}:",
                        repr(text),
                    )

                    if text.lower() == location.lower():
                        suggestion = item
                        break

                except Exception:
                    pass

            if suggestion is None:
                exact = self.page.get_by_text(
                    location,
                    exact=True,
                )

                exact_count = exact.count()

                print(
                    "Exact location text matches:",
                    exact_count,
                )

                for i in range(exact_count):
                    item = exact.nth(i)

                    try:
                        if item.is_visible():
                            suggestion = item
                            break
                    except Exception:
                        pass

            if suggestion is None:
                print(
                    "[LOCATION ERROR] Location suggestion not found."
                )
                return False

            suggestion.click(
                timeout=10000
            )

            print(
                "Clicked location suggestion:",
                location,
            )

            self.page.wait_for_timeout(1200)

            print(
                "URL after selecting location:",
                self.page.url,
            )

            if bad_navigation(self.page.url):
                print(
                    "[LOCATION ERROR] Selecting location caused "
                    "bad navigation."
                )
                return False

            if not valid_people_url(self.page.url):
                print(
                    "[LOCATION ERROR] Selecting location changed "
                    "the company People-search URL."
                )
                return False

        except Exception as ex:
            print(
                "[LOCATION ERROR] Location suggestion failed:",
                repr(ex),
            )
            return False

        # ------------------------------------------------------------
        # 5. Click Show results inside active filter UI
        # ------------------------------------------------------------
        try:
            print(
                "-" * 60
            )
            print(
                "CLICKING SHOW RESULTS"
            )

            dialogs = self.page.locator(
                "[role='dialog']:visible"
            )

            if dialogs.count():
                panel = dialogs.last

            show_results = None

            buttons = panel.get_by_role(
                "button",
                name=re.compile(
                    r"^\s*show\s+results\s*$",
                    re.IGNORECASE,
                ),
            )

            button_count = buttons.count()

            print(
                "Scoped Show results buttons:",
                button_count,
            )

            for i in range(button_count):
                item = buttons.nth(i)

                try:
                    if item.is_visible():
                        show_results = item
                        break
                except Exception:
                    pass

            if show_results is None:
                texts = panel.get_by_text(
                    re.compile(
                        r"^\s*show\s+results\s*$",
                        re.IGNORECASE,
                    ),
                )

                text_count = texts.count()

                print(
                    "Scoped Show results text matches:",
                    text_count,
                )

                for i in range(text_count):
                    item = texts.nth(i)

                    try:
                        if item.is_visible():
                            show_results = item
                            break
                    except Exception:
                        pass

            if show_results is None:
                print(
                    "[LOCATION ERROR] Scoped Show results not found."
                )
                return False

            show_results.click(
                timeout=10000
            )

            print(
                "Clicked Show results."
            )

            self.page.wait_for_timeout(5000)

            print(
                "URL after Show results:",
                self.page.url,
            )

            if bad_navigation(self.page.url):
                print(
                    "[LOCATION ERROR] Show results caused "
                    "root/login/authwall navigation."
                )
                return False

            if not valid_people_url(self.page.url):
                print(
                    "[LOCATION ERROR] Show results did not leave "
                    "the selected company's People search."
                )
                return False

        except Exception as ex:
            print(
                "[LOCATION ERROR] Show results failed:",
                repr(ex),
            )
            return False

        # ------------------------------------------------------------
        # 6. Final verification
        # ------------------------------------------------------------
        print(
            "-" * 60
        )
        print(
            "LOCATION FILTER VERIFIED"
        )

        print(
            "Final URL:",
            self.page.url,
        )

        try:
            print(
                "Final title:",
                self.page.title(),
            )
        except Exception:
            pass

        try:
            profiles = self.page.locator(
                "a[href*='/in/']:visible"
            )

            print(
                "Visible /in/ links:",
                profiles.count(),
            )
        except Exception as ex:
            print(
                "Profile diagnostic failed:",
                repr(ex),
            )

        try:
            matches = self.page.get_by_text(
                location,
                exact=False,
            )

            print(
                "Requested-location text matches:",
                matches.count(),
            )
        except Exception as ex:
            print(
                "Location diagnostic failed:",
                repr(ex),
            )

        print("=" * 60)
        print(
            "LOCATION FILTER SUCCESS"
        )
        print("=" * 60)

        return True

    def get_profiles(self, company="", location=""):
        """Discover primary employee profile links from LinkedIn people search."""
        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)
        print("Requested company:", company)
        print("Requested location:", location)

        profiles = []
        seen = set()
        search_area = None

        try:
            main = self.page.locator("main:visible").first
            if main.count():
                search_area = main
                print("Visible LinkedIn main search area found.")
        except Exception as ex:
            print("Visible main inspection failed:", repr(ex))

        if search_area is None:
            for selector in (
                "div.scaffold-finite-scroll__content:visible",
                "div.search-results-container:visible",
                "div[role='main']:visible",
            ):
                try:
                    candidate = self.page.locator(selector).first
                    if candidate.count():
                        search_area = candidate
                        print("Using bounded search-area fallback:", selector)
                        break
                except Exception as ex:
                    print("Search-area fallback failed:", selector, repr(ex))

        if search_area is None:
            print("ERROR: No bounded LinkedIn search area found.")
            return profiles

        def canonical_profile_url(href):
            if not href:
                return ""

            value = href.strip()

            if value.startswith("/"):
                value = "https://www.linkedin.com" + value

            value = value.split("?")[0].split("#")[0].rstrip("/")

            if "/in/" not in value.lower():
                return ""

            return value

        # ------------------------------------------------------------
        # PROFILE CANDIDATE DISCOVERY
        #
        # IMPORTANT:
        # LinkedIn's rendered DOM does not always expose the profile
        # result cards using stable entity-result/title selectors.
        #
        # The previously working implementation successfully discovered
        # the visible /in/ profile links from the bounded main search
        # area. Restore that behavior here.
        #
        # We intentionally DO NOT validate company/location here.
        # SearchWorkflowV2 opens each profile with LinkedInProfilePageV2
        # and validates the actual profile company + location there.
        # ------------------------------------------------------------

        candidate_links = []

        # ------------------------------------------------------------
        # PROFILE CANDIDATE DISCOVERY
        #
        # LinkedIn's live DOM has proven that specific result-card
        # selectors and ancestor heuristics are unreliable.
        #
        # The authenticated currentCompany + location people-search
        # page is already our search boundary.
        #
        # Therefore the discovery layer deliberately does only this:
        #
        #   1. Find visible /in/ profile links in the bounded main area.
        #   2. Canonicalize their URLs.
        #   3. Preserve discovery order.
        #   4. Let SearchWorkflowV2 / LinkedInProfilePageV2 perform the
        #      authoritative company + location validation.
        #
        # DO NOT add company-card or ancestor validation here.
        # ------------------------------------------------------------

        try:

            all_links = search_area.locator(
                "a[href*='/in/']:visible"
            )

            # LinkedIn can finish rendering employee links shortly
            # after the location filter completes.
            try:

                all_links.first.wait_for(
                    state="visible",
                    timeout=10000
                )

            except Exception:

                pass

            total_links = all_links.count()

            print(
                "Visible /in/ profile links in bounded search area:",
                total_links
            )

            if total_links == 0:

                print(
                    "ERROR: No visible LinkedIn /in/ profile links "
                    "found in bounded search area."
                )

                print(
                    "Profiles extracted: 0"
                )

                return profiles


            # --------------------------------------------------------
            # Collect canonical profile candidates.
            # --------------------------------------------------------

            for i in range(
                total_links
            ):

                try:

                    link = all_links.nth(i)

                    href = canonical_profile_url(
                        link.get_attribute(
                            "href"
                        )
                    )

                    if not href:
                        continue

                    candidate_links.append(
                        (
                            100,
                            "bounded-visible-profile-link",
                            link
                        )
                    )

                except Exception as ex:

                    print(
                        "Profile-link inspection failed:",
                        repr(ex)
                    )


        except Exception as ex:

            print(
                "Bounded /in/ profile discovery failed:",
                repr(ex)
            )

            print(
                "Profiles extracted: 0"
            )

            return profiles

        # ------------------------------------------------------------
        # Remove duplicate profile URLs while preserving discovery order.
        # ------------------------------------------------------------

        if candidate_links:
            unique_candidates = []
            candidate_seen = set()

            for score, source, link in candidate_links:
                try:
                    href = canonical_profile_url(
                        link.get_attribute("href")
                    )

                    if not href or href in candidate_seen:
                        continue

                    candidate_seen.add(href)
                    unique_candidates.append(
                        (score, source, link)
                    )

                except Exception as ex:
                    print(
                        "Candidate de-duplication failed:",
                        repr(ex)
                    )

            candidate_links = unique_candidates

        print(
            "Reliable /in/ profile candidates identified:",
            len(candidate_links)
        )

        if not candidate_links:
            print(
                "ERROR: No reliable employee profile links identified."
            )
            return profiles

        for score, source, link in candidate_links:
            try:
                clean_url = canonical_profile_url(
                    link.get_attribute("href")
                )

                if not clean_url or clean_url in seen:
                    continue

                seen.add(clean_url)

                raw_name = ""

                try:
                    raw_name = (
                        link.inner_text(timeout=2000)
                        .strip()
                        .replace("\n", " ")
                    )
                except Exception:
                    pass

                profiles.append(
                    {
                        "full_name": raw_name,
                        "profile_url": clean_url,
                        "company": company,
                        "location": location,
                    }
                )

                print("-" * 60)
                print("Employee candidate:", raw_name)
                print("Candidate URL:", clean_url)
                print("Discovery source:", source)
                print("Discovery score:", score)

            except Exception as ex:
                print(
                    "Profile candidate processing failed:",
                    repr(ex)
                )

        print("=" * 60)
        print(
            "EMPLOYEE PROFILES EXTRACTED:",
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
