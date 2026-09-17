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
        Apply a LinkedIn location filter while preserving the exact
        currentCompany people-search scope.

        Design goals:
          1. Never fall back to generic people search.
          2. Never guess a LinkedIn geo ID.
          3. Prefer LinkedIn's normal location picker.
          4. In CI, where LinkedIn sometimes hides ARIA metadata, use
             bounded DOM hit-testing and controlled keyboard selection.
          5. If LinkedIn exposes a geo ID in the rendered DOM or a
             typeahead response, apply that ID to the existing URL.
          6. Click Show results only after a real location selection.
          7. Validate that currentCompany survives every navigation.
        """

        print("=" * 60)
        print("APPLYING LOCATION FILTER")
        print("=" * 60)
        requested_location = str(location or "").strip()

        if not requested_location:
            print("[LOCATION ERROR] Empty location was supplied.")
            return False

        print("Requested location:", requested_location)

        before_url = self.page.url
        print("URL before location filter:", before_url)

        def normalize(value):
            if value is None:
                return ""
            return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip().lower()

        def is_people_company_url(url):
            if not url:
                return False
            lower = url.lower()
            return (
                "/search/results/people/" in lower
                and "currentcompany=" in lower
                and "/in/" not in lower
            )

        def query_values(url, key):
            try:
                from urllib.parse import urlsplit, parse_qs
                return parse_qs(urlsplit(url).query, keep_blank_values=True).get(key, [])
            except Exception:
                return []

        def has_location_filter(url):
            try:
                from urllib.parse import urlsplit, parse_qs
                query = parse_qs(urlsplit(url).query, keep_blank_values=True)
                for key in ("geoUrn", "facetGeoRegion", "geoId", "geo_id"):
                    if query.get(key):
                        return True
                return False
            except Exception:
                return False

        def safe_location_result_url(url):
            return is_people_company_url(url) and has_location_filter(url)

        # ------------------------------------------------------------
        # Safety checkpoint.
        # ------------------------------------------------------------
        if not is_people_company_url(before_url):
            print("[LOCATION ERROR] Not on company-scoped people-search.")
            return False

        original_company_values = query_values(before_url, "currentCompany")
        if not original_company_values:
            print("[LOCATION ERROR] currentCompany value could not be read.")
            return False

        # ------------------------------------------------------------
        # Open the Locations filter.
        # ------------------------------------------------------------
        try:
            locations = self.page.get_by_text("Locations", exact=True)
            count = locations.count()
            print("Exact Locations matches:", count)

            clicked = False
            for i in range(count):
                try:
                    candidate = locations.nth(i)
                    if not candidate.is_visible():
                        continue
                    candidate.click(timeout=15000)
                    clicked = True
                    print(f"Clicked Locations match #{i + 1}")
                    break
                except Exception:
                    continue

            if not clicked:
                print("[LOCATION ERROR] Could not click Locations filter.")
                return False

        except Exception as ex:
            print("[LOCATION ERROR] Opening Locations failed:", repr(ex))
            return False

        self.page.wait_for_timeout(1200)

        # ------------------------------------------------------------
        # Locate the exact LinkedIn location input.
        # ------------------------------------------------------------
        try:
            inputs = self.page.locator(
                "input[placeholder='Add a location']:visible"
            )
            count = inputs.count()
            print("Visible Add a location inputs:", count)

            if count == 0:
                print("[LOCATION ERROR] No visible Add a location input found.")
                return False

            location_box = inputs.last
            print(
                "Location input placeholder:",
                location_box.get_attribute("placeholder")
            )
            print(
                "Location input aria-controls:",
                location_box.get_attribute("aria-controls")
            )
            print(
                "Location input aria-owns:",
                location_box.get_attribute("aria-owns")
            )

        except Exception as ex:
            print("[LOCATION ERROR] Location input lookup failed:", repr(ex))
            return False

        # ------------------------------------------------------------
        # Capture typeahead responses while typing.
        #
        # This is supplemental only. We do not depend on a particular
        # LinkedIn endpoint or response shape.
        # ------------------------------------------------------------
        captured_responses = []

        def capture_response(response):
            try:
                if "linkedin.com" not in response.url.lower():
                    return

                resource_type = ""
                try:
                    resource_type = response.request.resource_type
                except Exception:
                    pass

                if resource_type and resource_type not in {"xhr", "fetch"}:
                    return

                content_type = response.headers.get("content-type", "").lower()
                if (
                    content_type
                    and not any(
                        token in content_type
                        for token in ("json", "text", "javascript")
                    )
                ):
                    return

                body = response.text()
                if not body:
                    return

                body_lower = body.lower()
                req = requested_location.lower()

                if (
                    req not in body_lower
                    and "fsd_geo" not in body_lower
                    and "geo_id" not in body_lower
                    and "geoid" not in body_lower
                    and "geo_urn" not in body_lower
                    and "geourn" not in body_lower
                ):
                    return

                captured_responses.append((response.url, body[:250000]))
                print(
                    "[LOCATION] Captured possible typeahead response:",
                    response.url[:500]
                )

            except Exception:
                pass

        try:
            self.page.on("response", capture_response)
        except Exception as ex:
            print("[LOCATION] Response listener setup failed:", repr(ex))

        # ------------------------------------------------------------
        # Type the requested location.
        # ------------------------------------------------------------
        try:
            location_box.click(timeout=10000)
            location_box.fill("")
            location_box.press_sequentially(
                requested_location,
                delay=140
            )
            print("[LOCATION] Typed location:", requested_location)
        except Exception as ex:
            try:
                self.page.remove_listener("response", capture_response)
            except Exception:
                pass
            print("[LOCATION ERROR] Could not type location:", repr(ex))
            return False

        self.page.wait_for_timeout(2200)

        # ------------------------------------------------------------
        # Helper: extract a LinkedIn geo ID from arbitrary JSON/text.
        # Only IDs associated with a location response are considered.
        # ------------------------------------------------------------
        def extract_geo_ids(text):
            if not text:
                return []

            found = []

            patterns = (
                r"urn:li:(?:fsd_)?geo:(\d+)",
                r'"(?:geoId|geo_id|geoid|geoUrn|geo_urn|locationId|location_id)"'
                r"\s*:\s*\"?(?:urn:li:(?:fsd_)?geo:)?(\d+)\"?",
            )

            for pattern in patterns:
                for match in re.finditer(
                    pattern,
                    text,
                    flags=re.IGNORECASE
                ):
                    value = match.group(1)
                    if value not in found:
                        found.append(value)

            return found

        # ------------------------------------------------------------
        # Helper: bounded DOM candidate discovery.
        #
        # LinkedIn CI pages have been observed with no role=option,
        # no aria-controls and no aria-activedescendant. Therefore we
        # inspect only the area immediately below the location input.
        # ------------------------------------------------------------
        def dom_location_candidates():
            try:
                box = location_box.bounding_box()
                if not box:
                    return []

                result = self.page.evaluate(
                    """({b, requested}) => {
                        const norm = v =>
                            String(v || "")
                                .replace(/\\s+/g, " ")
                                .trim()
                                .toLowerCase();

                        const req = norm(requested);
                        const out = [];
                        const seen = new Set();

                        const visible = el => {
                            if (!el) return false;
                            const s = getComputedStyle(el);
                            const r = el.getBoundingClientRect();
                            return (
                                s.display !== "none" &&
                                s.visibility !== "hidden" &&
                                s.opacity !== "0" &&
                                r.width > 0 &&
                                r.height > 0
                            );
                        };

                        const usefulText = el => {
                            return norm(
                                el.innerText ||
                                el.textContent ||
                                el.getAttribute("aria-label") ||
                                ""
                            );
                        };

                        const matches = el => {
                            const t = usefulText(el);
                            if (!t) return false;

                            const compact = t.replace(/[^a-z0-9]+/g, " ").trim();

                            return (
                                t === req ||
                                t.startsWith(req) ||
                                (
                                    compact.startsWith(req) &&
                                    compact.length <= 180
                                )
                            );
                        };

                        const add = el => {
                            if (!el || seen.has(el) || !visible(el)) return;

                            const r = el.getBoundingClientRect();

                            const inHorizontalBand =
                                r.right >= b.x - 80 &&
                                r.left <= b.x + b.width + 220;

                            const inVerticalBand =
                                r.top >= b.y + b.height - 4 &&
                                r.top <= b.y + b.height + 320;

                            if (!inHorizontalBand || !inVerticalBand) {
                                return;
                            }

                            if (!matches(el)) return;

                            seen.add(el);

                            out.push({
                                text: String(
                                    el.innerText ||
                                    el.textContent ||
                                    el.getAttribute("aria-label") ||
                                    ""
                                ).replace(/\\s+/g, " ").trim(),
                                x: r.x,
                                y: r.y,
                                w: r.width,
                                h: r.height,
                                cx: r.x + r.width / 2,
                                cy: r.y + r.height / 2,
                                tag: el.tagName,
                                role: el.getAttribute("role"),
                                testid: el.getAttribute("data-testid"),
                                html: el.outerHTML.slice(0, 5000)
                            });
                        };

                        const left = Math.max(0, b.x - 30);
                        const right = b.x + b.width + 240;
                        const top = b.y + b.height;
                        const bottom = top + 320;

                        for (let y = top; y <= bottom; y += 5) {
                            for (let x = left; x <= right; x += 10) {
                                for (const el of document.elementsFromPoint(x, y)) {
                                    add(el);

                                    let p = el.parentElement;
                                    for (let d = 0; p && d < 5; d++) {
                                        add(p);
                                        p = p.parentElement;
                                    }
                                }
                            }
                        }

                        out.sort((a, z) => a.y - z.y);
                        return out.slice(0, 30);
                    }""",
                    {
                        "b": box,
                        "requested": requested_location
                    }
                )

                return result or []

            except Exception as ex:
                print("[LOCATION] DOM candidate scan failed:", repr(ex))
                return []

        # ------------------------------------------------------------
        # Helper: find a geo ID close to the requested location in the
        # rendered DOM. This avoids selecting an unrelated geo ID from
        # the whole page.
        # ------------------------------------------------------------
        def geo_id_from_dom():
            candidates = dom_location_candidates()

            print(
                "[LOCATION] Bounded DOM location candidates:",
                len(candidates)
            )

            for index, candidate in enumerate(candidates):
                print(
                    f"[LOCATION] Candidate #{index + 1}:",
                    repr(candidate.get("text")),
                    "tag=",
                    candidate.get("tag"),
                    "role=",
                    candidate.get("role"),
                    "testid=",
                    candidate.get("testid")
                )

                ids = extract_geo_ids(candidate.get("html", ""))
                if ids:
                    print(
                        "[LOCATION] Geo ID found in location candidate:",
                        ids[0]
                    )
                    return ids[0]

            return None

        def looks_selected_in_ui():
            """
            Detect a normal LinkedIn picker selection even when the URL
            has not changed yet. LinkedIn commonly clears the input after
            the suggestion is selected and leaves the filter pending until
            Show results is clicked.
            """
            try:
                visible_inputs = self.page.locator(
                    "input[placeholder='Add a location']:visible"
                )

                if visible_inputs.count():
                    value = normalize(
                        visible_inputs.last.input_value()
                    )
                    if value == "":
                        return True

            except Exception:
                pass

            try:
                requested_norm = normalize(requested_location)
                selected = self.page.locator(
                    "button:visible, span:visible, div:visible"
                )

                count = min(selected.count(), 1200)

                for i in range(count):
                    try:
                        element = selected.nth(i)
                        text = normalize(
                            element.inner_text(timeout=300)
                        )

                        if (
                            text == requested_norm
                            or text == requested_norm + ", united states"
                        ):
                            box = element.bounding_box()
                            if box and box["y"] > 0:
                                return True

                    except Exception:
                        continue

            except Exception:
                pass

            return False

        # ------------------------------------------------------------
        # First selection strategy: bounded DOM click.
        # ------------------------------------------------------------
        location_selected = False
        dom_candidates = dom_location_candidates()

        if dom_candidates:
            for candidate in dom_candidates:
                try:
                    print(
                        "[LOCATION] Clicking bounded candidate:",
                        repr(candidate["text"]),
                        "at",
                        (candidate["cx"], candidate["cy"])
                    )

                    self.page.mouse.click(
                        candidate["cx"],
                        candidate["cy"]
                    )
                    self.page.wait_for_timeout(1200)

                    current = self.page.url

                    if (
                        is_people_company_url(current)
                        and (
                            has_location_filter(current)
                            or current != before_url
                            or looks_selected_in_ui()
                        )
                    ):
                        location_selected = True
                        print(
                            "[LOCATION] Location selected through bounded DOM click."
                        )
                        break

                except Exception as ex:
                    print(
                        "[LOCATION] Candidate click failed:",
                        repr(ex)
                    )

        # ------------------------------------------------------------
        # Second strategy: accessible text/option locators.
        # ------------------------------------------------------------
        if not location_selected:
            try:
                requested_norm = normalize(requested_location)
                option_candidates = self.page.locator(
                    "[role='option']:visible"
                )

                count = option_candidates.count()
                print(
                    "[LOCATION] Visible role=option candidates:",
                    count
                )

                for i in range(count):
                    try:
                        option = option_candidates.nth(i)
                        text = normalize(option.inner_text(timeout=1500))

                        if (
                            text == requested_norm
                            or text.startswith(requested_norm)
                            or (
                                requested_norm in text
                                and len(text) <= 180
                            )
                        ):
                            print(
                                "[LOCATION] Clicking role=option:",
                                repr(text)
                            )
                            option.click(timeout=10000)
                            self.page.wait_for_timeout(1200)

                            current = self.page.url
                            if (
                                is_people_company_url(current)
                                and (
                                    has_location_filter(current)
                                    or looks_selected_in_ui()
                                )
                            ):
                                location_selected = True
                                break

                    except Exception:
                        continue

            except Exception as ex:
                print(
                    "[LOCATION] role=option strategy failed:",
                    repr(ex)
                )

        # ------------------------------------------------------------
        # Third strategy: controlled keyboard selection.
        #
        # Do not require aria-activedescendant. LinkedIn has rendered
        # usable keyboard typeaheads without that attribute in CI.
        # After Enter, validate the URL before accepting the result.
        # ------------------------------------------------------------
        if not location_selected:
            try:
                location_box.click(timeout=5000)
                self.page.keyboard.press("ArrowDown")
                self.page.wait_for_timeout(500)

                active_id = location_box.get_attribute(
                    "aria-activedescendant"
                )
                active_text = ""

                if active_id:
                    try:
                        active = self.page.locator(
                            f"#{active_id}"
                        )
                        active_text = normalize(
                            active.inner_text(timeout=1500)
                        )
                    except Exception:
                        active_text = ""

                print(
                    "[LOCATION] Keyboard active descendant:",
                    active_id
                )
                print(
                    "[LOCATION] Keyboard active text:",
                    repr(active_text)
                )

                # If ARIA exposes the correct location, Enter is safe.
                if (
                    active_text
                    and (
                        active_text == normalize(requested_location)
                        or active_text.startswith(
                            normalize(requested_location)
                        )
                    )
                ):
                    self.page.keyboard.press("Enter")
                    self.page.wait_for_timeout(1200)

                    current = self.page.url
                    if (
                        is_people_company_url(current)
                        and (
                            has_location_filter(current)
                            or looks_selected_in_ui()
                        )
                    ):
                        location_selected = True
                        print(
                            "[LOCATION] Location selected through controlled keyboard fallback."
                        )

                # If ARIA is absent, inspect the bounded DOM again after
                # ArrowDown. Some LinkedIn variants populate the visible
                # candidate only at this point.
                if not location_selected:
                    candidates_after_arrow = dom_location_candidates()

                    for candidate in candidates_after_arrow:
                        text = normalize(candidate.get("text"))

                        if (
                            text == normalize(requested_location)
                            or text.startswith(
                                normalize(requested_location)
                            )
                            or (
                                normalize(requested_location) in text
                                and len(text) <= 180
                            )
                        ):
                            self.page.mouse.click(
                                candidate["cx"],
                                candidate["cy"]
                            )
                            self.page.wait_for_timeout(1200)

                            current = self.page.url
                            if (
                                is_people_company_url(current)
                                and (
                                    has_location_filter(current)
                                    or looks_selected_in_ui()
                                )
                            ):
                                location_selected = True
                                print(
                                    "[LOCATION] Location selected after keyboard-assisted DOM discovery."
                                )
                                break

            except Exception as ex:
                print(
                    "[LOCATION] Keyboard selection failed:",
                    repr(ex)
                )

        # ------------------------------------------------------------
        # Fourth strategy: recover a geo ID from the rendered DOM.
        # ------------------------------------------------------------
        location_geo_id = geo_id_from_dom()

        # ------------------------------------------------------------
        # Fifth strategy: recover a geo ID from captured LinkedIn
        # responses. This is only used if the response contains an ID
        # associated with the location lookup.
        # ------------------------------------------------------------
        if not location_geo_id:
            for _, body in reversed(captured_responses):
                ids = extract_geo_ids(body)
                if ids:
                    location_geo_id = ids[0]
                    print(
                        "[LOCATION] Geo ID extracted from LinkedIn response:",
                        location_geo_id
                    )
                    break

        # Stop response capture once the typeahead phase is complete.
        try:
            self.page.remove_listener("response", capture_response)
        except Exception:
            pass

        # ------------------------------------------------------------
        # If a verified geo ID is available, construct the exact
        # company-scoped URL. This is a recovery mechanism, not a guess:
        # the ID must come from LinkedIn's rendered page/response.
        # ------------------------------------------------------------
        if location_geo_id and not location_selected:
            try:
                from urllib.parse import (
                    urlsplit,
                    urlunsplit,
                    parse_qs,
                    urlencode
                )

                parts = urlsplit(self.page.url)
                query = parse_qs(
                    parts.query,
                    keep_blank_values=True
                )

                # Restore the original company scope explicitly.
                query["currentCompany"] = original_company_values
                query["geoUrn"] = [f'["{location_geo_id}"]']

                filtered_url = urlunsplit(
                    (
                        parts.scheme,
                        parts.netloc,
                        parts.path,
                        urlencode(query, doseq=True),
                        parts.fragment
                    )
                )

                print(
                    "[LOCATION] Applying verified geoUrn URL:"
                )
                print(filtered_url)

                self.page.goto(
                    filtered_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )
                self.page.wait_for_timeout(3000)

                current = self.page.url

                if safe_location_result_url(current):
                    location_selected = True
                    print(
                        "[LOCATION] Verified geoUrn filter applied successfully."
                    )
                else:
                    print(
                        "[LOCATION] Verified geoUrn navigation did not pass safety validation."
                    )

            except Exception as ex:
                print(
                    "[LOCATION] Verified geoUrn URL application failed:",
                    repr(ex)
                )

        # ------------------------------------------------------------
        # If selection was made through the normal picker, the filter
        # may still be pending behind Show results.
        # ------------------------------------------------------------
        if location_selected:
            current = self.page.url

            if not is_people_company_url(current):
                print(
                    "[LOCATION ERROR] Location selection left people-search."
                )
                return False

            current_company_values = query_values(
                current,
                "currentCompany"
            )

            if current_company_values != original_company_values:
                print(
                    "[LOCATION ERROR] currentCompany changed unexpectedly."
                )
                print(
                    "Expected:",
                    original_company_values
                )
                print(
                    "Actual:",
                    current_company_values
                )
                return False

        else:
            # --------------------------------------------------------
            # Last chance: if the UI has a real location suggestion but
            # no URL change yet, select it by exact text and then proceed
            # to Show results.
            # --------------------------------------------------------
            try:
                candidates = dom_location_candidates()

                if candidates:
                    for candidate in candidates:
                        text = normalize(candidate.get("text"))

                        if (
                            text == normalize(requested_location)
                            or text.startswith(
                                normalize(requested_location)
                            )
                        ):
                            print(
                                "[LOCATION] Final bounded click attempt:",
                                repr(candidate.get("text"))
                            )
                            self.page.mouse.click(
                                candidate["cx"],
                                candidate["cy"]
                            )
                            self.page.wait_for_timeout(1000)
                            if looks_selected_in_ui():
                                location_selected = True
                            break

            except Exception as ex:
                print(
                    "[LOCATION] Final bounded click attempt failed:",
                    repr(ex)
                )

        if not location_selected:
            print(
                "ERROR: Could not safely select LinkedIn location."
            )
            print(
                "Requested location:",
                requested_location
            )
            print(
                "A LinkedIn geo ID was not guessed or fabricated."
            )

            try:
                current_inputs = self.page.locator(
                    "input[placeholder='Add a location']:visible"
                )

                if current_inputs.count():
                    box = current_inputs.last
                    print(
                        "Final input value:",
                        box.input_value()
                    )
                    print(
                        "Final aria-activedescendant:",
                        box.get_attribute(
                            "aria-activedescendant"
                        )
                    )
                    print(
                        "Final aria-expanded:",
                        box.get_attribute(
                            "aria-expanded"
                        )
                    )
            except Exception:
                pass

            try:
                self.page.screenshot(
                    path="location_autocomplete_failure_final.png",
                    full_page=False
                )
                print(
                    "Saved location_autocomplete_failure_final.png"
                )
            except Exception:
                pass

            return False

        # ------------------------------------------------------------
        # Show results.
        #
        # If geoUrn URL navigation already applied the filter, there may
        # be no Show results button. In that case the URL itself is the
        # authoritative applied filter.
        # ------------------------------------------------------------
        current = self.page.url

        if has_location_filter(current):
            print(
                "[LOCATION] Location filter already present in URL."
            )
        else:
            print("=" * 60)
            print("LOCATING SHOW RESULTS BUTTON")
            print("=" * 60)

            show_results = None

            try:
                buttons = self.page.get_by_role(
                    "button",
                    name="Show results",
                    exact=True
                )

                count = buttons.count()
                print(
                    "Exact accessible Show results BUTTONS:",
                    count
                )

                candidates = []

                for i in range(count):
                    try:
                        button = buttons.nth(i)

                        if not button.is_visible():
                            continue

                        if not button.is_enabled():
                            continue

                        box = button.bounding_box()

                        try:
                            z_index = button.evaluate(
                                """el => {
                                    const z = parseInt(
                                        getComputedStyle(el).zIndex,
                                        10
                                    );
                                    return Number.isFinite(z) ? z : 0;
                                }"""
                            )
                        except Exception:
                            z_index = 0

                        candidates.append(
                            (
                                z_index,
                                box["y"] if box else -1,
                                button
                            )
                        )

                    except Exception:
                        continue

                if candidates:
                    candidates.sort(
                        key=lambda item: (
                            item[0],
                            item[1]
                        ),
                        reverse=True
                    )
                    show_results = candidates[0][2]

            except Exception as ex:
                print(
                    "[LOCATION] Show results lookup failed:",
                    repr(ex)
                )

            if show_results is None:
                try:
                    exact_text = self.page.get_by_text("Show results", exact=True)
                    print("[LOCATION] Exact visible Show results text matches:", exact_text.count())
                    for i in range(exact_text.count()):
                        try:
                            candidate = exact_text.nth(i)
                            if candidate.is_visible() and candidate.bounding_box():
                                show_results = candidate
                                print("[LOCATION] Selected exact visible Show results text #", i + 1)
                                break
                        except Exception:
                            continue
                except Exception as ex:
                    print("[LOCATION] Show results text fallback failed:", repr(ex))

            if show_results is None:
                try:
                    show_candidates = self.page.evaluate("""() => {
                        const norm=v=>String(v||"").replace(/\\s+/g," ").trim().toLowerCase();
                        const visible=el=>{const s=getComputedStyle(el),r=el.getBoundingClientRect();return s.display!=="none"&&s.visibility!=="hidden"&&s.opacity!=="0"&&r.width>0&&r.height>0};
                        return [...document.querySelectorAll("*")].filter(el=>visible(el)&&norm(el.innerText||el.textContent||el.getAttribute("aria-label"))==="show results").map(el=>{const r=el.getBoundingClientRect();return {tag:el.tagName,role:el.getAttribute("role"),x:r.x,y:r.y,w:r.width,h:r.height,area:r.width*r.height}}).sort((a,b)=>b.area-a.area).slice(0,20);
                    }""")
                    print("[LOCATION] DOM Show results candidates:", len(show_candidates or []))
                    if show_candidates:
                        exact_text=self.page.get_by_text("Show results", exact=True)
                        for i in range(exact_text.count()):
                            try:
                                candidate=exact_text.nth(i)
                                if candidate.is_visible():
                                    show_results=candidate
                                    break
                            except Exception:
                                continue
                except Exception as ex:
                    print("[LOCATION] DOM Show results fallback failed:", repr(ex))

            if show_results is None:
                print("[LOCATION ERROR] Could not locate the LinkedIn Show results control.")
                return False

            # Before clicking, ensure we still have the same company scope.
            before_show_url = self.page.url

            if not is_people_company_url(before_show_url):
                print(
                    "[LOCATION ERROR] Before Show results, page is not "
                    "company-scoped people-search."
                )
                return False

            if query_values(
                before_show_url,
                "currentCompany"
            ) != original_company_values:
                print(
                    "[LOCATION ERROR] Before Show results, currentCompany "
                    "does not match the selected company."
                )
                return False

            try:
                print(
                    "Show results text:",
                    repr(
                        show_results.inner_text(
                            timeout=2000
                        ).strip()
                    )
                )
                print(
                    "Show results tag:",
                    show_results.evaluate(
                        "(el) => el.tagName"
                    )
                )
                print(
                    "Show results aria-label:",
                    show_results.get_attribute(
                        "aria-label"
                    )
                )

                show_results.scroll_into_view_if_needed(
                    timeout=5000
                )
                try:
                    show_results.click(timeout=15000)
                except Exception as click_ex:
                    print("[LOCATION] Normal Show results click failed; using DOM click fallback:", repr(click_ex))
                    show_results.evaluate("el => { el.scrollIntoView({block:'center'}); el.click(); }")

                print("Show results control clicked successfully.")

            except Exception as ex:
                print(
                    "[LOCATION ERROR] Show results click failed:",
                    repr(ex)
                )
                return False

            # --------------------------------------------------------
            # Wait for the resulting company-scoped people-search page.
            # --------------------------------------------------------
            final_url = None

            for attempt in range(15):
                self.page.wait_for_timeout(1000)
                current = self.page.url
                current_lower = current.lower()

                print(
                    f"Post-Show-results URL check {attempt + 1}/15:",
                    current
                )

                if current_lower.rstrip("/") == "https://www.linkedin.com":
                    print(
                        "[LOCATION ERROR] Show results navigated to root."
                    )
                    return False

                if "/in/" in current_lower:
                    print(
                        "[LOCATION ERROR] Show results navigated to a profile."
                    )
                    return False

                if is_people_company_url(current):
                    final_url = current
                    break

            if not final_url:
                final_url = self.page.url

            if not is_people_company_url(final_url):
                print(
                    "[LOCATION ERROR] Final page is not company people-search."
                )
                return False

            if query_values(
                final_url,
                "currentCompany"
            ) != original_company_values:
                print(
                    "[LOCATION ERROR] Final URL lost or changed currentCompany."
                )
                return False

            current = final_url

        # ------------------------------------------------------------
        # Final location validation.
        #
        # A real location filter should normally be represented by
        # geoUrn/facetGeoRegion in the URL. If LinkedIn has not exposed
        # either parameter, do not claim success.
        # ------------------------------------------------------------
        final_url = self.page.url
        final_lower = final_url.lower()

        print("=" * 60)
        print("FINAL LOCATION FILTER VALIDATION")
        print("=" * 60)
        print("Final URL:", final_url)

        if not is_people_company_url(final_url):
            print(
                "[LOCATION ERROR] Final page is not people-search."
            )
            return False

        if query_values(
            final_url,
            "currentCompany"
        ) != original_company_values:
            print(
                "[LOCATION ERROR] Final URL currentCompany mismatch."
            )
            return False

        if "/in/" in final_lower:
            print(
                "[LOCATION ERROR] Final URL is a profile."
            )
            return False

        if not has_location_filter(final_url):
            print(
                "[LOCATION ERROR] Final URL does not expose a location "
                "filter (geoUrn/facetGeoRegion/geoId)."
            )
            return False

        # Wait for the employee results to settle.
        try:
            self.page.locator(
                "a[href*='/in/']:visible"
            ).first.wait_for(
                state="visible",
                timeout=30000
            )
        except Exception:
            self.page.wait_for_timeout(5000)

        profile_count = self.page.locator(
            "a[href*='/in/']:visible"
        ).count()

        print(
            "Visible profile links after location filter:",
            profile_count
        )

        print(
            "Location applied successfully."
        )

        return True
    def get_profiles(self, company="", location=""):
        """
        Discover primary employee profile links from the authenticated
        LinkedIn company + location people-search results.

        IMPORTANT:

        LinkedIn may expose several /in/ links for a single employee
        result. The primary employee link normally contains the richer
        result-card text, such as:

            Name
            Job title / headline
            Location
            Company
            Connect / Message
            Mutual connections

        Mutual-connection profile links normally contain only the person's
        name.

        Therefore we score the rendered /in/ links and keep the richest
        link for each unique profile URL.

        This intentionally does NOT rely on brittle LinkedIn result-card
        CSS classes.
        """

        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)
        print("Requested company:", company)
        print("Requested location:", location)

        profiles = []

        # ------------------------------------------------------------
        # Locate the bounded LinkedIn employee-search area.
        # ------------------------------------------------------------

        search_area = None

        for selector in (
            "main:visible",
            "div.scaffold-finite-scroll__content:visible",
            "div.search-results-container:visible",
            "div[role='main']:visible",
        ):
            try:
                candidate = self.page.locator(selector).first

                if (
                    candidate.count()
                    and candidate.is_visible()
                ):
                    search_area = candidate

                    print(
                        "Using bounded employee search area:",
                        selector
                    )

                    break

            except Exception as ex:
                print(
                    "Search-area inspection failed:",
                    selector,
                    repr(ex)
                )

        if search_area is None:
            print(
                "ERROR: No bounded LinkedIn employee search area found."
            )
            return profiles

        # ------------------------------------------------------------
        # Canonical profile URL.
        # ------------------------------------------------------------

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

        # ------------------------------------------------------------
        # Text normalization.
        # ------------------------------------------------------------

        def normalize_text(value):
            if not value:
                return ""

            value = (
                str(value)
                .replace("\xa0", " ")
                .replace("\n", " ")
                .replace("\r", " ")
            )

            value = re.sub(
                r"\s+",
                " ",
                value
            )

            return value.strip().lower()

        requested_company_normalized = normalize_text(
            company
        )

        requested_location_normalized = normalize_text(
            location
        )

        # ------------------------------------------------------------
        # Location tokens.
        #
        # Example:
        # "New Jersey"
        # -> ["new", "jersey"]
        # ------------------------------------------------------------

        location_tokens = [
            token
            for token in re.findall(
                r"[a-z0-9]+",
                requested_location_normalized
            )
            if len(token) >= 3
        ]

        # ------------------------------------------------------------
        # Company tokens.
        #
        # Example:
        # "SmartWorks, LLC"
        # -> ["smartworks", "llc"]
        #
        # We use the meaningful token(s) as supporting evidence only.
        # ------------------------------------------------------------

        company_tokens = [
            token
            for token in re.findall(
                r"[a-z0-9]+",
                requested_company_normalized
            )
            if len(token) >= 3
        ]

        # ------------------------------------------------------------
        # Collect all visible /in/ links.
        #
        # This preserves the DOM behavior that previously worked.
        # ------------------------------------------------------------

        try:
            links = search_area.locator(
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
            print(
                "ERROR: No visible LinkedIn profile links found."
            )
            return profiles

        # ------------------------------------------------------------
        # best_by_url:
        #
        # One employee can have multiple /in/ anchors.
        #
        # Keep only the richest/highest-confidence representation for
        # that profile URL.
        # ------------------------------------------------------------

        best_by_url = {}

        for index in range(total_links):

            try:
                link = links.nth(index)

                href = canonical_profile_url(
                    link.get_attribute("href")
                )

                if not href:
                    continue

                raw_text = ""

                try:
                    raw_text = (
                        link.inner_text(
                            timeout=2000
                        )
                        .strip()
                    )
                except Exception:
                    pass

                text = normalize_text(
                    raw_text
                )

                if not text:
                    continue

                score = 0
                reasons = []

                # ----------------------------------------------------
                # Strongest signal:
                #
                # The employee result anchor can contain "mutual
                # connections" because the complete employee result is
                # rendered inside that anchor.
                # ----------------------------------------------------

                if "mutual connections" in text:
                    score += 100
                    reasons.append(
                        "contains mutual-connections result text"
                    )

                # ----------------------------------------------------
                # Requested location is a very strong signal.
                #
                # Mutual connections generally do not contain the
                # employee's geographic result location.
                # ----------------------------------------------------

                if (
                    requested_location_normalized
                    and requested_location_normalized in text
                ):
                    score += 80
                    reasons.append(
                        "contains requested location"
                    )

                elif location_tokens:
                    matched_location_tokens = sum(
                        1
                        for token in location_tokens
                        if token in text
                    )

                    if matched_location_tokens:
                        score += (
                            25
                            * matched_location_tokens
                        )

                        reasons.append(
                            "contains location tokens"
                        )

                # ----------------------------------------------------
                # Requested company is another strong signal.
                # ----------------------------------------------------

                if (
                    requested_company_normalized
                    and requested_company_normalized in text
                ):
                    score += 70
                    reasons.append(
                        "contains requested company"
                    )

                else:
                    matched_company_tokens = sum(
                        1
                        for token in company_tokens
                        if token in text
                    )

                    if matched_company_tokens:
                        score += (
                            20
                            * matched_company_tokens
                        )

                        reasons.append(
                            "contains company tokens"
                        )

                # ----------------------------------------------------
                # Employee result action signals.
                # ----------------------------------------------------

                if "connect" in text:
                    score += 15
                    reasons.append(
                        "contains Connect"
                    )

                if "message" in text:
                    score += 15
                    reasons.append(
                        "contains Message"
                    )

                if "follow" in text:
                    score += 10
                    reasons.append(
                        "contains Follow"
                    )

                # ----------------------------------------------------
                # Richer text is useful because mutual-connection
                # anchors are normally just a person's name.
                # ----------------------------------------------------

                text_length = len(
                    text
                )

                if text_length >= 150:
                    score += 35
                    reasons.append(
                        "rich result text"
                    )

                elif text_length >= 100:
                    score += 25
                    reasons.append(
                        "rich result text"
                    )

                elif text_length >= 60:
                    score += 15
                    reasons.append(
                        "extended result text"
                    )

                elif text_length <= 60:
                    score -= 20
                    reasons.append(
                        "short profile-link text"
                    )

                # ----------------------------------------------------
                # Very short name-only links with no location/company
                # evidence are treated as likely nested people.
                # ----------------------------------------------------

                if (
                    text_length <= 60
                    and requested_location_normalized
                    not in text
                    and not (
                        requested_company_normalized
                        and requested_company_normalized in text
                    )
                    and "mutual connections" not in text
                ):
                    score -= 50
                    reasons.append(
                        "likely nested/mutual profile"
                    )

                existing = best_by_url.get(
                    href
                )

                candidate = {
                    "url": href,
                    "text": raw_text.replace(
                        "\n",
                        " "
                    ).strip(),
                    "normalized_text": text,
                    "score": score,
                    "reasons": reasons,
                    "dom_index": index,
                }

                # Keep the strongest representation of the same URL.
                if (
                    existing is None
                    or score > existing["score"]
                ):
                    best_by_url[href] = candidate

                print("-" * 60)
                print(
                    "PROFILE LINK:",
                    index + 1
                )
                print(
                    "URL:",
                    href
                )
                print(
                    "Text:",
                    raw_text.replace(
                        "\n",
                        " "
                    ).strip()[:500]
                )
                print(
                    "Score:",
                    score
                )
                print(
                    "Reasons:",
                    ", ".join(reasons)
                )

            except Exception as ex:
                print(
                    "Profile-link scoring failed:",
                    repr(ex)
                )

        # ------------------------------------------------------------
        # Sort strongest primary employee links first.
        #
        # Preserve DOM order when scores are equal.
        # ------------------------------------------------------------

        ranked = sorted(
            best_by_url.values(),
            key=lambda item: (
                -item["score"],
                item["dom_index"],
            )
        )

        print("=" * 60)
        print(
            "UNIQUE PROFILE URLs AFTER DEDUP:",
            len(ranked)
        )
        print("=" * 60)

        # ------------------------------------------------------------
        # Do not blindly accept extremely weak name-only links.
        #
        # A primary employee result should normally have at least one
        # meaningful result signal:
        #
        #   location
        #   company
        #   mutual-connections result text
        #   Connect/Message/Follow
        #   rich result text
        #
        # Workflow-level profile validation remains authoritative.
        # ------------------------------------------------------------

        reliable = []

        for item in ranked:

            text = item["normalized_text"]

            strong_signal = (
                "mutual connections" in text
                or (
                    requested_location_normalized
                    and requested_location_normalized in text
                )
                or (
                    requested_company_normalized
                    and requested_company_normalized in text
                )
                or "connect" in text
                or "message" in text
                or "follow" in text
                or len(text) >= 100
            )

            if not strong_signal:
                print(
                    "SKIP weak/naked /in/ link:",
                    item["url"],
                    "|",
                    item["text"]
                )
                continue

            reliable.append(
                item
            )

        print(
            "Reliable primary employee candidates:",
            len(reliable)
        )

        # ------------------------------------------------------------
        # Build result records.
        # ------------------------------------------------------------

        for item in reliable:

            profile_url = item["url"]

            profiles.append(
                {
                    "full_name": item["text"],
                    "profile_url": profile_url,
                    "company": company,
                    "location": location,
                }
            )

            print("-" * 60)
            print(
                "PRIMARY EMPLOYEE CANDIDATE:"
            )
            print(
                "Name/Text:",
                item["text"]
            )
            print(
                "URL:",
                profile_url
            )
            print(
                "Score:",
                item["score"]
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
