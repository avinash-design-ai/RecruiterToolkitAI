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




    def get_profiles(
        self,
        company="",
        location="",
        max_profiles=None,
    ):
        """
        Extract employee candidates from the authenticated company-scoped
        LinkedIn people-search page.

        PASS 1:
            Use known LinkedIn result-card selectors.

        PASS 2:
            Inspect each visible /in/ link independently using only local
            Playwright ancestors. Never select a page-level ancestor that
            contains many employees.

        Connection degree is ignored.

        Location is authoritative at profile-validation level. The DOM
        discovery stage does not discard a candidate merely because LinkedIn's
        virtualized result markup does not expose location text.
        """

        print("=" * 60)
        print("EXTRACTING EMPLOYEE PROFILES")
        print("=" * 60)

        print("Requested company:", company)
        print("Requested location:", location)

        if max_profiles is not None:
            try:
                max_profiles = int(max_profiles)
            except (TypeError, ValueError):
                raise ValueError(
                    "max_profiles must be a positive integer or None."
                )

            if max_profiles < 1:
                raise ValueError(
                    "max_profiles must be at least 1."
                )

        print("Page candidate limit:", max_profiles)

        profiles = []
        seen_urls = set()

        def limit_reached():
            return (
                max_profiles is not None
                and len(profiles) >= max_profiles
            )

        # ============================================================
        # HELPERS
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

        def extract_primary_name(anchor_text, result_text=""):
            """
            Return the employee identity represented by the PRIMARY /in/
            anchor inside a single LinkedIn employee search-result row.

            LinkedIn sometimes renders the anchor text as the whole result
            card, including degree text or mutual-connection text. Never use
            connection-degree labels as identity data, and never treat a
            mutual-connection suffix as the employee's name.

            For anonymized rows, preserve the literal 'LinkedIn Member'
            label instead of rejecting the profile.
            """
            text = normalize_text(anchor_text)

            if not text:
                text = normalize_text(result_text)

            if not text:
                return ""

            lower = text.lower()

            if lower.startswith("linkedin member"):
                return "LinkedIn Member"

            for marker in (
                " connect ",
                " • ",
            ):
                parts = text.split(marker, 1)
                if parts[0].strip():
                    text = parts[0].strip()

            lower = text.lower()

            if "mutual connection" in lower:
                text = re.split(
                    r",\s+|\s+&\s+",
                    text,
                    maxsplit=1,
                )[0].strip()

            if text.lower().startswith("linkedin member"):
                return "LinkedIn Member"

            if len(text) > 180:
                text = text[:180].strip()

            return text

        def add_candidate(
            href,
            name,
            result_text,
            enforce_location=False
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
                if "linkedin member" in clean_text.lower():
                    clean_name = "LinkedIn Member"
                else:
                    return False

            if enforce_location and not location_matches(
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


        # ROOT_CAUSE_EXTRACTION_PAGINATION_V5: hydration gate + semantic profile-control recovery +
        # defense-in-depth result-location validation.
        # ============================================================
        # VERIFY COMPANY PEOPLE SEARCH
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
        # HYDRATION WAIT
        #
        # IMPORTANT:
        # Page 2 can temporarily have:
        #
        #   0 visible /in/ links
        #   0 recognizable result cards
        #
        # while the employee-result text is already rendered.
        #
        # next_page() already recognizes this condition. get_profiles()
        # must use the same third signal.
        # ============================================================

        print("=" * 60)
        print("WAITING FOR EMPLOYEE RESULT DOM")
        print("=" * 60)

        rendered_profile_links = 0
        rendered_result_cards = 0
        rendered_result_text = False

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

        result_words = (
            "people",
            "employees",
            "results",
            "connections",
        )

        for attempt in range(1, 41):

            try:
                self.page.wait_for_timeout(
                    500
                )
            except Exception:
                pass

            # --------------------------------------------------------
            # Visible profile links
            # --------------------------------------------------------

            try:

                rendered_profile_links = (
                    self.page
                    .locator(
                        "a[href*='/in/']"
                    )
                    .count()
                )

            except Exception:

                rendered_profile_links = 0

            # --------------------------------------------------------
            # Recognizable result cards
            # --------------------------------------------------------

            rendered_result_cards = 0

            for selector in (
                "li.reusable-search__result-container",
                "li[class*='reusable-search__result']",
                "li.entity-result",
                "div.entity-result",
                "li.search-result",
                "li[class*='search-result']",
                "ul.reusable-search__entity-result-list > li",
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

            # --------------------------------------------------------
            # Rendered employee-result text
            # --------------------------------------------------------

            rendered_result_text = False

            try:

                body_text = (
                    self.page
                    .locator("body")
                    .inner_text(
                        timeout=2000
                    )
                )

                normalized_body = re.sub(
                    r"\s+",
                    " ",
                    body_text or ""
                ).strip().lower()

                role_hits = sum(
                    1
                    for signal in role_signals
                    if signal in normalized_body
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
                f"Employee DOM wait {attempt}/40:",
                rendered_profile_links,
                "visible /in/ links |",
                rendered_result_cards,
                "result cards |",
                rendered_result_text,
                "employee-result text"
            )

            # A text-only result is NOT enough for candidate extraction.
            # LinkedIn can paint the search-result text before it hydrates the
            # profile links/row controls.  The old implementation stopped on
            # rendered_result_text alone, immediately entered PASS 1/2, saw
            # zero /in/ links, and then reported a false "no candidates" page.
            if (
                rendered_profile_links > 0
                or rendered_result_cards > 0
            ):

                print(
                    "Employee result DOM detected."
                )

                break

            if (
                rendered_result_text
                and attempt >= 20
            ):

                print(
                    "Employee result text detected, but no profile "
                    "links/cards hydrated after 20 polling attempts."
                )

                print(
                    "Continuing with semantic profile-control recovery."
                )

                break

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
        # KNOWN RESULT-CARD SELECTORS
        # ============================================================

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

                locator = self.page.locator(
                    selector
                )

                count = locator.count()

                if count > 0:

                    cards = locator

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

                    card_text = normalize_text(
                        card.inner_text()
                    )

                    if len(card_text) < 20:
                        continue

                    links = card.locator(
                        "a[href*='/in/']"
                    )

                    link_count = links.count()

                    if link_count == 0:
                        continue

                    # First /in/ link in a real result card is the
                    # employee. Mutual-connection links follow it.
                    link = links.nth(0)

                    href = (
                        link.get_attribute(
                            "href"
                        )
                        or ""
                    )

                    raw_name = (
                        link
                        .inner_text(
                            timeout=1500
                        )
                        .strip()
                    )

                    name = extract_primary_name(
                        raw_name,
                        card_text,
                    )

                    if add_candidate(
                        href,
                        name,
                        card_text,
                        enforce_location=True
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

                except Exception as ex:

                    print(
                        f"Result-card "
                        f"{card_index + 1} inspection failed:",
                        repr(ex)
                    )

        # ============================================================
        # PASS 1B
        # SEMANTIC PROFILE-CONTROL RECOVERY
        #
        # GitHub/headless LinkedIn can render the employee result text but
        # omit normal /in/ anchors from the DOM. In that mode the visible
        # row can still expose a "View LinkedIn Member" control.
        #
        # Recovery order:
        #   1. local href/data-url/HTML lookup
        #   2. Ctrl-click / middle-click the row control and capture the
        #      authenticated profile tab URL
        #
        # No profile URL is fabricated from a name or row text.
        # ============================================================

        if not limit_reached():

            print("=" * 60)
            print("PASS 1B - SEMANTIC PROFILE-CONTROL RECOVERY")
            print("=" * 60)

            # Use a leaf-oriented XPath instead of get_by_text(..., exact=True).
            # LinkedIn's headless result markup can expose the rendered phrase
            # as a descendant text node without creating an exact text locator.
            try:
                controls = self.page.locator(
                    "xpath=//*[contains(normalize-space(.), "
                    "'View LinkedIn Member') "
                    "and not(.//*[contains(normalize-space(.), "
                    "'View LinkedIn Member')])]"
                )
                control_count = min(25, controls.count())
            except Exception as ex:
                controls = None
                control_count = 0
                print(
                    "Semantic profile-control lookup failed:",
                    repr(ex),
                )

            print(
                "Semantic profile controls found:",
                control_count,
            )

            def control_result_text(node):
                """
                Pick the smallest useful local employee-result ancestor.
                The returned text is also the bounded evidence used by
                location validation.
                """
                best_text = ""
                best_score = -1

                for level in range(0, 10):
                    try:
                        ancestor = (
                            node
                            if level == 0
                            else node.locator(
                                "xpath=" + "/.." * level
                            )
                        )

                        if not ancestor.count():
                            continue

                        try:
                            text_value = normalize_text(
                                ancestor.inner_text(timeout=1000)
                            )
                        except Exception:
                            continue

                        if (
                            "view linkedin member" not in
                            text_value.lower()
                        ):
                            continue

                        if len(text_value) < 20 or len(text_value) > 2200:
                            continue

                        lower = text_value.lower()
                        score = 0

                        if location_matches(text_value):
                            score += 100

                        if "linkedin member" in lower:
                            score += 35

                        if any(
                            signal in lower
                            for signal in (
                                "recruiter",
                                "talent acquisition",
                                "manager",
                                "engineer",
                                "developer",
                                "analyst",
                                "consultant",
                                "specialist",
                                "staffing",
                                "director",
                                "architect",
                            )
                        ):
                            score += 40

                        try:
                            class_text = (
                                ancestor.get_attribute("class")
                                or ""
                            ).lower()
                        except Exception:
                            class_text = ""

                        if any(
                            signal in class_text
                            for signal in (
                                "reusable-search__result",
                                "entity-result",
                                "search-result",
                                "pvs-entity",
                            )
                        ):
                            score += 30

                        # Prefer a tighter row over a larger page/container.
                        score += max(0, 25 - level * 3)
                        score -= max(0, len(text_value) - 1200) // 100

                        if score > best_score:
                            best_score = score
                            best_text = text_value

                    except Exception:
                        continue

                return best_text

            def href_from_local_markup(node):
                # Prefer real attributes on the control or its local row.
                for level in range(0, 9):
                    try:
                        ancestor = (
                            node
                            if level == 0
                            else node.locator(
                                "xpath=" + "/.." * level
                            )
                        )

                        if not ancestor.count():
                            continue

                        for selector in (
                            "a[href*='/in/']",
                            "[href*='/in/']",
                            "[data-href*='/in/']",
                            "[data-url*='/in/']",
                            "[data-profile-url*='/in/']",
                            "[data-redirect-url*='/in/']",
                        ):
                            try:
                                matches = ancestor.locator(selector)
                                count = min(5, matches.count())
                                for idx in range(count):
                                    candidate = matches.nth(idx)

                                    for attr in (
                                        "href",
                                        "data-href",
                                        "data-url",
                                        "data-profile-url",
                                        "data-redirect-url",
                                    ):
                                        try:
                                            value = (
                                                candidate.get_attribute(attr)
                                                or ""
                                            ).strip()

                                            if "/in/" in value.lower():
                                                return value
                                        except Exception:
                                            continue
                            except Exception:
                                continue

                        for attr in (
                            "href",
                            "data-href",
                            "data-url",
                            "data-profile-url",
                            "data-redirect-url",
                        ):
                            try:
                                value = (
                                    ancestor.get_attribute(attr)
                                    or ""
                                ).strip()

                                if "/in/" in value.lower():
                                    return value
                            except Exception:
                                continue

                        # Final local markup check.
                        try:
                            html = ancestor.evaluate(
                                "el => el.outerHTML"
                            )
                            match = re.search(
                                r"(?:https?://www\.linkedin\.com)?/in/[A-Za-z0-9._%-]+",
                                str(html or ""),
                                re.IGNORECASE,
                            )

                            if match:
                                return match.group(0)
                        except Exception:
                            pass

                    except Exception:
                        continue

                return ""

            def open_control_and_capture_profile(node, control_index):
                """
                Some headless LinkedIn layouts do not expose an href at all.
                The "View LinkedIn Member" control can still open the actual
                authenticated profile in a new tab. Capture that URL and close
                only the temporary tab.
                """
                try:
                    node.scroll_into_view_if_needed(timeout=5000)
                except Exception:
                    pass

                context = None
                try:
                    context = self.page.context
                except Exception:
                    return ""

                def inspect_new_pages(before_pages):
                    try:
                        current_pages = list(context.pages)
                    except Exception:
                        return ""

                    for candidate_page in current_pages:
                        if candidate_page in before_pages:
                            continue

                        try:
                            candidate_page.wait_for_load_state(
                                "domcontentloaded",
                                timeout=15000,
                            )
                        except Exception:
                            pass

                        try:
                            candidate_page.wait_for_timeout(1500)
                        except Exception:
                            pass

                        candidate_url = str(
                            candidate_page.url or ""
                        ).strip()

                        lower = candidate_url.lower()

                        if (
                            "/in/" in lower
                            and not any(
                                marker in lower
                                for marker in (
                                    "/login",
                                    "/authwall",
                                    "/checkpoint",
                                    "/ssr-login",
                                )
                            )
                        ):
                            print(
                                f"Semantic control {control_index} opened profile:",
                                candidate_url,
                            )

                            # Close only the temporary discovery tab. The actual
                            # profile will be opened by LinkedInProfilePageV2 later.
                            try:
                                if not candidate_page.is_closed():
                                    candidate_page.close()
                            except Exception:
                                pass

                            return candidate_url

                        try:
                            if not candidate_page.is_closed():
                                candidate_page.close()
                        except Exception:
                            pass

                    return ""

                for action_name, click_kwargs in (
                    (
                        "Ctrl-click",
                        {
                            "modifiers": ["Control"],
                            "timeout": 8000,
                            "no_wait_after": True,
                        },
                    ),
                    (
                        "middle-click",
                        {
                            "button": "middle",
                            "timeout": 8000,
                            "no_wait_after": True,
                        },
                    ),
                ):
                    try:
                        before_pages = set(context.pages)

                        with context.expect_page(timeout=9000):
                            node.click(**click_kwargs)

                        captured = inspect_new_pages(before_pages)

                        if captured:
                            return captured

                    except Exception as ex:
                        print(
                            f"Semantic control {control_index} {action_name} "
                            "did not expose a profile tab:",
                            repr(ex),
                        )

                # Last resort: allow the control to navigate the SAME page,
                # but immediately restore the employee-search URL after capturing
                # a real /in/ profile URL. This avoids corrupting the search-page
                # owner if LinkedIn ignores Ctrl-click/middle-click in headless mode.
                before_search_url = str(
                    self.page.url or ""
                ).strip()

                try:
                    before_pages = set(context.pages)

                    node.click(
                        timeout=5000,
                        no_wait_after=True,
                    )
                    self.page.wait_for_timeout(1500)

                    current_url = str(
                        self.page.url or ""
                    ).strip()

                    lower_current = current_url.lower()

                    if (
                        "/in/" in lower_current
                        and not any(
                            marker in lower_current
                            for marker in (
                                "/login",
                                "/authwall",
                                "/checkpoint",
                                "/ssr-login",
                            )
                        )
                    ):
                        print(
                            f"Semantic control {control_index} navigated the "
                            "search page directly to a profile:",
                            current_url,
                        )

                        try:
                            self.page.goto(
                                before_search_url,
                                wait_until="domcontentloaded",
                                timeout=60000,
                                referer=current_url,
                            )
                            self.page.wait_for_timeout(1500)
                        except Exception as restore_ex:
                            print(
                                "Search-page restore after semantic click failed:",
                                repr(restore_ex),
                            )

                        return current_url

                    captured = inspect_new_pages(before_pages)

                    if captured:
                        return captured

                except Exception as ex:
                    print(
                        f"Semantic control {control_index} fallback click failed:",
                        repr(ex),
                    )

                return ""

            recovered = 0

            for index in range(control_count):
                if limit_reached():
                    break

                try:
                    control = controls.nth(index)

                    try:
                        if not control.is_visible():
                            continue
                    except Exception:
                        pass

                    result_text = control_result_text(control)

                    profile_href = href_from_local_markup(control)

                    if not profile_href:
                        profile_href = open_control_and_capture_profile(
                            control,
                            index + 1,
                        )

                    if not profile_href:
                        print(
                            f"Semantic control {index + 1}: "
                            "no authenticated profile URL could be recovered."
                        )
                        continue

                    primary_name = extract_primary_name(
                        "LinkedIn Member",
                        result_text,
                    )

                    if add_candidate(
                        profile_href,
                        primary_name,
                        result_text or primary_name,
                        enforce_location=True,
                    ):
                        recovered += 1

                        print("-" * 60)
                        print(
                            "EMPLOYEE CANDIDATE (SEMANTIC CONTROL):",
                            canonical_profile_url(profile_href),
                        )
                        print(
                            "Primary anchor:",
                            primary_name[:200],
                        )
                        print(
                            "Connection degree: IGNORED",
                        )

                except Exception as ex:
                    print(
                        f"Semantic profile-control {index + 1} inspection failed:",
                        repr(ex),
                    )

            print(
                "Semantic profile-control candidates recovered:",
                recovered,
            )

        # ============================================================
        # PASS 1C
        # HIDDEN HTML /in/ URL RECOVERY
        #
        # A few LinkedIn render paths keep profile URLs in the rendered HTML
        # but do not expose them as anchor locators. This pass only accepts
        # a URL when nearby HTML also contains employee-result evidence.
        # It does not generate URLs from names.
        # ============================================================

        if not limit_reached():

            print("=" * 60)
            print("PASS 1C - HIDDEN HTML PROFILE-URL RECOVERY")
            print("=" * 60)

            try:
                html = self.page.content()

                profile_matches = list(
                    re.finditer(
                        r"https?://www\.linkedin\.com/in/[A-Za-z0-9._%-]+|/in/[A-Za-z0-9._%-]+",
                        html or "",
                        re.IGNORECASE,
                    )
                )

                print(
                    "Raw /in/ URLs found in rendered HTML:",
                    len(profile_matches),
                )

                recovered_html = 0
                seen_html = set()

                for match in profile_matches:
                    if limit_reached():
                        break

                    raw_url = match.group(0)

                    profile_url = canonical_profile_url(
                        raw_url
                    )

                    if (
                        not profile_url
                        or profile_url in seen_html
                        or profile_url in seen_urls
                    ):
                        continue

                    start = max(0, match.start() - 1800)
                    end = min(
                        len(html),
                        match.end() + 1800,
                    )

                    local_html = html[start:end]

                    # Strip tags so location/result text can be validated.
                    local_text = normalize_text(
                        re.sub(
                            r"<[^>]+>",
                            " ",
                            local_html,
                        )
                    )

                    lower_local = local_text.lower()

                    if (
                        "view linkedin member" not in lower_local
                        and "linkedin member" not in lower_local
                        and not any(
                            signal in lower_local
                            for signal in (
                                "recruiter",
                                "manager",
                                "engineer",
                                "developer",
                                "analyst",
                                "consultant",
                                "specialist",
                                "staffing",
                            )
                        )
                    ):
                        continue

                    primary_name = extract_primary_name(
                        "LinkedIn Member",
                        local_text,
                    )

                    if add_candidate(
                        profile_url,
                        primary_name,
                        local_text or primary_name,
                        enforce_location=True,
                    ):
                        recovered_html += 1
                        seen_html.add(profile_url)

                        print(
                            "EMPLOYEE CANDIDATE (HIDDEN HTML):",
                            profile_url,
                        )

                print(
                    "Hidden HTML profile URLs recovered:",
                    recovered_html,
                )

            except Exception as ex:
                print(
                    "Hidden HTML profile-url recovery failed:",
                    repr(ex),
                )

        # ============================================================
        # PASS 2
        # VIRTUALIZED-DOM EMPLOYEE RESULT-ROW EXTRACTION
        #
        # The result row is the boundary. We never use a page-level /in/
        # link as an employee by itself.
        #
        # For each visible /in/ link:
        #   1. Walk local ancestors only.
        #   2. Prefer a local ancestor that looks like an employee result row.
        #   3. Treat ONLY the first /in/ link inside that row as the employee.
        #   4. Ignore later /in/ links (mutual/nested profiles).
        #   5. Ignore 1st/2nd/3rd-degree labels completely.
        # ============================================================

        print("=" * 60)
        print("PASS 2 - VIRTUALIZED-DOM EMPLOYEE RESULT-ROW EXTRACTION")
        print("=" * 60)

        if not limit_reached():

            try:
                self.page.evaluate("window.scrollTo(0, 0)")
            except Exception:
                pass

            total_rounds = 16
            empty_rounds_at_bottom = 0

            row_role_signals = (
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
                "president",
                "administrator",
                "architect",
            )

            row_class_signals = (
                "reusable-search__result",
                "entity-result",
                "search-result",
                "base-search-card",
                "pvs-entity",
            )

            for scan_round in range(1, total_rounds + 1):

                if limit_reached():
                    break

                try:
                    links = self.page.locator(
                        "a[href*='/in/']"
                    )
                    link_count = links.count()
                except Exception as ex:
                    print(
                        "Visible /in/ link lookup failed:",
                        repr(ex)
                    )
                    links = None
                    link_count = 0

                round_added = 0
                processed_rows = set()

                if links is not None and link_count > 0:

                    for link_index in range(link_count):

                        if limit_reached():
                            break

                        try:
                            link = links.nth(link_index)

                            best_container = None
                            best_text = ""
                            best_level = -1
                            best_link_count = 0
                            best_score = -1

                            for level in range(0, 10):

                                try:
                                    ancestor = link.locator(
                                        "xpath=" + "/.." * (level + 1)
                                    )

                                    if not ancestor.count():
                                        continue

                                    ancestor_text = normalize_text(
                                        ancestor.inner_text(
                                            timeout=1000
                                        )
                                    )

                                    if (
                                        len(ancestor_text) < 20
                                        or len(ancestor_text) > 2200
                                    ):
                                        continue

                                    ancestor_links = ancestor.locator(
                                        "a[href*='/in/']"
                                    )

                                    local_count = ancestor_links.count()

                                    if local_count < 1 or local_count > 5:
                                        continue

                                    try:
                                        class_text = (
                                            ancestor.get_attribute("class")
                                            or ""
                                        ).lower()
                                    except Exception:
                                        class_text = ""

                                    lower_text = ancestor_text.lower()

                                    score = 0

                                    if location_matches(
                                        ancestor_text
                                    ):
                                        score += 60

                                    if any(
                                        signal in lower_text
                                        for signal in row_role_signals
                                    ):
                                        score += 40

                                    if "linkedin member" in lower_text:
                                        score += 35

                                    if any(
                                        signal in class_text
                                        for signal in row_class_signals
                                    ):
                                        score += 30

                                    if len(ancestor_text) >= 80:
                                        score += 10

                                    score -= level

                                    # Do not promote a tiny mutual-profile
                                    # fragment to an employee result. A real
                                    # result row should expose at least one
                                    # strong signal: location, role, known
                                    # result-row class, or LinkedIn Member.
                                    if score < 25:
                                        continue

                                    if score > best_score:
                                        best_container = ancestor
                                        best_text = ancestor_text
                                        best_level = level
                                        best_link_count = local_count
                                        best_score = score

                                except Exception:
                                    continue

                            if best_container is None:
                                # LinkedIn sometimes renders a valid employee row
                                # without exposing a recognizable role/location/class
                                # signal in the ancestor text. Do not discard the
                                # candidate at discovery time; profile validation
                                # remains authoritative for company/location.
                                fallback_container = None
                                fallback_text = ""
                                fallback_level = -1
                                fallback_link_count = 0

                                for fallback_level_candidate in range(0, 7):
                                    try:
                                        fallback_ancestor = link.locator(
                                            "xpath=" + "/.." * (fallback_level_candidate + 1)
                                        )

                                        if not fallback_ancestor.count():
                                            continue

                                        fallback_ancestor_text = normalize_text(
                                            fallback_ancestor.inner_text(timeout=1000)
                                        )

                                        if (
                                            len(fallback_ancestor_text) < 10
                                            or len(fallback_ancestor_text) > 1800
                                        ):
                                            continue

                                        fallback_links = fallback_ancestor.locator(
                                            "a[href*='/in/']"
                                        )
                                        fallback_count = fallback_links.count()

                                        # A real employee row normally contains the
                                        # employee link plus zero/few related links.
                                        if fallback_count < 1 or fallback_count > 4:
                                            continue

                                        fallback_container = fallback_ancestor
                                        fallback_text = fallback_ancestor_text
                                        fallback_link_count = fallback_count
                                        break

                                    except Exception:
                                        continue

                                if fallback_container is None:
                                    continue

                                best_container = fallback_container
                                best_text = fallback_text
                                best_level = fallback_level
                                best_link_count = fallback_link_count
                                best_score = 0

                            local_links = best_container.locator(
                                "a[href*='/in/']"
                            )

                            local_count = local_links.count()

                            if local_count < 1:
                                continue

                            # The first /in/ link inside the employee result
                            # row is the employee. Later /in/ links are mutual
                            # or nested profiles and are ignored.
                            primary_link = local_links.nth(0)

                            primary_href = (
                                primary_link.get_attribute(
                                    "href"
                                )
                                or ""
                            ).strip()

                            primary_url = canonical_profile_url(
                                primary_href
                            )

                            if not primary_url:
                                continue

                            if primary_url in processed_rows:
                                continue

                            processed_rows.add(primary_url)

                            raw_primary_name = (
                                primary_link.inner_text(
                                    timeout=1500
                                ).strip()
                            )

                            primary_name = extract_primary_name(
                                raw_primary_name,
                                best_text,
                            )

                            # Do NOT reject:
                            #   - 1st/2nd/3rd-degree labels
                            #   - mutual-connection wording in the primary anchor
                            #   - LinkedIn Member
                            if not primary_name:
                                if "linkedin member" in best_text.lower():
                                    primary_name = "LinkedIn Member"
                                else:
                                    continue

                            if add_candidate(
                                primary_href,
                                primary_name,
                                best_text or primary_name,
                                enforce_location=True,
                            ):
                                round_added += 1

                                print("-" * 60)
                                print(
                                    "EMPLOYEE CANDIDATE:",
                                    primary_url,
                                )
                                print(
                                    "Primary anchor:",
                                    primary_name[:200],
                                )
                                print(
                                    "Local ancestor level:",
                                    best_level,
                                )
                                print(
                                    "Local /in/ link count:",
                                    best_link_count,
                                )
                                print(
                                    "Result group:",
                                    (best_text or primary_name)[:500],
                                )
                                print(
                                    "Connection degree: IGNORED",
                                )

                        except Exception as ex:
                            print(
                                f"PASS 2 link {link_index + 1} "
                                f"inspection failed:",
                                repr(ex),
                            )

                try:
                    scroll_state = self.page.evaluate(
                        '''() => {
                            const candidates = [
                                document.scrollingElement,
                                ...Array.from(
                                    document.querySelectorAll("main, section, article, ul, div")
                                )
                            ].filter(Boolean);

                            const seen = new Set();
                            const scrollables = [];

                            for (const el of candidates) {
                                if (seen.has(el)) continue;
                                seen.add(el);

                                try {
                                    const style = window.getComputedStyle(el);
                                    const overflowY = style.overflowY || "";
                                    const scrollable =
                                        el.scrollHeight > (el.clientHeight + 20) &&
                                        (
                                            overflowY === "auto" ||
                                            overflowY === "scroll" ||
                                            overflowY === "overlay" ||
                                            el === document.scrollingElement
                                        );

                                    if (!scrollable || el.clientHeight < 100) continue;
                                    scrollables.push(el);
                                } catch (_) {}
                            }

                            let moved = false;
                            let movableCount = 0;

                            for (const el of scrollables) {
                                try {
                                    const maxTop = Math.max(0, el.scrollHeight - el.clientHeight);
                                    if ((el.scrollTop + 8) < maxTop) {
                                        const before = el.scrollTop;
                                        el.scrollTop = Math.min(maxTop, before + 900);
                                        if (el.scrollTop > before + 2) {
                                            moved = true;
                                            movableCount += 1;
                                        }
                                    }
                                } catch (_) {}
                            }

                            window.scrollBy(0, 700);

                            return {
                                scrollableCount: scrollables.length,
                                movableCount,
                                moved
                            };
                        }'''
                    )

                    scrollable_count = int(
                        scroll_state.get("scrollableCount", 0)
                    )
                    movable_count = int(
                        scroll_state.get("movableCount", 0)
                    )
                    scrolled_inner = bool(
                        scroll_state.get("moved", False)
                    )

                    at_bottom = not scrolled_inner

                except Exception:
                    scrollable_count = 0
                    movable_count = 0
                    scrolled_inner = False
                    at_bottom = False

                print(
                    f"PASS 2 scan {scan_round}/{total_rounds}: "
                    f"{link_count} visible /in/ links, "
                    f"{round_added} new employees, "
                    f"profiles={len(profiles)}, "
                    f"at_bottom={at_bottom}"
                )

                if at_bottom:

                    if round_added == 0:
                        empty_rounds_at_bottom += 1
                    else:
                        empty_rounds_at_bottom = 0

                    if empty_rounds_at_bottom >= 2:
                        break

                # The JS block above explicitly scrolls LinkedIn's inner result
                # container(s). Keep a smaller wheel nudge as a virtualization fallback.
                try:
                    self.page.mouse.wheel(
                        0,
                        700
                    )
                except Exception:
                    pass

            try:
                self.page.evaluate(
                    "window.scrollTo(0, 0)"
                )
            except Exception:
                pass

        # ============================================================
        # FINAL RESULT
        # ============================================================

        print("=" * 60)

        if rendered_result_text and not profiles:
            print(
                "RESULT-TEXT PRESENT BUT NO EMPLOYEE CANDIDATE WAS EXTRACTED."
            )

            try:
                all_dom_links = self.page.locator(
                    "a[href*='/in/']"
                )
                dom_count = all_dom_links.count()

                print(
                    "All DOM /in/ anchors after extraction:",
                    dom_count
                )

                preview = []
                for i in range(min(dom_count, 20)):
                    try:
                        href = (
                            all_dom_links.nth(i).get_attribute("href")
                            or ""
                        )
                        if href:
                            preview.append(href)
                    except Exception:
                        continue

                print(
                    "DOM /in/ href preview:",
                    preview
                )

            except Exception as ex:
                print(
                    "DOM /in/ diagnostic failed:",
                    repr(ex)
                )

            try:
                body_preview = normalize_text(
                    self.page.locator("body").inner_text(timeout=2000)
                )

                print(
                    "Rendered employee-result text preview:",
                    body_preview[:1800]
                )

            except Exception as ex:
                print(
                    "Rendered text diagnostic failed:",
                    repr(ex)
                )

        print(
            "EMPLOYEE PROFILES EXTRACTED:",
            len(profiles)
        )

        if not profiles:
            print(
                "WARNING: No extractable profile URL survived DOM discovery. "
                "The LinkedIn page did render employee-result text, but it "
                "did not expose usable profile URLs in anchors or semantic "
                "profile controls."
            )

        print("=" * 60)

        return profiles



    def next_page(self):
        """
        Advance the authenticated company-scoped LinkedIn people search.

        Fail-safe pagination contract:
        - Preserve LinkedIn's current query parameters exactly.
        - Change ONLY the page parameter when constructing an explicit next URL.
        - Try SAME authenticated page navigation first.
        - Try a fresh tab in the SAME authenticated browser context second.
        - Use LinkedIn's own Next href/control only after direct navigation fails.
        - Validate company scope, page advancement, authentication state, and
          rendered employee-result state before accepting a transition.
        - Restore the previous authenticated search URL after a failed attempt.
        - Return False only when LinkedIn positively exposes a disabled Next control.
        - Raise on unresolved pagination failure so the workflow cannot mistake
          navigation failure for "no more employee pages".
        """
        from hashlib import sha1
        from urllib.parse import (
            parse_qs,
            parse_qsl,
            urlencode,
            urljoin,
            urlsplit,
            urlunsplit,
        )

        owner_page = self.page
        before_url = str(
            getattr(owner_page, "url", "") or ""
        ).strip()
        before_lower = before_url.lower()

        print("=" * 60)
        print("PAGINATION - FAIL-SAFE STATE MACHINE")
        print("=" * 60)
        print("Current URL:", before_url)

        def is_blocked(url):
            value = str(url or "").lower()
            return any(
                marker in value
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

        def parse_query(url):
            return parse_qs(
                urlsplit(str(url or "")).query,
                keep_blank_values=True,
            )

        def company_ids(url):
            data = parse_query(url)
            return (
                data.get("currentCompany", [])
                or data.get("currentcompany", [])
            )

        def page_number(url):
            data = parse_query(url)
            try:
                raw = (
                    data.get("page", ["1"])
                    or ["1"]
                )[0]
                return max(
                    1,
                    int(str(raw).strip()),
                )
            except Exception:
                return 1

        def is_company_people_url(url, expected_company_ids):
            value = str(url or "").lower()

            if is_blocked(value):
                return False

            if "/search/results/people/" not in value:
                return False

            actual_ids = company_ids(url)

            return bool(actual_ids) and actual_ids == expected_company_ids

        def non_page_query(url):
            return sorted(
                (
                    str(key).lower(),
                    tuple(str(item) for item in values),
                )
                for key, values in parse_query(url).items()
                if str(key).lower() not in {"page", "network", "pastcompany"}
            )

        def build_next_url(start_url):
            parsed = urlsplit(start_url)
            current_number = page_number(start_url)
            target_number = current_number + 1

            rebuilt = []
            page_written = False

            for key, value in parse_qsl(
                parsed.query,
                keep_blank_values=True,
            ):
                if str(key).lower() == "page":
                    if not page_written:
                        rebuilt.append(
                            (
                                key,
                                str(target_number),
                            )
                        )
                        page_written = True
                    continue

                if str(key).lower() in {"network", "pastcompany"}:
                    continue

                rebuilt.append(
                    (key, value)
                )

            if not page_written:
                rebuilt.append(
                    (
                        "page",
                        str(target_number),
                    )
                )

            target_url = urlunsplit(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    urlencode(
                        rebuilt,
                        doseq=True,
                    ),
                    parsed.fragment,
                )
            )

            if (
                non_page_query(target_url)
                != non_page_query(start_url)
            ):
                raise RuntimeError(
                    "Pagination safety check failed: explicit next URL "
                    "changed a query parameter other than page."
                )

            return target_url

        def result_signature(active_page):
            parts = []

            selectors = (
                "li.reusable-search__result-container",
                "li[class*='reusable-search__result']",
                "li.entity-result",
                "div.entity-result",
                "li.search-result",
                "li[class*='search-result']",
                "ul.reusable-search__entity-result-list > li",
            )

            for selector in selectors:
                try:
                    rows = active_page.locator(selector)
                    count = min(
                        10,
                        rows.count(),
                    )

                    if count:
                        for index in range(count):
                            try:
                                text_value = rows.nth(index).inner_text(
                                    timeout=1000
                                )
                            except Exception:
                                continue

                            normalized = " ".join(
                                str(text_value or "").split()
                            ).strip()

                            if normalized:
                                parts.append(
                                    normalized[:1200]
                                )

                        if parts:
                            break
                except Exception:
                    continue

            try:
                links = active_page.locator(
                    "a[href*='/in/']"
                )
                count = min(
                    20,
                    links.count(),
                )

                for index in range(count):
                    try:
                        href = (
                            links.nth(index).get_attribute(
                                "href"
                            )
                            or ""
                        ).strip()
                    except Exception:
                        continue

                    if href:
                        parts.append(
                            href.split("?", 1)[0]
                            .split("#", 1)[0]
                            .rstrip("/")
                            .lower()
                        )
            except Exception:
                pass

            if not parts:
                try:
                    body = active_page.locator(
                        "body"
                    ).inner_text(
                        timeout=1500
                    )
                    body = " ".join(
                        str(body or "").split()
                    ).strip()

                    if body:
                        parts.append(
                            body[:4000]
                        )
                except Exception:
                    pass

            payload = "\n".join(parts)

            return sha1(
                payload.encode(
                    "utf-8",
                    errors="ignore",
                )
            ).hexdigest()

        def active_page_indicator(active_page, expected_page):
            """Return True when LinkedIn itself marks the requested page active."""
            expected = str(expected_page)

            for selector in (
                "[aria-current='page']",
                "button[aria-current='page']",
                "a[aria-current='page']",
            ):
                try:
                    locator = active_page.locator(selector)
                    count = min(20, locator.count())
                    for index in range(count):
                        try:
                            text_value = " ".join(
                                str(
                                    locator.nth(index).inner_text(timeout=500)
                                    or ""
                                ).split()
                            ).strip()
                            if text_value == expected:
                                return True
                        except Exception:
                            continue
                except Exception:
                    continue

            # Fallback for LinkedIn controls that expose page state in labels.
            for selector in (
                "button:visible",
                "a:visible",
                "[role='button']:visible",
            ):
                try:
                    controls = active_page.locator(selector)
                    count = min(250, controls.count())
                    for index in range(count):
                        control = controls.nth(index)
                        parts = []
                        for attr in (
                            "aria-label",
                            "title",
                            "data-testid",
                            "data-control-name",
                        ):
                            try:
                                value = (
                                    control.get_attribute(attr)
                                    or ""
                                ).strip()
                                if value:
                                    parts.append(value)
                            except Exception:
                                pass
                        try:
                            value = (
                                control.inner_text(timeout=300)
                                or ""
                            ).strip()
                            if value:
                                parts.append(value)
                        except Exception:
                            pass

                        label = " ".join(parts).strip().lower()
                        if (
                            expected.lower() == label
                            or f"page {expected.lower()}" in label
                        ) and (
                            "current" in label
                            or "selected" in label
                            or "page" in label
                        ):
                            return True
                except Exception:
                    continue

            return False

        def result_state(active_page):
            visible_links = 0
            result_cards = 0
            result_text = False
            no_results = False

            try:
                visible_links = active_page.locator(
                    "a[href*='/in/']:visible"
                ).count()
            except Exception:
                visible_links = 0

            selectors = (
                "li.reusable-search__result-container:visible",
                "li[class*='reusable-search__result']:visible",
                "li.entity-result:visible",
                "div.entity-result:visible",
                "li.search-result:visible",
                "li[class*='search-result']:visible",
                "ul.reusable-search__entity-result-list > li:visible",
            )

            for selector in selectors:
                try:
                    result_cards = max(
                        result_cards,
                        active_page.locator(selector).count(),
                    )
                except Exception:
                    continue

            try:
                body = active_page.locator(
                    "body"
                ).inner_text(
                    timeout=2000
                )
                normalized = " ".join(
                    str(body or "").split()
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

                context_words = (
                    "people",
                    "employees",
                    "results",
                    "connections",
                )

                role_hits = sum(
                    1
                    for signal in role_signals
                    if signal in normalized
                )

                context_hits = sum(
                    1
                    for word in context_words
                    if word in normalized
                )

                result_text = (
                    len(normalized) >= 800
                    and role_hits >= 2
                    and context_hits >= 1
                )

                no_results = any(
                    marker in normalized
                    for marker in (
                        "no results",
                        "no people found",
                        "no results found",
                        "we couldn't find",
                    )
                )
            except Exception:
                pass

            return (
                visible_links,
                result_cards,
                result_text,
                no_results,
            )

        def wait_for_valid_page(
            active_page,
            expected_page,
            previous_signature,
            expected_company_ids,
        ):
            for attempt in range(1, 81):
                try:
                    active_page.wait_for_timeout(250)
                except Exception:
                    pass

                try:
                    candidate_url = str(
                        active_page.url or ""
                    ).strip()
                except Exception:
                    candidate_url = ""

                if is_blocked(candidate_url):
                    continue

                if not is_company_people_url(
                    candidate_url,
                    expected_company_ids,
                ):
                    continue

                if page_number(candidate_url) != expected_page:
                    continue

                current_signature = result_signature(
                    active_page
                )

                (
                    visible_links,
                    result_cards,
                    result_text,
                    no_results,
                ) = result_state(
                    active_page
                )

                signature_changed = (
                    bool(current_signature)
                    and current_signature != previous_signature
                )

                page_identity_confirmed = active_page_indicator(
                    active_page,
                    expected_page,
                )

                print(
                    "Active page indicator:",
                    page_identity_confirmed,
                )

                # Explicit LinkedIn no-results is an END state, not a successful page.
                if (
                    no_results
                    and visible_links == 0
                    and result_cards == 0
                    and not result_text
                ):
                    print("=" * 60)
                    print("END OF RESULTS CONFIRMED")
                    print("=" * 60)
                    print("Final URL:", candidate_url)
                    print("Page number:", page_number(candidate_url))
                    print("Result state: 0 links | 0 cards | no employee-result text")
                    return "END_OF_RESULTS"

                if (
                    (
                        signature_changed
                        or page_identity_confirmed
                    )
                    and (
                        visible_links > 0
                        or result_cards > 0
                        or result_text
                    )
                ):
                    print("=" * 60)
                    print("NEXT PAGE VALIDATED - POPULATED RESULT PAGE")
                    print("=" * 60)
                    print("Final next-page URL:", candidate_url)
                    print(
                        "Company scope preserved:",
                        company_ids(candidate_url),
                    )
                    print(
                        "Network preserved:",
                        parse_query(candidate_url).get(
                            "network",
                            [],
                        ),
                    )
                    print(
                        "Page number:",
                        page_number(candidate_url),
                    )
                    print(
                        "Result state:",
                        visible_links,
                        "visible /in/ links |",
                        result_cards,
                        "result cards |",
                        result_text,
                        "employee-result text |",
                        no_results,
                        "no-results",
                    )
                    return "VALIDATED"

            return "FAILED"

        def restore_owner_page():
            for attempt in range(1, 3):
                try:
                    print(
                        f"Restoring employee-search page {attempt}/2..."
                    )

                    owner_page.goto(
                        before_url,
                        wait_until="domcontentloaded",
                        timeout=60000,
                        referer=before_url,
                    )

                    owner_page.wait_for_timeout(2500)

                    restored_url = str(
                        owner_page.url or ""
                    ).strip()

                    if is_company_people_url(
                        restored_url,
                        original_company_ids,
                    ):
                        print(
                            "Authenticated employee-search page restored:",
                            restored_url,
                        )
                        return True
                except Exception as exc:
                    print(
                        "Restore failed:",
                        repr(exc),
                    )

            return False

        if not is_company_people_url(
            before_url,
            company_ids(before_url),
        ):
            raise RuntimeError(
                "Pagination cannot start: current page is not an "
                "authenticated company-scoped LinkedIn people search."
            )

        original_company_ids = company_ids(
            before_url
        )

        if not original_company_ids:
            raise RuntimeError(
                "Pagination cannot start: currentCompany is missing."
            )

        current_page_number = page_number(
            before_url
        )
        target_page_number = (
            current_page_number + 1
        )

        previous_signature = result_signature(
            owner_page
        )

        direct_next_url = build_next_url(
            before_url
        )

        print(
            "Current page:",
            current_page_number,
        )
        print(
            "Target page:",
            target_page_number,
        )
        print(
            "Company scope:",
            original_company_ids,
        )
        print(
            "Network:",
            parse_query(before_url).get(
                "network",
                [],
            ),
        )
        print(
            "Direct next-page URL:",
            direct_next_url,
        )

        # 1. Same authenticated page
        print("=" * 60)
        print("PAGINATION ATTEMPT: SAME AUTHENTICATED PAGE")
        print("=" * 60)

        try:
            owner_page.goto(
                direct_next_url,
                wait_until="domcontentloaded",
                timeout=60000,
                referer=before_url,
            )

            validation = wait_for_valid_page(
                owner_page,
                target_page_number,
                previous_signature,
                original_company_ids,
            )

            if validation == "VALIDATED":
                return True

            if validation == "END_OF_RESULTS":
                restore_owner_page()
                return False
        except Exception as exc:
            print(
                "Same-page pagination failed:",
                repr(exc),
            )

        restore_owner_page()

        # 2. Fresh tab, same authenticated browser context
        navigation_page = None

        print("=" * 60)
        print("PAGINATION ATTEMPT: FRESH AUTHENTICATED TAB")
        print("=" * 60)

        try:
            navigation_page = owner_page.context.new_page()

            navigation_page.goto(
                direct_next_url,
                wait_until="domcontentloaded",
                timeout=60000,
                referer=before_url,
            )

            validation = wait_for_valid_page(
                navigation_page,
                target_page_number,
                previous_signature,
                original_company_ids,
            )

            if validation == "END_OF_RESULTS":
                print("Fresh-tab pagination reached end-of-results.")
                return False

            if validation == "VALIDATED":
                old_page = owner_page
                self.page = navigation_page
                navigation_page = None

                try:
                    if (
                        old_page is not self.page
                        and not old_page.is_closed()
                    ):
                        old_page.close()
                except Exception as exc:
                    print(
                        "Previous page cleanup warning:",
                        repr(exc),
                    )

                return True

        except Exception as exc:
            print(
                "Fresh-tab pagination failed:",
                repr(exc),
            )
        finally:
            if navigation_page is not None:
                try:
                    if not navigation_page.is_closed():
                        navigation_page.close()
                except Exception:
                    pass

        restore_owner_page()

        # 3. LinkedIn's own Next href
        print("=" * 60)
        print("PAGINATION ATTEMPT: LINKEDIN NEXT HREF")
        print("=" * 60)

        next_href = ""

        for selector in (
            "a:visible",
            "button:visible",
            "[role='button']:visible",
        ):
            try:
                controls = owner_page.locator(
                    selector
                )
                count = min(
                    250,
                    controls.count(),
                )

                for index in range(count):
                    control = controls.nth(
                        index
                    )

                    try:
                        if not control.is_visible():
                            continue
                    except Exception:
                        continue

                    parts = []

                    for attr in (
                        "aria-label",
                        "title",
                        "data-testid",
                        "data-control-name",
                    ):
                        try:
                            value = (
                                control.get_attribute(
                                    attr
                                )
                                or ""
                            ).strip()
                            if value:
                                parts.append(value)
                        except Exception:
                            pass

                    try:
                        text_value = (
                            control.inner_text(
                                timeout=500
                            )
                            or ""
                        ).strip()

                        if text_value:
                            parts.append(
                                text_value
                            )
                    except Exception:
                        pass

                    label = " ".join(parts).lower()

                    if (
                        "next" not in label
                        or "previous" in label
                    ):
                        continue

                    disabled = False

                    try:
                        disabled = (
                            (
                                control.get_attribute(
                                    "aria-disabled"
                                )
                                or ""
                            ).lower()
                            == "true"
                        )
                    except Exception:
                        pass

                    try:
                        disabled = (
                            disabled
                            or bool(control.is_disabled())
                        )
                    except Exception:
                        pass

                    if disabled:
                        continue

                    try:
                        next_href = (
                            control.get_attribute(
                                "href"
                            )
                            or ""
                        ).strip()
                    except Exception:
                        next_href = ""

                    if next_href:
                        print(
                            "LinkedIn Next href found:",
                            next_href,
                        )
                        break

                if next_href:
                    break
            except Exception:
                continue

        if next_href:
            resolved_next_href = urljoin(
                before_url,
                next_href,
            )

            href_page = page_number(
                resolved_next_href
            )

            if (
                is_company_people_url(
                    resolved_next_href,
                    original_company_ids,
                )
                and href_page > current_page_number
            ):
                try:
                    owner_page.goto(
                        resolved_next_href,
                        wait_until="domcontentloaded",
                        timeout=60000,
                        referer=before_url,
                    )

                    validation = wait_for_valid_page(
                        owner_page,
                        href_page,
                        previous_signature,
                        original_company_ids,
                    )

                    if validation == "VALIDATED":
                        return True

                    if validation == "END_OF_RESULTS":
                        restore_owner_page()
                        return False
                except Exception as exc:
                    print(
                        "LinkedIn Next href navigation failed:",
                        repr(exc),
                    )

                restore_owner_page()

        # 4. Live Next control
        print("=" * 60)
        print("PAGINATION ATTEMPT: LIVE NEXT CONTROL")
        print("=" * 60)

        candidates = []

        for selector in (
            "a:visible",
            "button:visible",
            "[role='button']:visible",
        ):
            try:
                controls = owner_page.locator(
                    selector
                )
                count = min(
                    250,
                    controls.count(),
                )

                for index in range(count):
                    control = controls.nth(index)

                    try:
                        if not control.is_visible():
                            continue
                    except Exception:
                        continue

                    parts = []

                    for attr in (
                        "aria-label",
                        "title",
                        "data-testid",
                        "data-control-name",
                    ):
                        try:
                            value = (
                                control.get_attribute(
                                    attr
                                )
                                or ""
                            ).strip()
                            if value:
                                parts.append(value)
                        except Exception:
                            pass

                    try:
                        text_value = (
                            control.inner_text(
                                timeout=500
                            )
                            or ""
                        ).strip()

                        if text_value:
                            parts.append(
                                text_value
                            )
                    except Exception:
                        pass

                    label = " ".join(
                        parts
                    ).lower()

                    if (
                        "next" not in label
                        or "previous" in label
                    ):
                        continue

                    disabled = False

                    try:
                        disabled = (
                            (
                                control.get_attribute(
                                    "aria-disabled"
                                )
                                or ""
                            ).lower()
                            == "true"
                        )
                    except Exception:
                        pass

                    try:
                        disabled = (
                            disabled
                            or bool(control.is_disabled())
                        )
                    except Exception:
                        pass

                    candidates.append(
                        (
                            control,
                            disabled,
                            label,
                        )
                    )
            except Exception:
                continue

        enabled = [
            item
            for item in candidates
            if not item[1]
        ]

        if not enabled:
            if candidates:
                print(
                    "LinkedIn exposes a disabled Next control."
                )
                print(
                    "Pagination end-of-results positively confirmed."
                )
                return False

            print(
                "No usable Next control found; this is NOT treated "
                "as end-of-results."
            )
        else:
            next_control = enabled[0][0]

            try:
                next_control.scroll_into_view_if_needed()
            except Exception:
                pass

            try:
                next_control.click(
                    timeout=15000,
                    no_wait_after=True,
                )

                validation = wait_for_valid_page(
                    owner_page,
                    target_page_number,
                    previous_signature,
                    original_company_ids,
                )

                if validation == "VALIDATED":
                    return True

                if validation == "END_OF_RESULTS":
                    restore_owner_page()
                    return False
            except Exception as exc:
                print(
                    "Live Next click failed:",
                    repr(exc),
                )

            restore_owner_page()

        # Match the working desktop behavior: an unresolved Next navigation
        # is a stop condition, not a fatal workflow exception. This prevents
        # GitHub Actions from turning a LinkedIn pagination/UI variation into
        # a failed run after valid profiles have already been collected.
        print(
            "WARNING: LinkedIn pagination could not advance from page "
            f"{current_page_number} to page {target_page_number}. "
            "Treating this as the end of the usable result set."
        )
        return False
