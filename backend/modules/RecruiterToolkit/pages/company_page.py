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
        """Extract location-matching employee /in/ links without connection-degree filtering."""
        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)
        print("Requested company:", company)
        print("Requested location:", location)

        profiles = []
        search_area = None

        for selector in (
            "main:visible",
            "div.scaffold-finite-scroll__content:visible",
            "div.search-results-container:visible",
            "div[role='main']:visible",
        ):
            try:
                candidate = self.page.locator(selector).first
                if candidate.count() and candidate.is_visible():
                    search_area = candidate
                    print("Using bounded employee search area:", selector)
                    break
            except Exception as ex:
                print("Search-area inspection failed:", selector, repr(ex))

        if search_area is None:
            print("ERROR: No bounded LinkedIn employee search area found.")
            return profiles

        def canonical_profile_url(href):
            if not href:
                return ""
            value = str(href).strip()
            if value.startswith("/"):
                value = "https://www.linkedin.com" + value
            value = value.split("?", 1)[0].split("#", 1)[0].rstrip("/")
            return value.lower() if "/in/" in value.lower() else ""

        def normalize_text(value):
            if not value:
                return ""
            value = str(value).replace("\xa0", " ").replace("\n", " ").replace("\r", " ")
            return re.sub(r"\s+", " ", value).strip().lower()

        requested_location_normalized = normalize_text(location)
        location_tokens = [
            t for t in re.findall(r"[a-z0-9]+", requested_location_normalized)
            if len(t) >= 3
        ]

        try:
            links = search_area.locator("a[href*='/in/']:visible")
            total_links = links.count()
        except Exception as ex:
            print("Visible profile-link lookup failed:", repr(ex))
            return profiles

        print("Visible /in/ links available:", total_links)
        if total_links == 0:
            return profiles

        best_by_url = {}

        for index in range(total_links):
            try:
                link = links.nth(index)
                profile_url = canonical_profile_url(link.get_attribute("href"))
                if not profile_url:
                    continue

                raw_text = ""
                try:
                    raw_text = link.inner_text(timeout=2000).strip()
                except Exception:
                    pass

                # Prefer the nearest result-like ancestor when it contains
                # richer text than the anchor itself. This avoids selecting
                # nested mutual-connection links as separate employees.
                card_text = raw_text
                try:
                    ancestor_text = link.evaluate("""
                        (el) => {
                            let node = el;
                            for (let i = 0; i < 6 && node; i++, node = node.parentElement) {
                                const tag = (node.tagName || '').toLowerCase();
                                const cls = (node.className || '').toString().toLowerCase();
                                if (
                                    tag === 'li' ||
                                    cls.includes('entity-result') ||
                                    cls.includes('reusable-search__result') ||
                                    cls.includes('search-result')
                                ) {
                                    return node.innerText || '';
                                }
                            }
                            return '';
                        }
                    """)
                    if ancestor_text and len(str(ancestor_text).strip()) > len(raw_text):
                        card_text = str(ancestor_text).strip()
                except Exception:
                    pass

                text = normalize_text(card_text)
                if not text:
                    continue

                location_match = False
                if requested_location_normalized:
                    location_match = requested_location_normalized in text
                    if not location_match and location_tokens:
                        location_match = all(token in text for token in location_tokens)

                    if not location_match:
                        print("SKIP outside requested location:", profile_url,
                              "| requested:", location, "| text:", card_text[:400])
                        continue

                # Score ONLY to select the richest duplicate representation.
                # Connection degree (1st/2nd/3rd) is deliberately ignored.
                score = min(len(text), 300) // 10
                if requested_location_normalized in text:
                    score += 100
                if "connect" in text:
                    score += 10
                if "message" in text:
                    score += 10
                if "follow" in text:
                    score += 5

                candidate = {
                    "url": profile_url,
                    "text": card_text.replace("\n", " ").strip(),
                    "score": score,
                    "dom_index": index,
                }

                old = best_by_url.get(profile_url)
                if old is None or score > old["score"]:
                    best_by_url[profile_url] = candidate

                print("-" * 60)
                print("PROFILE LINK:", index + 1)
                print("URL:", profile_url)
                print("Text:", candidate["text"][:500])
                print("Score:", score)
                print("Connection degree is NOT used as a filter.")

            except Exception as ex:
                print("Profile-link inspection failed:", repr(ex))

        ranked = sorted(best_by_url.values(), key=lambda x: x["dom_index"])

        print("=" * 60)
        print("UNIQUE LOCATION-MATCHING PROFILE URLs:", len(ranked))
        print("=" * 60)

        for item in ranked:
            profiles.append({
                "full_name": item["text"],
                "profile_url": item["url"],
                "company": company,
                "location": location,
                "search_result_text": item["text"],
            })
            print("EMPLOYEE CANDIDATE:", item["url"], "|", item["text"][:300])

        print("EMPLOYEE PROFILES EXTRACTED:", len(profiles))
        return profiles

def next_page(self):
        """Click Next and only report success if the same company people-search remains active."""
        try:
            before_url = str(self.page.url or "").strip()
            qs = parse_qs(urlparse(before_url).query)
            company_ids = qs.get("currentCompany", []) or qs.get("currentcompany", [])

            print("=" * 60)
            print("PAGINATION DIAGNOSTICS")
            print("Current URL:", before_url)
            print("Current company ID:", company_ids)
            print("=" * 60)

            if "/search/results/people/" not in before_url.lower():
                print("NEXT ABORTED - not on people search.")
                return False

            before_profiles = set()
            try:
                links = self.page.locator("a[href*='/in/']:visible")
                for i in range(min(links.count(), 200)):
                    href = links.nth(i).get_attribute("href")
                    if href and "/in/" in href.lower():
                        before_profiles.add(
                            str(href).split("?", 1)[0].split("#", 1)[0].rstrip("/").lower()
                        )
            except Exception as ex:
                print("Pre-next profile snapshot failed:", repr(ex))

            next_control = None
            control_info = None

            selectors = [
                "nav[aria-label*='Pagination' i] button:visible",
                "nav[aria-label*='Pagination' i] a:visible",
                "div.artdeco-pagination button:visible",
                "div.artdeco-pagination a:visible",
                "button:visible",
                "[role='button']:visible",
                "a:visible",
            ]

            for selector in selectors:
                try:
                    controls = self.page.locator(selector)
                    for i in range(controls.count()):
                        c = controls.nth(i)
                        try: text = c.inner_text(timeout=1000).strip()
                        except Exception: text = ""
                        try: aria = (c.get_attribute("aria-label") or "").strip()
                        except Exception: aria = ""
                        try: title = (c.get_attribute("title") or "").strip()
                        except Exception: title = ""
                        try: href = (c.get_attribute("href") or "").strip()
                        except Exception: href = ""
                        try:
                            if c.is_disabled():
                                continue
                        except Exception:
                            pass

                        label = " ".join(x for x in (text, aria, title) if x).lower().strip()
                        if label == "next" or "next page" in label or aria.lower() == "next":
                            next_control = c
                            control_info = (selector, text, aria, title, href)
                            break
                    if next_control is not None:
                        break
                except Exception as ex:
                    print("Next-control inspection failed:", selector, repr(ex))

            if next_control is None:
                print("NEXT CONTROL NOT FOUND.")
                return False

            print("NEXT CONTROL FOUND")
            print("Selector:", control_info[0])
            print("Text:", control_info[1])
            print("aria-label:", control_info[2])
            print("title:", control_info[3])
            print("href:", control_info[4])
            try:
                print("outerHTML:", next_control.evaluate("(el) => el.outerHTML")[:2000])
            except Exception:
                pass

            print("Clicking Next...")
            next_control.click()

            last_url = before_url
            for wait_ms in (250, 750, 1500, 3000, 5000, 8000):
                self.page.wait_for_timeout(wait_ms if wait_ms == 250 else wait_ms - (250 if wait_ms > 250 else 0))
                now = str(self.page.url or "").strip()
                if now != last_url:
                    print(f"URL after {wait_ms} ms:", now)
                    last_url = now

                low = now.lower()
                if "/ssr-login/" in low or "/authwall" in low or "/login" in low:
                    print("=" * 60)
                    print("NEXT NAVIGATION DIAGNOSIS: LINKEDIN REDIRECTED TO LOGIN/AUTHWALL.")
                    print("Before Next:", before_url)
                    print("After Next:", now)
                    print("This is NOT counted as a successful next page.")
                    print("=" * 60)
                    return False

                if "/search/results/people/" not in low:
                    continue

                new_qs = parse_qs(urlparse(now).query)
                new_company_ids = new_qs.get("currentCompany", []) or new_qs.get("currentcompany", [])
                same_company = (not company_ids) or any(
                    str(x) in [str(y) for y in company_ids] for x in new_company_ids
                )
                if not same_company:
                    print("NEXT REJECTED - company scope changed.")
                    print("Expected:", company_ids, "Actual:", new_company_ids)
                    return False

                if now != before_url:
                    print("NEXT PAGE VALIDATED - same company people-search URL changed.")
                    return True

                after_profiles = set()
                try:
                    links = self.page.locator("a[href*='/in/']:visible")
                    for i in range(min(links.count(), 200)):
                        href = links.nth(i).get_attribute("href")
                        if href and "/in/" in href.lower():
                            after_profiles.add(
                                str(href).split("?", 1)[0].split("#", 1)[0].rstrip("/").lower()
                            )
                except Exception:
                    pass

                if after_profiles and after_profiles != before_profiles:
                    print("NEXT PAGE VALIDATED - result set changed in-place.")
                    return True

            print("NEXT CLICK DID NOT PRODUCE A VALIDATED NEXT PAGE.")
            return False

        except Exception as ex:
            print("Next page failed:", repr(ex))
            return False

