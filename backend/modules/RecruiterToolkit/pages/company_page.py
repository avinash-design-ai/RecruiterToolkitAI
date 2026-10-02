from pages.base_page import BasePage
from urllib.parse import urlparse, parse_qs


import re
class CompanyPage(BasePage):
    # ROOT_CAUSE_LOCATION_FILTER_V2

    def __init__(self, page):
        super().__init__(page)

    def search_company(self, company):
        '''
        Search LinkedIn for the requested company.

        Restores the previously working authenticated-feed behavior, including
        dismissal of LinkedIn dialogs that can obscure the global search control.
        If the search input is not exposed, use LinkedIn's authenticated company
        search URL instead of leaving the workflow on /feed/.

        No company/location/profile-count value is hardcoded.
        '''
        from urllib.parse import quote_plus
        import re

        requested_company = str(company or "").strip()
        if not requested_company:
            print("ERROR: Empty company name.")
            return False

        self._search_company = requested_company

        print("=" * 60)
        print("SEARCHING LINKEDIN COMPANY")
        print("=" * 60)
        print("Requested company:", requested_company)
        print("Current URL:", self.page.url)

        def is_blocked_url(url):
            value = str(url or "").lower()
            return any(
                marker in value
                for marker in (
                    "/login", "/authwall", "/checkpoint", "/uas/login",
                    "/signup", "/ssr-login", "remember-me-auto-login",
                )
            )

        def is_company_search_url(url):
            return "/search/results/companies/" in str(url or "").lower()

        def visible_company_link_count():
            try:
                return self.page.locator("a[href*='/company/']:visible").count()
            except Exception:
                return 0

        def dismiss_blocking_dialogs():
            try:
                dialogs = self.page.locator(
                    "dialog[open]:visible, [role='dialog']:visible"
                )
                dialog_count = dialogs.count()
                if not dialog_count:
                    return

                print(
                    "Open LinkedIn dialog(s) detected before company search:",
                    dialog_count,
                )

                for i in range(dialog_count):
                    try:
                        dialog_text = dialogs.nth(i).inner_text(
                            timeout=2000
                        ).strip()
                        if dialog_text:
                            print("Blocking dialog text:", dialog_text[:500])
                    except Exception:
                        pass

                try:
                    self.page.keyboard.press("Escape")
                    self.page.wait_for_timeout(750)
                except Exception:
                    pass

                dialogs = self.page.locator(
                    "dialog[open]:visible, [role='dialog']:visible"
                )
                for i in range(dialogs.count()):
                    try:
                        dialog = dialogs.nth(i)
                        close_buttons = dialog.get_by_role(
                            "button",
                            name=re.compile(
                                r"close|dismiss|not now|cancel",
                                re.IGNORECASE,
                            ),
                        )
                        if close_buttons.count():
                            close_buttons.first.click(timeout=5000)
                            self.page.wait_for_timeout(500)
                            break
                    except Exception as ex:
                        print("Dialog close-button attempt failed:", repr(ex))

                if self.page.locator(
                    "dialog[open]:visible, [role='dialog']:visible"
                ).count():
                    print("WARNING: A LinkedIn dialog is still visible before company-search click.")
                else:
                    print("LinkedIn blocking dialog dismissed before company search.")
            except Exception as ex:
                print(
                    "Dialog dismissal check failed; continuing with company search:",
                    repr(ex),
                )

        def find_search_input():
            selectors = (
                "input.search-global-typeahead__input:visible",
                "input[placeholder='Search']:visible",
                "input[placeholder*='Search' i]:visible",
                "input[placeholder*='looking' i]:visible",
                "input[aria-label*='Search' i]:visible",
                "input[type='search']:visible",
            )
            for selector in selectors:
                try:
                    locator = self.page.locator(selector)
                    if locator.count() > 0:
                        return locator.first
                except Exception:
                    continue

            try:
                locator = self.page.get_by_role(
                    "textbox",
                    name=re.compile(r"search", re.IGNORECASE),
                )
                if locator.count() > 0:
                    return locator.first
            except Exception:
                pass
            return None

        def open_direct_company_search():
            fallback_url = (
                "https://www.linkedin.com/search/results/companies/?keywords="
                + quote_plus(requested_company)
            )
            print(
                "Trying controlled same-page company-search URL fallback:",
                fallback_url,
            )

            try:
                self.page.goto(
                    fallback_url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                    referer="https://www.linkedin.com/feed/",
                )
                self.page.wait_for_timeout(3000)
            except Exception as ex:
                print("Company-search URL fallback failed:", repr(ex))
                return False

            for attempt in range(1, 21):
                try:
                    self.page.wait_for_timeout(500)
                except Exception:
                    pass

                current_url = str(self.page.url or "").strip()
                links = visible_company_link_count()
                print(
                    f"Company fallback DOM wait {attempt}/20:",
                    links,
                    "visible /company/ links |",
                    current_url,
                )

                if is_blocked_url(current_url):
                    print(
                        "ERROR: Company-search URL fallback reached a blocked page:",
                        current_url,
                    )
                    return False

                if links > 0:
                    print("Company search results successfully synchronized.")
                    return True

            print("ERROR: LinkedIn company-search results could not be synchronized.")
            print("Final company-search URL:", self.page.url)
            return False

        dismiss_blocking_dialogs()
        search_box = find_search_input()

        if search_box is None:
            print(
                "WARNING: LinkedIn global search input was not exposed on the "
                "authenticated Feed DOM."
            )
            print(
                "Using controlled company-search URL fallback instead of "
                "scanning Feed company links."
            )
            return open_direct_company_search()

        try:
            search_box.click(timeout=10000)
            search_box.fill(requested_company)
            print("Entering company into LinkedIn search:", requested_company)
            search_box.press("Enter")
            print("Company search submitted.")
        except Exception as ex:
            print("Primary company-search submission failed:", repr(ex))
            print("Trying controlled company-search URL fallback.")
            return open_direct_company_search()

        last_url = ""
        for attempt in range(1, 31):
            try:
                self.page.wait_for_timeout(500)
            except Exception:
                pass

            current_url = str(self.page.url or "").strip()
            last_url = current_url
            links = visible_company_link_count()

            if is_blocked_url(current_url):
                print(
                    "ERROR: LinkedIn redirected company search to a blocked page:",
                    current_url,
                )
                return False

            if links > 0:
                print(
                    f"Company search results detected: {links} visible company "
                    f"links on attempt {attempt}/30."
                )
                return True

            if is_company_search_url(current_url):
                print(
                    f"Company search results URL detected on attempt {attempt}/30:",
                    current_url,
                )
                try:
                    self.page.wait_for_timeout(1000)
                except Exception:
                    pass
                if visible_company_link_count() > 0:
                    print("Company links hydrated after navigation.")
                    return True

            if attempt in (8, 16, 24):
                try:
                    retry_box = find_search_input()
                    if retry_box is not None:
                        retry_box.press("Enter")
                        print(
                            f"Re-submitted company search on attempt {attempt}/30."
                        )
                except Exception as ex:
                    print(
                        f"Company search re-submit failed on attempt {attempt}/30:",
                        repr(ex),
                    )

        print("Company result DOM was not detected after normal LinkedIn search.")
        print("URL after normal search:", last_url)
        return open_direct_company_search()

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
        Open the exact company-scoped LinkedIn people-search page.

        V2 invariants:
          - currentCompany is preserved for the selected company.
          - pastCompany is NEVER allowed.
          - network is NEVER allowed.
          - no connection-degree filter is added.
          - location is handled separately by apply_location()/get_profiles().
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
            if not url:
                return True
            lower = str(url).lower()
            return any(
                part in lower
                for part in (
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

        def has_query_parameter(url, wanted_name):
            try:
                from urllib.parse import parse_qs, urlsplit
                query = parse_qs(
                    urlsplit(str(url or "")).query,
                    keep_blank_values=True,
                )
                wanted = str(wanted_name).lower()
                return any(
                    str(key).lower() == wanted
                    for key in query
                )
            except Exception:
                return False

        def sanitize_people_search_url(url):
            """
            Remove only:
              - network     = connection-degree filter
              - pastCompany = previous-company filter

            Preserve currentCompany and unrelated LinkedIn parameters.
            """
            try:
                from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

                parsed = urlsplit(str(url or ""))
                rebuilt = []

                for key, value in parse_qsl(
                    parsed.query,
                    keep_blank_values=True,
                ):
                    if str(key).lower() in {"network", "pastcompany"}:
                        continue
                    rebuilt.append((key, value))

                return urlunsplit(
                    (
                        parsed.scheme,
                        parsed.netloc,
                        parsed.path,
                        urlencode(rebuilt, doseq=True),
                        parsed.fragment,
                    )
                )
            except Exception:
                return str(url or "")

        def sanitize_and_reload(original_url, reason):
            clean_url = sanitize_people_search_url(original_url)

            if clean_url == original_url:
                return str(original_url or "").strip()

            removed = []
            if has_query_parameter(original_url, "pastCompany"):
                removed.append("pastCompany")
            if has_query_parameter(original_url, "network"):
                removed.append("network")

            print("=" * 60)
            print("LINKEDIN PEOPLE-SEARCH SCOPE SANITIZATION")
            print("=" * 60)
            print("Reason:", reason)
            print("Original URL:", original_url)
            print("Removing:", ", ".join(removed))
            print("Sanitized URL:", clean_url)

            try:
                self.page.goto(
                    clean_url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                    referer=original_url,
                )
                self.page.wait_for_timeout(2500)
            except Exception as ex:
                print("ERROR: Failed to open sanitized people-search URL:", repr(ex))
                return None

            return str(self.page.url or "").strip()

        def validate_clean_people_search(url, expected_ids):
            if is_blocked_url(url) or not is_people_url(url):
                print("ERROR: Final URL is not a valid authenticated company people search.")
                print("Final URL:", url)
                return False

            actual_ids = company_ids(url)

            if actual_ids != expected_ids:
                print("ERROR: currentCompany changed unexpectedly.")
                print("Expected:", expected_ids)
                print("Actual:", actual_ids)
                print("Final URL:", url)
                return False

            if has_query_parameter(url, "pastCompany"):
                print("ERROR: pastCompany still present after sanitization.")
                print("Final URL:", url)
                return False

            if has_query_parameter(url, "network"):
                print("ERROR: network still present after sanitization.")
                print("Final URL:", url)
                return False

            return True

        # CASE 1: company-result click already landed on people search.
        if is_people_url(current_url):
            ids = company_ids(current_url)

            print("=" * 60)
            print("COMPANY PEOPLE-SEARCH PAGE ALREADY OPEN")
            print("=" * 60)
            print("Company scope:", ids)

            if is_blocked_url(current_url):
                print("ERROR: Current people-search URL is blocked/authwall.")
                return False

            if not ids:
                print("ERROR: Current people-search page has no currentCompany.")
                return False

            clean_url = sanitize_and_reload(
                current_url,
                "company-result click",
            )
            if clean_url is None:
                return False

            current_url = clean_url

            if not validate_clean_people_search(current_url, ids):
                return False

            print("Connection-degree handling: DISABLED")
            print("Verified: network parameter ABSENT.")
            print("Verified: pastCompany parameter ABSENT.")
            print("Company scope preserved:", ids)

            self._employee_search_scope_ready = True

            print("=" * 60)
            print("COMPANY PEOPLE SEARCH READY")
            print("=" * 60)
            print("Final URL:", current_url)
            print("Company scope preserved:", ids)

            return True

        # CASE 2: still on the company page.
        if "/company/" in current_url.lower() and not is_blocked_url(current_url):
            links = self.page.locator(
                "a[href*='/search/results/people/']"
            )

            count = links.count()
            print("People-search links found:", count)

            selected = None

            # Prefer a clean current-company people-search link.
            for i in range(count):
                try:
                    link = links.nth(i)
                    href = (link.get_attribute("href") or "").strip()

                    if not href:
                        continue

                    if "/search/results/people/" not in href.lower():
                        continue

                    ids = company_ids(href)
                    if not ids:
                        continue

                    if has_query_parameter(href, "pastCompany"):
                        print("Skipping people-search link with pastCompany:", href)
                        continue

                    selected = link
                    break
                except Exception:
                    continue

            # If LinkedIn exposes only a polluted link, use it and sanitize
            # immediately after navigation rather than failing open.
            if selected is None:
                for i in range(count):
                    try:
                        link = links.nth(i)
                        href = (link.get_attribute("href") or "").strip()

                        if (
                            href
                            and "/search/results/people/" in href.lower()
                            and company_ids(href)
                        ):
                            selected = link
                            break
                    except Exception:
                        continue

            if selected is None:
                print("ERROR: No company-scoped people-search link found.")
                return False

            try:
                selected.scroll_into_view_if_needed()
                selected.click(timeout=15000)
                self.page.wait_for_timeout(5000)
            except Exception as ex:
                print("People-search link click failed:", repr(ex))
                return False

            final_url = str(self.page.url or "").strip()
            print("Final employee-search URL before sanitization:", final_url)

            if is_blocked_url(final_url) or not is_people_url(final_url):
                print(
                    "ERROR: LinkedIn did not open an authenticated "
                    "company people search."
                )
                return False

            final_ids = company_ids(final_url)
            if not final_ids:
                print("ERROR: Opened people-search page has no currentCompany.")
                return False

            clean_url = sanitize_and_reload(
                final_url,
                "company-page people-search link",
            )
            if clean_url is None:
                return False

            final_url = clean_url

            if not validate_clean_people_search(final_url, final_ids):
                return False

            print("Connection-degree handling: DISABLED")
            print("Verified: network parameter ABSENT.")
            print("Verified: pastCompany parameter ABSENT.")
            print("Company scope preserved:", final_ids)
            print("Final employee-search URL:", final_url)

            self._employee_search_scope_ready = True
            return True

        print("ERROR: Current page is not an authenticated company page")
        print("or a company-scoped LinkedIn people search.")
        print("Current URL:", current_url)
        return False

    def apply_location(self, location):
        """
        Apply the requested location to the authenticated company-scoped
        LinkedIn people-search query using geoUrn.

        This is the real location-filter stage. Candidate discovery must only
        start after this method has verified that LinkedIn accepted the geo filter.
        """
        print("=" * 60)
        print("APPLYING LINKEDIN LOCATION FILTER")
        print("=" * 60)

        requested_location = str(location or "").strip()
        current_url = str(self.page.url or "").strip()
        print("Requested location:", requested_location)
        print("Current URL before location filter:", current_url)

        if not requested_location:
            print("No location requested; location facet remains unset.")
            return True

        import json
        from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit

        def pairs(url):
            return parse_qsl(urlsplit(str(url or "")).query, keep_blank_values=True)

        def values(url):
            result = {}
            for key, value in pairs(url):
                result.setdefault(str(key), []).append(value)
            return result

        def company_ids(url):
            query = values(url)
            return query.get("currentCompany", []) or query.get("currentcompany", [])

        def normalized(value):
            value = str(value or "").replace("\xa0", " ").strip().lower()
            value = re.sub(r"[^a-z0-9]+", " ", value)
            return " ".join(value.split())

        def blocked(url):
            lower = str(url or "").lower()
            return any(
                marker in lower
                for marker in (
                    "/login", "/authwall", "/checkpoint", "/uas/login",
                    "/signup", "/ssr-login", "remember-me-auto-login",
                )
            )

        if "/search/results/people/" not in current_url.lower() or not company_ids(current_url):
            print("[LOCATION ERROR] Current page is not a company-scoped people search.")
            return False

        if blocked(current_url):
            print("[LOCATION ERROR] Current people-search page is blocked/authwalled.")
            return False

        expected_company_ids = company_ids(current_url)
        requested_normalized = normalized(requested_location)
        requested_tokens = set(requested_normalized.split())

        def extract_geo_candidates(payload):
            candidates = []

            def walk(value):
                if isinstance(value, list):
                    for item in value:
                        walk(item)
                    return
                if not isinstance(value, dict):
                    return

                display = ""
                for key in ("displayText", "displayName", "name", "label", "title", "text"):
                    item = value.get(key)
                    if isinstance(item, str) and item.strip():
                        display = item.strip()
                        break

                geo_id = ""
                for key in ("geoId", "geoID", "geoUrn", "entityUrn", "entity", "urn", "id"):
                    item = value.get(key)
                    if item is None:
                        continue
                    match = re.search(r"(?:urn:li:geo:)?([0-9]{3,})", str(item))
                    if match:
                        geo_id = match.group(1)
                        break

                if display and geo_id:
                    candidates.append((display, geo_id))

                for child in value.values():
                    walk(child)

            walk(payload)
            return candidates

        def fetch_geo(endpoint):
            try:
                response = self.page.evaluate(
                    """
                    async (url) => {
                        const response = await fetch(url, {
                            method: 'GET',
                            credentials: 'same-origin',
                            headers: { 'Accept': 'application/json, text/plain, */*' }
                        });
                        return {
                            status: response.status,
                            body: await response.text()
                        };
                    }
                    """,
                    endpoint,
                )
            except Exception as exc:
                print("GEO TYPEAHEAD REQUEST FAILED:", repr(exc))
                return None

            if not isinstance(response, dict):
                return None

            status = int(response.get("status") or 0)
            body = str(response.get("body") or "").strip()
            print("GEO TYPEAHEAD HTTP STATUS:", status)
            if status != 200 or not body:
                return None

            try:
                return json.loads(body)
            except json.JSONDecodeError:
                match = re.search(r"(\[.*\]|\{.*\})", body, re.S)
                if not match:
                    return None
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    return None

        base = (
            "https://www.linkedin.com/jobs-guest/api/typeaheadHits"
            f"?origin=jserp&typeaheadType=GEO&query={quote_plus(requested_location)}"
        )

        endpoints = [
            base,
            base + "&geoTypes=STATE",
        ]

        candidates = []
        for endpoint in endpoints:
            payload = fetch_geo(endpoint)
            if payload is None:
                continue
            candidates.extend(extract_geo_candidates(payload))

        if not candidates:
            print("[LOCATION ERROR] GEO typeahead returned no usable location candidate.")
            return False

        ranked = []
        seen = set()
        for display, geo_id in candidates:
            key = (normalized(display), str(geo_id))
            if key in seen:
                continue
            seen.add(key)

            display_norm = normalized(display)
            display_tokens = set(display_norm.split())
            score = 0
            if display_norm == requested_normalized:
                score += 1000
            if requested_normalized and display_norm.startswith(requested_normalized + " "):
                score += 900
            if requested_normalized and requested_normalized in display_norm:
                score += 800
            if requested_tokens and requested_tokens.issubset(display_tokens):
                score += 700
            ranked.append((score, display, str(geo_id)))

        ranked.sort(key=lambda item: (-item[0], item[1].lower(), item[2]))
        score, display, geo_id = ranked[0]

        if score < 700:
            print("[LOCATION ERROR] No sufficiently relevant GEO match for:", requested_location)
            print("Top candidates:", ranked[:8])
            return False

        print("Resolved LinkedIn location:", display)
        print("Resolved geo id:", geo_id)
        print("GEO match score:", score)

        parsed = urlsplit(current_url)
        rebuilt = []
        for key, value in pairs(current_url):
            if str(key).lower() in {"page", "network", "pastcompany", "geourn"}:
                continue
            rebuilt.append((key, value))
        rebuilt.append(("geoUrn", json.dumps([geo_id], separators=(",", ":"))))

        filtered_url = urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urlencode(rebuilt, doseq=True), parsed.fragment)
        )

        print("Applying filtered people-search URL:")
        print(filtered_url)

        try:
            self.page.goto(
                filtered_url,
                wait_until="domcontentloaded",
                timeout=60000,
                referer=current_url,
            )
            self.page.wait_for_timeout(3000)
        except Exception as exc:
            print("[LOCATION ERROR] Geo-filtered navigation failed:", repr(exc))
            return False

        final_url = str(self.page.url or "").strip()
        final_values = values(final_url)
        final_company_ids = company_ids(final_url)
        final_geo = final_values.get("geoUrn", []) or final_values.get("geoURN", [])
        final_network = final_values.get("network", []) or final_values.get("Network", [])
        final_past = final_values.get("pastCompany", []) or final_values.get("pastcompany", [])

        print("Final URL after location filter:", final_url)
        print("Final company scope:", final_company_ids)
        print("Final geoUrn:", final_geo)
        print("Final network:", final_network)
        print("Final pastCompany:", final_past)

        if blocked(final_url):
            print("[LOCATION ERROR] Geo-filtered navigation reached an authwall/login.")
            return False
        if "/search/results/people/" not in final_url.lower():
            print("[LOCATION ERROR] Geo-filtered navigation is not a people-search page.")
            return False
        if final_company_ids != expected_company_ids:
            print("[LOCATION ERROR] currentCompany changed during location filtering.")
            print("Expected:", expected_company_ids)
            print("Actual:", final_company_ids)
            return False
        if final_network:
            print("[LOCATION ERROR] network parameter survived location filtering.")
            return False
        if final_past:
            print("[LOCATION ERROR] pastCompany parameter survived location filtering.")
            return False
        if not final_geo:
            print("[LOCATION ERROR] geoUrn is missing from the final people-search URL.")
            return False

        self._employee_search_location = {
            "requested": requested_normalized,
            "display": display,
            "geo_id": geo_id,
        }

        print("LOCATION FILTER APPLIED TO LINKEDIN SEARCH.")
        print("Connection-degree filtering: DISABLED (network absent).")
        print("Company scope preserved:", final_company_ids)
        print("Location scope preserved by geoUrn:", final_geo)
        return True




    def open_result_profile(self, control_index):
        """Open one rendered `View LinkedIn Member` result in a temporary tab.

        This is used only when LinkedIn has rendered the employee result but
        has not exposed a normal `/in/` href in the DOM. The URL is learned
        from the actual LinkedIn click; it is never fabricated from text.
        """
        import re

        try:
            controls = self.page.locator(
                "xpath=//*[normalize-space(text())='View LinkedIn Member']"
            )
            count = controls.count()
        except Exception as exc:
            print("Profile-control lookup failed:", repr(exc))
            return None, ""

        if control_index < 0 or control_index >= count:
            print(
                "Profile-control index out of range:",
                control_index,
                "of",
                count,
            )
            return None, ""

        control = controls.nth(control_index)
        before_url = str(self.page.url or "").strip()

        try:
            clickable = control.locator(
                "xpath=ancestor-or-self::*[self::a or self::button or @role='button'][1]"
            )
            if clickable.count() > 0:
                control = clickable.first
        except Exception:
            pass

        def is_profile_url(url):
            value = str(url or "").strip().lower()
            return (
                "/in/" in value
                and "/login" not in value
                and "/authwall" not in value
                and "/checkpoint" not in value
                and "/ssr-login" not in value
            )

        def canonical(url):
            value = str(url or "").strip()
            if value.startswith("/"):
                value = "https://www.linkedin.com" + value
            value = value.split("?", 1)[0].split("#", 1)[0].rstrip("/")
            # Normalize the host so linkedin.com and www.linkedin.com are
            # treated as the same profile.
            value = re.sub(
                r"^https?://(?:www\.)?linkedin\.com",
                "https://www.linkedin.com",
                value,
                flags=re.IGNORECASE,
            )
            return value

        try:
            context = self.page.context
        except Exception as exc:
            print("Profile-control browser context unavailable:", repr(exc))
            return None, ""

        def find_new_profile_page(before_pages):
            try:
                pages = list(context.pages)
            except Exception:
                return None
            for candidate in pages:
                if candidate in before_pages:
                    continue
                try:
                    candidate_url = str(candidate.url or "").strip()
                    if is_profile_url(candidate_url):
                        return candidate
                except Exception:
                    continue
            return None

        for action_name, kwargs in (
            (
                "Ctrl-click",
                {
                    "modifiers": ["Control"],
                    "no_wait_after": True,
                    "timeout": 5000,
                },
            ),
            (
                "Middle-click",
                {
                    "button": "middle",
                    "no_wait_after": True,
                    "timeout": 5000,
                },
            ),
        ):
            try:
                before_pages = set(context.pages)
                control.click(**kwargs)

                profile_page = None
                for _ in range(15):
                    try:
                        self.page.wait_for_timeout(200)
                    except Exception:
                        pass
                    profile_page = find_new_profile_page(before_pages)
                    if profile_page is not None:
                        break

                if profile_page is None:
                    print(
                        f"{action_name}: no profile tab appeared for "
                        f"control {control_index}."
                    )
                    continue

                try:
                    profile_page.wait_for_load_state(
                        "domcontentloaded",
                        timeout=15000,
                    )
                except Exception:
                    pass

                try:
                    profile_page.wait_for_timeout(1200)
                except Exception:
                    pass

                actual_url = canonical(profile_page.url)
                print(
                    f"{action_name}: resolved profile {control_index}:",
                    actual_url,
                )
                return profile_page, actual_url

            except Exception as exc:
                print(
                    f"{action_name} failed for profile control "
                    f"{control_index}:",
                    repr(exc),
                )

        # Do NOT fabricate a URL and do NOT accept the search-result text as a
        # profile record. This is intentionally a hard candidate skip.
        print(
            "No real profile URL was obtained from rendered employee control; "
            "candidate skipped."
        )

        # In case a failed click changed the current page, restore the exact
        # employee-search URL before returning to the workflow.
        try:
            current_url = str(self.page.url or "").strip()
            if current_url != before_url and "/search/results/people/" not in current_url.lower():
                self.page.goto(
                    before_url,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                self.page.wait_for_timeout(1000)
        except Exception as exc:
            print("Search-page restore after failed profile-control click failed:", repr(exc))

        return None, ""

    def get_profiles(self, company="", location="", max_profiles=None):
        """Discover real employees from the company/location-scoped people page.

        LinkedIn may update the URL before the result-card DOM is hydrated.
        We therefore perform a small, bounded hydration pass before giving up.
        Candidate discovery is based on real /in/ links inside the main result
        area and does NOT require a 1st/2nd/3rd-degree marker.
        """
        import re

        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)
        print("Requested company:", company)
        print("Requested location:", location)

        if max_profiles is not None:
            max_profiles = int(max_profiles)
            if max_profiles < 1:
                raise ValueError("max_profiles must be a positive integer or None.")

        current_url = str(self.page.url or "").strip()
        lower_url = current_url.lower()
        if "/search/results/people/" not in lower_url or "currentcompany=" not in lower_url:
            print("ERROR: Current page is not a company-scoped LinkedIn people search.")
            print("Current URL:", current_url)
            return []

        profiles = []
        seen_urls = set()

        def limit_reached():
            return max_profiles is not None and len(profiles) >= max_profiles

        def canonical(href):
            if not href:
                return ""
            value = str(href).strip()
            if value.startswith("/"):
                value = "https://www.linkedin.com" + value
            value = value.split("?", 1)[0].split("#", 1)[0].rstrip("/")
            if "/in/" not in value.lower():
                return ""
            return re.sub(
                r"^https?://(?:www\.)?linkedin\.com",
                "https://www.linkedin.com",
                value,
                flags=re.IGNORECASE,
            )

        def visible_profile_links():
            """Choose the populated employee-result link set with the largest count."""
            selectors = (
                "main a[href*='/in/']:visible",
                "section[aria-label*='Search results'] a[href*='/in/']:visible",
                "a[href*='/in/']:visible",
            )
            best = None
            best_count = 0
            for selector in selectors:
                try:
                    locator = self.page.locator(selector)
                    count = locator.count()
                    if count > best_count:
                        best = locator
                        best_count = count
                except Exception:
                    continue
            return best

        def candidate_context(link):
            """Return bounded result-card text without walking to page-level containers."""
            best = ""
            for level in range(1, 8):
                try:
                    ancestor = link.locator("xpath=" + "/.." * level)
                    text = " ".join((ancestor.inner_text(timeout=1200) or "").split())
                    if not text:
                        continue
                    if (
                        "• 1st" in text
                        or "• 2nd" in text
                        or "• 3rd" in text
                        or str(location).lower() in text.lower()
                    ):
                        return text[:2000]
                    if 20 <= len(text) <= 1400 and not best:
                        best = text[:2000]
                except Exception:
                    continue
            return best

        def plausible_name(text):
            raw = " ".join(str(text or "").split()).strip()
            if not raw:
                return ""
            if "•" in raw:
                raw = re.sub(r"\s*•\s*(?:1st|2nd|3rd)\b.*$", "", raw, flags=re.IGNORECASE).strip()
            if "View LinkedIn Member" in raw:
                return ""
            blocked = {
                "linkedin",
                "home",
                "messaging",
                "notifications",
                "jobs",
                "search",
                "people",
                "profile",
            }
            if raw.lower() in blocked:
                return ""
            if len(raw) > 120:
                return ""
            if not re.search(r"[A-Za-z]", raw):
                return ""
            return raw

        def add_link_candidate(link):
            try:
                href = canonical(link.get_attribute("href"))
                if not href or href in seen_urls:
                    return False

                link_text = link.inner_text().strip()
                row_text = candidate_context(link)

                name = plausible_name(link_text)
                if not name:
                    for attr in ("aria-label", "title"):
                        try:
                            name = plausible_name(link.get_attribute(attr))
                        except Exception:
                            name = ""
                        if name:
                            break

                if not name:
                    return False

                context_lower = row_text.lower()
                evidence = (
                    "• 1st" in row_text
                    or "• 2nd" in row_text
                    or "• 3rd" in row_text
                    or str(location).lower() in context_lower
                    or "view profile" in context_lower
                    or "connect" in context_lower
                    or "message" in context_lower
                    or len(row_text) >= 60
                )
                if row_text and not evidence:
                    return False

                seen_urls.add(href)
                profiles.append({
                    "full_name": name,
                    "profile_url": href,
                    "control_index": None,
                    "search_result_location": location,
                    "search_result_text": row_text,
                })
                print(f"Candidate {len(profiles)}: {name} -> {href}")
                return True
            except Exception as exc:
                print("Employee-link inspection failed:", repr(exc))
                return False

        def hydrate_once(label):
            """Bounded DOM hydration for LinkedIn's lazy employee results."""
            try:
                self.page.wait_for_timeout(1200)
            except Exception:
                pass
            for delta in (1200, 1800, 2400, -2200, -1200):
                try:
                    self.page.mouse.wheel(0, delta)
                    self.page.wait_for_timeout(350)
                except Exception:
                    break
            try:
                self.page.wait_for_timeout(900)
            except Exception:
                pass

            links = visible_profile_links()
            count = 0
            try:
                count = links.count() if links is not None else 0
            except Exception:
                count = 0
            print(f"Employee DOM hydration {label}: {count} visible /in/ links")
            return links, count

        links = visible_profile_links()
        initial_count = 0
        try:
            initial_count = links.count() if links is not None else 0
        except Exception:
            initial_count = 0
        print("Visible /in/ links:", initial_count)

        if links is not None:
            for i in range(initial_count):
                if limit_reached():
                    break
                add_link_candidate(links.nth(i))

        if not profiles:
            for cycle in range(1, 4):
                links, count = hydrate_once(f"{cycle}/3")
                if links is None:
                    continue
                for i in range(count):
                    if limit_reached():
                        break
                    add_link_candidate(links.nth(i))
                if profiles or limit_reached():
                    break

        if not profiles and not limit_reached():
            try:
                print("EMPLOYEE RESULT DOM STILL EMPTY: reloading current scoped search once...")
                self.page.reload(wait_until="domcontentloaded", timeout=30000)
                try:
                    self.page.wait_for_timeout(2500)
                except Exception:
                    pass
                for cycle in range(1, 3):
                    links, count = hydrate_once(f"reload-{cycle}/2")
                    if links is None:
                        continue
                    for i in range(count):
                        if limit_reached():
                            break
                        add_link_candidate(links.nth(i))
                    if profiles or limit_reached():
                        break
            except Exception as exc:
                print("Employee result-page reload failed:", repr(exc))

        if not limit_reached() and not profiles:
            controls = None
            control_count = 0
            try:
                controls = self.page.locator(
                    "xpath=//*[normalize-space(text())='View LinkedIn Member']"
                )
                control_count = min(20, controls.count())
            except Exception:
                pass

            print("Rendered employee profile controls:", control_count)
            for index in range(control_count):
                if limit_reached():
                    break
                try:
                    if not controls.nth(index).is_visible():
                        continue
                except Exception:
                    continue
                profiles.append({
                    "full_name": "LinkedIn Member",
                    "profile_url": "",
                    "control_index": index,
                    "search_result_location": location,
                    "search_result_text": "",
                })
                print(f"Candidate {len(profiles)}: employee control #{index}")

        print("EMPLOYEE CANDIDATES DISCOVERED:", len(profiles))
        return profiles



    def next_page(self):
        """Advance using LinkedIn's rendered Next control on the same page."""
        import re
        from urllib.parse import parse_qsl, urlsplit

        current_url = str(self.page.url or "").strip()
        lower = current_url.lower()
        if "/search/results/people/" not in lower or "currentcompany=" not in lower:
            print("NEXT ABORTED: not on company-scoped people search.")
            return False

        def query_values(url, wanted):
            values = []
            for key, value in parse_qsl(urlsplit(url).query, keep_blank_values=True):
                if key.lower() == wanted.lower():
                    values.append(value)
            return values

        def page_number(url):
            values = query_values(url, "page")
            if not values:
                return 1
            try:
                return int(values[-1])
            except Exception:
                return 1

        current_page = page_number(current_url)
        target_page = current_page + 1
        expected_company = query_values(current_url, "currentCompany")
        expected_geo = query_values(current_url, "geoUrn")

        print("=" * 60)
        print("NEXT PAGE")
        print("=" * 60)
        print("Current page:", current_page)
        print("Target page:", target_page)
        print("Current URL:", current_url)

        selectors = (
            "button[aria-label='Next']",
            "button[aria-label*='Next']",
            "a[aria-label='Next']",
            "a[aria-label*='Next']",
            "button:has-text('Next')",
            "a:has-text('Next')",
        )

        next_control = None
        for selector in selectors:
            try:
                locator = self.page.locator(selector)
                count = locator.count()
            except Exception:
                continue

            for index in range(count):
                candidate = locator.nth(index)
                try:
                    if not candidate.is_visible():
                        continue
                    if str(candidate.get_attribute("disabled") or "").lower() in {"true", "disabled"}:
                        continue
                    if str(candidate.get_attribute("aria-disabled") or "").lower() == "true":
                        continue
                    next_control = candidate
                    break
                except Exception:
                    continue
            if next_control is not None:
                break

        if next_control is None:
            print("NO MORE EMPLOYEE RESULTS: rendered Next control not found.")
            return False

        try:
            next_control.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            pass

        before_hrefs = set()
        try:
            links = self.page.locator("a[href*='/in/']:visible")
            for i in range(min(30, links.count())):
                href = str(links.nth(i).get_attribute("href") or "").strip()
                if href:
                    before_hrefs.add(href)
        except Exception:
            pass

        try:
            print("Clicking rendered LinkedIn Next control...")
            next_control.click(no_wait_after=True, timeout=15000)
        except Exception as exc:
            print("NEXT CLICK FAILED:", repr(exc))
            return False

        final_url = current_url
        final_page = current_page
        changed = False

        for attempt in range(1, 16):
            try:
                self.page.wait_for_timeout(500)
            except Exception:
                pass

            try:
                final_url = str(self.page.url or "").strip()
                final_page = page_number(final_url)
            except Exception:
                continue

            if final_url != current_url or final_page >= target_page:
                changed = True
                break

            # LinkedIn can render the next result set before the URL updates.
            try:
                links = self.page.locator("a[href*='/in/']:visible")
                after_hrefs = set()
                for i in range(min(30, links.count())):
                    href = str(links.nth(i).get_attribute("href") or "").strip()
                    if href:
                        after_hrefs.add(href)
                if after_hrefs and after_hrefs != before_hrefs:
                    changed = True
                    final_url = str(self.page.url or current_url).strip()
                    final_page = page_number(final_url)
                    break
            except Exception:
                pass

        if not changed:
            print("NEXT FAILED: LinkedIn did not advance the authenticated search page.")
            print("Still on URL:", final_url)
            return False

        final_lower = final_url.lower()
        if (
            "/search/results/people/" not in final_lower
            or "currentcompany=" not in final_lower
            or "/login" in final_lower
            or "/authwall" in final_lower
            or "/ssr-login" in final_lower
        ):
            print("NEXT FAILED: LinkedIn did not return an authenticated people-search page.")
            print("Final URL:", final_url)
            return False

        final_company = query_values(final_url, "currentCompany")
        final_geo = query_values(final_url, "geoUrn")

        if expected_company and final_company != expected_company:
            print("NEXT FAILED: currentCompany changed.")
            print("Expected:", expected_company)
            print("Actual:", final_company)
            return False

        if expected_geo and final_geo != expected_geo:
            print("NEXT FAILED: geoUrn changed.")
            print("Expected:", expected_geo)
            print("Actual:", final_geo)
            return False

        # When LinkedIn updates the URL, require the expected page number.
        # If the UI advanced without adding a page parameter, keep the page
        # because the result-set change was independently observed.
        if "page=" in final_lower and final_page != target_page:
            print("NEXT FAILED: unexpected page number.")
            print("Expected:", target_page)
            print("Actual:", final_page)
            return False

        try:
            self.page.wait_for_timeout(2500)
            self.page.mouse.wheel(0, 1600)
            self.page.wait_for_timeout(700)
            self.page.mouse.wheel(0, -1000)
            self.page.wait_for_timeout(900)
        except Exception:
            pass

        print("NEXT PAGE READY:", final_url)
        return True
