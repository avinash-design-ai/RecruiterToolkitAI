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

    def get_profiles(self, company="", location="", max_candidates=100):
        """
        Discover genuine employee profile URLs from the authenticated,
        company-scoped LinkedIn people-search page.

        Important invariants:
        - connection degree is ignored;
        - discovery never invents a profile URL;
        - /in/<slug> is required (nested /in/... paths are rejected);
        - result-card / local-row boundaries are preferred over page-wide scans;
        - GitHub/headless "View LinkedIn Member" rows may be resolved by a real
          Ctrl-click/middle-click and the resulting authenticated /in URL is
          captured before the temporary tab is closed;
        - company/location are validated authoritatively by SearchWorkflowV2.
        """
        import re
        from urllib.parse import urlsplit

        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)
        print("Requested company:", company)
        print("Requested location:", location)

        try:
            candidate_limit = max(1, int(max_candidates))
        except (TypeError, ValueError):
            candidate_limit = 100
        candidate_limit = min(candidate_limit, 100)

        profiles = []
        seen_urls = set()

        def normalize_text(value):
            if not value:
                return ""
            return re.sub(
                r"\s+",
                " ",
                str(value).replace("\xa0", " ").replace("\r", " ").replace("\n", " "),
            ).strip()

        def canonical_profile_url(href):
            if not href:
                return ""
            value = str(href).strip()
            if value.startswith("/"):
                value = "https://www.linkedin.com" + value
            value = value.split("?", 1)[0].split("#", 1)[0].rstrip("/")
            try:
                parsed = urlsplit(value)
                host = (parsed.netloc or "").lower()
                path = parsed.path or ""
            except Exception:
                return ""
            if host not in {"linkedin.com", "www.linkedin.com"}:
                return ""
            if not re.fullmatch(r"/in/[^/]+", path, flags=re.IGNORECASE):
                return ""
            return "https://www.linkedin.com" + path.lower()

        def non_profile_label(value):
            text = normalize_text(value).lower()
            return any(
                phrase in text
                for phrase in (
                    "view my portfolio",
                    "view portfolio",
                    "visit my portfolio",
                    "visit portfolio",
                    "view website",
                    "visit website",
                    "personal website",
                    "see open roles",
                    "view open roles",
                    "view jobs",
                    "view services",
                    "services",
                )
            )

        requested_location = normalize_text(location).lower()
        location_tokens = [
            token for token in re.findall(r"[a-z0-9]+", requested_location)
            if len(token) >= 3
        ]

        def location_matches(text):
            value = normalize_text(text).lower()
            if not requested_location:
                return True
            if requested_location in value:
                return True
            return bool(location_tokens and all(token in value for token in location_tokens))

        def extract_primary_name(anchor_text, result_text=""):
            text = normalize_text(anchor_text) or normalize_text(result_text)
            if not text or non_profile_label(text):
                return ""
            lower = text.lower()
            if lower.startswith("linkedin member"):
                return "LinkedIn Member"
            for marker in (" connect ", " • "):
                if marker in text:
                    text = text.split(marker, 1)[0].strip()
            if "mutual connection" in text.lower():
                text = re.split(r",\s+|\s+&\s+", text, maxsplit=1)[0].strip()
            if text.lower().startswith("linkedin member"):
                return "LinkedIn Member"
            return text[:180].strip()

        def add_candidate(href, name, result_text):
            if len(profiles) >= candidate_limit:
                return False
            if non_profile_label(name):
                return False
            profile_url = canonical_profile_url(href)
            if not profile_url or profile_url in seen_urls:
                return False
            clean_name = extract_primary_name(name, result_text)
            if not clean_name:
                return False
            clean_text = normalize_text(result_text)
            profiles.append(
                {
                    "full_name": clean_name,
                    "profile_url": profile_url,
                    "company": company,
                    "location": location,
                    "search_result_text": clean_text,
                    "search_result_location": location if location_matches(clean_text) else "",
                }
            )
            seen_urls.add(profile_url)
            return True

        current_url = str(self.page.url or "").strip()
        current_lower = current_url.lower()
        if "/search/results/people/" not in current_lower or "currentcompany=" not in current_lower:
            print("ERROR: Current page is not a company-scoped LinkedIn people search.")
            print("Current URL:", current_url)
            return profiles

        print("Company-scoped employee search confirmed.")
        print("Current URL:", current_url)

        # ------------------------------------------------------------
        # Hydration: accept links, cards, or the headless text-only state.
        # ------------------------------------------------------------
        print("=" * 60)
        print("WAITING FOR EMPLOYEE RESULT DOM")
        print("=" * 60)

        def employee_render_state(page):
            visible_links = 0
            cards = 0
            text = ""
            try:
                visible_links = page.locator("a[href*='/in/']:visible").count()
            except Exception:
                pass
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
                    cards = max(cards, page.locator(selector).count())
                except Exception:
                    pass
            try:
                text = normalize_text(page.locator("body").inner_text(timeout=1500)).lower()
            except Exception:
                text = ""
            no_results = any(marker in text for marker in ("no results found", "0 results", "no people found"))
            member_controls = "view linkedin member" in text
            role_hits = sum(
                1
                for signal in (
                    "recruiter", "talent acquisition", "sales", "manager", "engineer",
                    "developer", "analyst", "consultant", "specialist", "staffing",
                )
                if signal in text
            )
            rendered_employee_text = len(text) >= 700 and (member_controls or role_hits >= 2) and not no_results
            return visible_links, cards, rendered_employee_text, text

        for attempt in range(1, 41):
            try:
                self.page.wait_for_timeout(500)
            except Exception:
                pass
            visible_links, cards, rendered_text, _ = employee_render_state(self.page)
            print(
                f"Employee DOM wait {attempt}/40:",
                visible_links,
                "visible /in/ links |",
                cards,
                "result cards |",
                rendered_text,
                "employee-result text",
            )
            if visible_links or cards or rendered_text:
                break
            if attempt in (8, 16, 24, 32):
                try:
                    self.page.mouse.wheel(0, 1200)
                except Exception:
                    pass

        # ------------------------------------------------------------
        # PASS 1: explicit LinkedIn result-card boundaries.
        # ------------------------------------------------------------
        print("=" * 60)
        print("PASS 1 - RESULT CARD EXTRACTION")
        print("=" * 60)

        card_selectors = (
            "li.reusable-search__result-container",
            "li[class*='reusable-search__result']",
            "li.entity-result",
            "div.entity-result",
            "li.search-result",
            "li[class*='search-result']",
            "ul.reusable-search__entity-result-list > li",
        )
        cards = None
        for selector in card_selectors:
            try:
                candidate = self.page.locator(selector)
                if candidate.count() > 0:
                    cards = candidate
                    print("Using result-card selector:", selector)
                    print("Result cards:", candidate.count())
                    break
            except Exception:
                continue

        if cards is not None:
            for card_index in range(cards.count()):
                if len(profiles) >= candidate_limit:
                    break
                try:
                    card = cards.nth(card_index)
                    card_text = normalize_text(card.inner_text())
                    if len(card_text) < 20:
                        continue
                    links = card.locator("a[href*='/in/']:visible")
                    link_count = links.count()
                    if not link_count:
                        continue
                    primary = None
                    for i in range(min(6, link_count)):
                        link = links.nth(i)
                        href = link.get_attribute("href") or ""
                        name_text = link.inner_text(timeout=1200).strip()
                        if canonical_profile_url(href) and not non_profile_label(name_text):
                            primary = link
                            break
                    if primary is None:
                        continue
                    href = primary.get_attribute("href") or ""
                    name = primary.inner_text(timeout=1200).strip()
                    if add_candidate(href, name, card_text):
                        print("EMPLOYEE CANDIDATE:", canonical_profile_url(href))
                        print("Primary anchor:", normalize_text(name)[:180])
                        print("Connection degree: IGNORED")
                except Exception as ex:
                    print("Result-card inspection failed:", repr(ex))

        # ------------------------------------------------------------
        # PASS 2: virtualized/local-row links.
        # ------------------------------------------------------------
        print("=" * 60)
        print("PASS 2 - LOCAL RESULT-ROW EXTRACTION")
        print("=" * 60)

        row_class_signals = (
            "reusable-search__result", "entity-result", "search-result",
            "base-search-card", "pvs-entity",
        )
        row_role_signals = (
            "recruiter", "talent acquisition", "sales", "specialist", "manager",
            "engineer", "developer", "analyst", "consultant", "director", "staffing",
            "human resources", "president", "administrator", "architect",
        )

        for scan_round in range(1, 13):
            if len(profiles) >= candidate_limit:
                break
            try:
                links = self.page.locator("a[href*='/in/']:visible")
                link_count = links.count()
            except Exception:
                link_count = 0
                links = None
            round_added = 0

            if links is not None:
                for link_index in range(link_count):
                    if len(profiles) >= candidate_limit:
                        break
                    try:
                        link = links.nth(link_index)
                        href = link.get_attribute("href") or ""
                        if not canonical_profile_url(href):
                            continue
                        anchor_text = normalize_text(link.inner_text(timeout=1000))
                        if non_profile_label(anchor_text):
                            continue

                        best = None
                        best_score = -1
                        for level in range(0, 13):
                            ancestor = link if level == 0 else link.locator("xpath=" + "/.." * level)
                            try:
                                if not ancestor.count():
                                    continue
                                text_value = normalize_text(ancestor.inner_text(timeout=1000))
                                if len(text_value) < 20 or len(text_value) > 3000:
                                    continue
                                local_links = ancestor.locator("a[href*='/in/']:visible")
                                local_count = local_links.count()
                                if not local_count or local_count > 12:
                                    continue
                                lower = text_value.lower()
                                score = 0
                                if location_matches(text_value):
                                    score += 100
                                if any(signal in lower for signal in row_role_signals):
                                    score += 35
                                try:
                                    class_text = (ancestor.get_attribute("class") or "").lower()
                                except Exception:
                                    class_text = ""
                                if any(signal in class_text for signal in row_class_signals):
                                    score += 30
                                score += max(0, 25 - level * 2)
                                score -= max(0, len(text_value) - 1400) // 100
                                if score > best_score:
                                    best_score = score
                                    best = (ancestor, text_value, local_count, level)
                            except Exception:
                                continue

                        if best is None:
                            continue
                        ancestor, result_text, local_count, level = best
                        local_links = ancestor.locator("a[href*='/in/']:visible")
                        primary = None
                        for local_index in range(min(12, local_links.count())):
                            candidate_link = local_links.nth(local_index)
                            candidate_href = candidate_link.get_attribute("href") or ""
                            candidate_name = normalize_text(candidate_link.inner_text(timeout=800))
                            if canonical_profile_url(candidate_href) and not non_profile_label(candidate_name):
                                primary = candidate_link
                                break
                        if primary is None:
                            continue
                        primary_href = primary.get_attribute("href") or ""
                        primary_name = primary.inner_text(timeout=1000).strip()
                        if add_candidate(primary_href, primary_name, result_text):
                            round_added += 1
                            print("EMPLOYEE CANDIDATE:", canonical_profile_url(primary_href))
                            print("Primary anchor:", normalize_text(primary_name)[:180])
                            print("Local ancestor level:", level)
                            print("Local /in/ link count:", local_count)
                            print("Connection degree: IGNORED")
                    except Exception as ex:
                        print("Local-row inspection failed:", repr(ex))

            print(
                f"PASS 2 scan {scan_round}/12:",
                link_count,
                "visible /in/ links,",
                round_added,
                "new employees, profiles=",
                len(profiles),
            )

            # Scroll both the page and LinkedIn's inner result containers.
            try:
                state = self.page.evaluate(
                    """() => {
                        const nodes = [document.scrollingElement, ...Array.from(document.querySelectorAll('main,section,article,ul,div'))].filter(Boolean);
                        let moved = false;
                        for (const el of nodes) {
                            try {
                                const style = getComputedStyle(el);
                                const scrollable = el.scrollHeight > el.clientHeight + 20 && ['auto','scroll','overlay'].includes(style.overflowY);
                                if (scrollable) {
                                    const maxTop = Math.max(0, el.scrollHeight - el.clientHeight);
                                    if (el.scrollTop + 8 < maxTop) {
                                        const before = el.scrollTop;
                                        el.scrollTop = Math.min(maxTop, before + 900);
                                        if (el.scrollTop > before + 2) moved = true;
                                    }
                                }
                            } catch (_) {}
                        }
                        window.scrollBy(0, 700);
                        return {moved};
                    }"""
                )
                moved = bool(state.get("moved", False))
            except Exception:
                moved = False
            if not moved and round_added == 0:
                break
            try:
                self.page.wait_for_timeout(300)
            except Exception:
                pass

        try:
            self.page.evaluate("window.scrollTo(0, 0)")
        except Exception:
            pass

        # ------------------------------------------------------------
        # PASS 3: headless "View LinkedIn Member" controls.
        # Resolve only by real local markup or a real browser-created tab.
        # ------------------------------------------------------------
        if len(profiles) < candidate_limit:
            print("=" * 60)
            print("PASS 3 - VIEW LINKEDIN MEMBER CONTROL RECOVERY")
            print("=" * 60)
            try:
                controls = self.page.locator(
                    "xpath=//*[contains(normalize-space(.), 'View LinkedIn Member') "
                    "and not(.//*[contains(normalize-space(.), 'View LinkedIn Member')])]"
                )
            except Exception:
                controls = None

            def best_control_row(control):
                best_text = ""
                best_score = -1
                for level in range(0, 10):
                    try:
                        ancestor = control if level == 0 else control.locator("xpath=" + "/.." * level)
                        if not ancestor.count():
                            continue
                        text_value = normalize_text(ancestor.inner_text(timeout=1000))
                        if len(text_value) < 20 or len(text_value) > 2400:
                            continue
                        if "view linkedin member" not in text_value.lower():
                            continue
                        score = 0
                        if location_matches(text_value):
                            score += 100
                        if any(signal in text_value.lower() for signal in row_role_signals):
                            score += 30
                        try:
                            class_text = (ancestor.get_attribute("class") or "").lower()
                        except Exception:
                            class_text = ""
                        if any(signal in class_text for signal in row_class_signals):
                            score += 25
                        score += max(0, 20 - level * 2)
                        if score > best_score:
                            best_score = score
                            best_text = text_value
                    except Exception:
                        continue
                return best_text

            def href_from_local_markup(control):
                for level in range(0, 9):
                    try:
                        ancestor = control if level == 0 else control.locator("xpath=" + "/.." * level)
                        if not ancestor.count():
                            continue
                        for selector in ("a[href*='/in/']", "[data-href*='/in/']", "[data-url*='/in/']"):
                            matches = ancestor.locator(selector)
                            for i in range(min(5, matches.count())):
                                node = matches.nth(i)
                                for attr in ("href", "data-href", "data-url"):
                                    value = (node.get_attribute(attr) or "").strip()
                                    if canonical_profile_url(value):
                                        return value
                        html = ancestor.evaluate("el => el.outerHTML")
                        match = re.search(r"https?://(?:www\.)?linkedin\.com/in/[^\"'<>/?#]+/?", html or "", re.IGNORECASE)
                        if match and canonical_profile_url(match.group(0)):
                            return match.group(0)
                    except Exception:
                        continue
                return ""

            def click_control_for_url(control, index):
                try:
                    context = self.page.context
                    before_pages = set(context.pages)
                    control.scroll_into_view_if_needed(timeout=5000)
                    for action_name, kwargs in (
                        ("Ctrl-click", {"modifiers": ["Control"], "timeout": 9000, "no_wait_after": True}),
                        ("middle-click", {"button": "middle", "timeout": 9000, "no_wait_after": True}),
                    ):
                        try:
                            with context.expect_page(timeout=9500):
                                control.click(**kwargs)
                        except Exception as ex:
                            print(f"Control {index} {action_name} failed:", repr(ex))
                            continue
                        for candidate_page in list(context.pages):
                            if candidate_page in before_pages:
                                continue
                            try:
                                candidate_page.wait_for_load_state("domcontentloaded", timeout=15000)
                            except Exception:
                                pass
                            try:
                                candidate_page.wait_for_timeout(1200)
                            except Exception:
                                pass
                            candidate_url = str(candidate_page.url or "").strip()
                            captured = canonical_profile_url(candidate_url)
                            try:
                                if not candidate_page.is_closed():
                                    candidate_page.close()
                            except Exception:
                                pass
                            if captured:
                                print(f"Control {index} opened genuine profile:", captured)
                                return captured
                    return ""
                except Exception as ex:
                    print(f"Control {index} capture failed:", repr(ex))
                    return ""

            if controls is not None:
                for index in range(min(candidate_limit - len(profiles), 40, controls.count())):
                    if len(profiles) >= candidate_limit:
                        break
                    try:
                        control = controls.nth(index)
                        if not control.is_visible():
                            continue
                        row_text = best_control_row(control)
                        if not row_text:
                            continue
                        href = href_from_local_markup(control)
                        if not href:
                            href = click_control_for_url(control, index + 1)
                        if not href:
                            print(f"Control {index + 1}: no genuine profile URL recovered")
                            continue
                        if add_candidate(href, "LinkedIn Member", row_text):
                            print("EMPLOYEE CANDIDATE (CONTROL):", canonical_profile_url(href))
                    except Exception as ex:
                        print("Control recovery inspection failed:", repr(ex))

        print("=" * 60)
        print("EMPLOYEE PROFILES EXTRACTED:", len(profiles))
        print("=" * 60)
        return profiles



    def next_page(self):
        """
        Advance to the next company-scoped LinkedIn people-search page.

        The current authenticated page is never navigated directly. A fresh tab
        is used to probe the explicit next URL first, then LinkedIn's rendered
        Next control. A candidate page is adopted only after its company scope,
        page number, and employee-result rendering are validated.

        Crucially, GitHub/headless LinkedIn can render real employee rows as
        text plus "View LinkedIn Member" controls while exposing zero /in/ links.
        That state is valid and must not be mistaken for an empty result page.
        """
        import re
        from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit

        before_page = self.page
        before_url = str(before_page.url or "").strip()
        print("=" * 60)
        print("PAGINATION")
        print("=" * 60)
        print("Current URL:", before_url)

        def blocked(url):
            value = str(url or "").lower()
            return any(
                marker in value
                for marker in (
                    "/login", "/authwall", "/checkpoint", "/uas/login",
                    "/signup", "/ssr-login", "remember-me-auto-login",
                )
            )

        def company_ids(url):
            try:
                query = parse_qs(urlsplit(url).query, keep_blank_values=True)
                return query.get("currentCompany", []) or query.get("currentcompany", [])
            except Exception:
                return []

        def page_number(url):
            try:
                raw = (parse_qs(urlsplit(url).query, keep_blank_values=True).get("page", ["1"]) or ["1"])[0]
                return max(1, int(str(raw).strip()))
            except Exception:
                return 1

        def valid_people_url(url, expected_company_ids):
            if not url or blocked(url):
                return False
            lower = str(url).lower()
            if "/search/results/people/" not in lower or "currentcompany=" not in lower:
                return False
            return company_ids(url) == expected_company_ids

        if not valid_people_url(before_url, company_ids(before_url)):
            print("NEXT ABORTED - current page is not company-scoped people search.")
            return False

        expected_company_ids = company_ids(before_url)
        current_page_number = page_number(before_url)
        target_page_number = current_page_number + 1

        parsed = urlsplit(before_url)
        pairs = []
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            if key.lower() == "page":
                continue
            pairs.append((key, value))
        pairs.append(("page", str(target_page_number)))
        direct_next_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(pairs), parsed.fragment))

        def employee_rendered(page):
            visible_links = 0
            cards = 0
            text = ""
            try:
                visible_links = page.locator("a[href*='/in/']:visible").count()
            except Exception:
                pass
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
                    cards = max(cards, page.locator(selector).count())
                except Exception:
                    pass
            try:
                text = re.sub(r"\s+", " ", page.locator("body").inner_text(timeout=1500) or "").strip().lower()
            except Exception:
                text = ""
            no_results = any(marker in text for marker in ("no results found", "0 results", "no people found"))
            ready_text = (
                "view linkedin member" in text
                or (
                    "linkedin member" in text
                    and any(signal in text for signal in ("recruiter", "talent acquisition", "manager", "engineer", "developer", "analyst", "specialist"))
                )
            )
            return (visible_links > 0 or cards > 0 or (len(text) >= 700 and ready_text)) and not no_results

        def result_signature(page):
            values = []
            try:
                links = page.locator("a[href*='/in/']:visible")
                for i in range(min(12, links.count())):
                    href = (links.nth(i).get_attribute("href") or "").strip()
                    if href:
                        values.append(href.split("?", 1)[0].split("#", 1)[0].rstrip("/").lower())
            except Exception:
                pass
            return tuple(values)

        def find_next_control(page):
            selectors = (
                "button[data-testid='pagination-controls-next-button-visible']:visible",
                "button[data-testid*='pagination-controls-next-button']:visible",
                "nav[aria-label*='Pagination' i] button:visible",
                "nav[aria-label*='Pagination' i] a:visible",
                "div.artdeco-pagination button:visible",
                "div.artdeco-pagination a:visible",
            )
            for selector in selectors:
                try:
                    controls = page.locator(selector)
                    for i in range(controls.count()):
                        control = controls.nth(i)
                        label_parts = []
                        for attr in ("aria-label", "title", "data-testid"):
                            label_parts.append((control.get_attribute(attr) or "").strip())
                        try:
                            label_parts.append(control.inner_text(timeout=800).strip())
                        except Exception:
                            pass
                        label = " ".join(x for x in label_parts if x).lower()
                        if "next" not in label:
                            continue
                        try:
                            if control.is_disabled():
                                continue
                        except Exception:
                            pass
                        if control.is_visible():
                            return control
                except Exception:
                    continue
            return None

        # 1) Explicit next URL in an isolated tab.
        navigation_page = None
        try:
            navigation_page = before_page.context.new_page()
            navigation_page.goto(direct_next_url, wait_until="domcontentloaded", timeout=60000, referer=before_url)
            navigation_page.wait_for_timeout(3500)
            candidate_url = str(navigation_page.url or "").strip()
            print("Direct next-page probe final URL:", candidate_url)
            if valid_people_url(candidate_url, expected_company_ids) and page_number(candidate_url) >= target_page_number:
                if employee_rendered(navigation_page):
                    self.page = navigation_page
                    navigation_page = None
                    try:
                        if not before_page.is_closed():
                            before_page.close()
                    except Exception:
                        pass
                    print("NEXT PAGE VALIDATED VIA ISOLATED DIRECT URL")
                    print("Final next-page URL:", candidate_url)
                    return True
            elif blocked(candidate_url):
                print("Direct next-page probe hit authentication/SSR redirect.")
        except Exception as ex:
            print("Direct next-page probe failed:", repr(ex))
        finally:
            if navigation_page is not None:
                try:
                    if not navigation_page.is_closed():
                        navigation_page.close()
                except Exception:
                    pass

        # 2) Rendered Next control in a fresh copy of the current page.
        for attempt in range(1, 3):
            navigation_page = None
            try:
                print("Isolated Next-control attempt:", f"{attempt}/2")
                navigation_page = before_page.context.new_page()
                navigation_page.goto(before_url, wait_until="domcontentloaded", timeout=60000, referer=before_url)
                navigation_page.wait_for_timeout(3500)
                if not valid_people_url(str(navigation_page.url or ""), expected_company_ids):
                    continue
                before_signature = result_signature(navigation_page)
                next_control = find_next_control(navigation_page)
                if next_control is None:
                    continue
                try:
                    next_control.scroll_into_view_if_needed()
                except Exception:
                    pass
                next_control.click(timeout=15000, no_wait_after=True)

                for validation_attempt in range(1, 61):
                    navigation_page.wait_for_timeout(300)
                    candidate_url = str(navigation_page.url or "").strip()
                    if blocked(candidate_url):
                        break
                    if not valid_people_url(candidate_url, expected_company_ids):
                        continue
                    current_no = page_number(candidate_url)
                    current_signature = result_signature(navigation_page)
                    url_changed = candidate_url.rstrip("/") != before_url.rstrip("/")
                    results_changed = bool(current_signature) and current_signature != before_signature
                    if current_no < target_page_number and not url_changed and not results_changed:
                        continue
                    if not employee_rendered(navigation_page):
                        continue
                    self.page = navigation_page
                    navigation_page = None
                    try:
                        if not before_page.is_closed():
                            before_page.close()
                    except Exception:
                        pass
                    print("NEXT PAGE VALIDATED VIA ISOLATED NEXT CONTROL")
                    print("Final next-page URL:", candidate_url)
                    return True
            except Exception as ex:
                print("Isolated Next-control attempt failed:", repr(ex))
            finally:
                if navigation_page is not None:
                    try:
                        if not navigation_page.is_closed():
                            navigation_page.close()
                    except Exception:
                        pass

        self.page = before_page
        print("NEXT FAILED - no validated next company people-search page exists from the current page.")
        print("LIVE EMPLOYEE-SEARCH PAGE PRESERVED:", self.page.url)
        return False
