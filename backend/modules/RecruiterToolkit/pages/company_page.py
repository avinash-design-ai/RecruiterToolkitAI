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

        # PATCH: Dismiss LinkedIn blocking dialogs before global company search
        # LinkedIn can leave a modal/dialog over the authenticated Feed page.
        # Playwright finds the search input but its click is intercepted by the
        # dialog, causing a 30-second Locator.click timeout.
        try:
            dialogs = self.page.locator(
                "dialog[open]:visible, [role='dialog']:visible"
            )

            dialog_count = dialogs.count()

            if dialog_count:
                print(
                    "Open LinkedIn dialog(s) detected before company search:",
                    dialog_count,
                )

                for i in range(dialog_count):
                    try:
                        dialog = dialogs.nth(i)

                        try:
                            dialog_text = (
                                dialog.inner_text(timeout=2000)
                                .strip()
                            )
                        except Exception:
                            dialog_text = ""

                        if dialog_text:
                            print(
                                "Blocking dialog text:",
                                dialog_text[:500],
                            )
                    except Exception:
                        pass

                # First use LinkedIn's normal modal-dismiss behavior.
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(750)

                # Some dialogs do not close on Escape. Try an explicit
                # Close/Dismiss button inside the remaining dialog only.
                dialogs = self.page.locator(
                    "dialog[open]:visible, [role='dialog']:visible"
                )

                remaining = dialogs.count()

                if remaining:
                    for i in range(remaining):
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
                            print(
                                "Dialog close-button attempt failed:",
                                repr(ex),
                            )

                dialogs = self.page.locator(
                    "dialog[open]:visible, [role='dialog']:visible"
                )

                if dialogs.count():
                    print(
                        "WARNING: A LinkedIn dialog is still visible before "
                        "company-search click; allowing the normal Playwright "
                        "click to surface a precise failure if it remains blocking."
                    )
                else:
                    print(
                        "LinkedIn blocking dialog dismissed before company search."
                    )

        except Exception as ex:
            # Do not fail the workflow merely because dialog inspection itself
            # is unavailable. Continue with the existing search behavior.
            print(
                "Dialog dismissal check failed; continuing with company search:",
                repr(ex),
            )

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
        """
        Open the authenticated company-scoped LinkedIn people search and
        broaden the connection-degree filter through LinkedIn's UI.

        IMPORTANT:
        - Do NOT rewrite network=F to F/S/O with page.goto().
        - LinkedIn can redirect that synthetic URL to /uas/login even when
          the current browser session is authenticated.
        - The UI filter change is performed inside the already-authenticated
          people-search page, so LinkedIn owns the resulting navigation.
        """

        print("=" * 60)
        print("OPENING COMPANY EMPLOYEES / PEOPLE SEARCH")
        print("=" * 60)

        # True only after the authenticated employee-search page has been
        # broadened to 1st + 2nd + 3rd+ (or was already unrestricted).
        self._employee_search_scope_ready = False

        current_url = str(self.page.url or "").strip()
        print("Current URL:")
        print(current_url)

        def is_people_url(url):
            if not url:
                return False
            lower = url.lower()
            return (
                "/search/results/people/" in lower
                and "currentcompany=" in lower
            )

        def is_blocked_url(url):
            if not url:
                return True
            lower = url.lower()
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
                from urllib.parse import urlsplit, parse_qs
                query = parse_qs(urlsplit(url).query, keep_blank_values=True)
                return query.get("currentCompany", []) or query.get("currentcompany", [])
            except Exception:
                return []

        def label_for(locator):
            parts = []
            for attr in ("aria-label", "title"):
                try:
                    value = locator.get_attribute(attr) or ""
                    if value:
                        parts.append(value)
                except Exception:
                    pass
            try:
                value = locator.inner_text(timeout=1000).strip()
                if value:
                    parts.append(value)
            except Exception:
                pass
            return " ".join(parts).strip()

        def click_filter_trigger():
            # Do NOT search arbitrary page elements for "connections".
            # LinkedIn result cards can contain phrases such as
            # "4 other mutual connections", which caused the previous
            # implementation to open the wrong UI.
            #
            # The employee search flow now uses All Filters explicitly,
            # so this helper is retained only as a safe no-op fallback.
            print("Direct Connections chip selection disabled; using All Filters.")
            return False


        def click_all_filters_trigger():
            for selector in (
                "button:visible",
                "[role='button']:visible",
                "a:visible",
            ):
                try:
                    loc = self.page.locator(selector)
                    for i in range(loc.count()):
                        item = loc.nth(i)
                        if not item.is_visible():
                            continue
                        label = label_for(item).strip().lower()
                        if label == "all filters" or "all filters" in label:
                            item.scroll_into_view_if_needed()
                            item.click(timeout=10000)
                            self.page.wait_for_timeout(1000)
                            print("All filters opened.")
                            return True
                except Exception:
                    continue
            return False

        def normalized_label(value):
            return re.sub(
                r"\s+",
                " ",
                str(value or "").replace("\\xa0", " ")
            ).strip().lower()


        def filter_dialog():
            # Prefer the visible All Filters modal/dialog. This prevents
            # employee result cards behind the modal from being considered.
            selectors = (
                "[role='dialog']:visible",
                ".artdeco-modal:visible",
            )

            for selector in selectors:
                try:
                    loc = self.page.locator(selector)
                    for i in range(min(loc.count(), 20)):
                        item = loc.nth(i)
                        if not item.is_visible():
                            continue
                        txt = normalized_label(label_for(item))
                        if "connections" in txt or "all filters" in txt:
                            return item
                except Exception:
                    continue

            return None


        def open_connections_section():
            dialog = filter_dialog()

            if dialog is None:
                print("ERROR: All Filters dialog not found.")
                return False

            # If degree options are already visible, no section click is needed.
            for label in ("1st", "2nd", "3rd+"):
                try:
                    if dialog.get_by_text(label, exact=True).count() > 0:
                        return True
                except Exception:
                    pass

            # Open the exact Connections section inside the dialog.
            candidates = (
                dialog.get_by_text("Connections", exact=True),
                dialog.locator("button:visible"),
                dialog.locator("[role='button']:visible"),
                dialog.locator("label:visible"),
                dialog.locator("li:visible"),
            )

            for loc in candidates:
                try:
                    for i in range(min(loc.count(), 200)):
                        item = loc.nth(i)
                        if not item.is_visible():
                            continue

                        label = normalized_label(label_for(item))

                        if label == "connections":
                            item.scroll_into_view_if_needed()
                            item.click(timeout=10000)
                            self.page.wait_for_timeout(700)
                            print("Connections section opened inside All Filters.")
                            return True
                except Exception:
                    continue

            # Some LinkedIn versions render the section as a text heading
            # whose parent is the clickable control.
            try:
                heading = dialog.get_by_text("Connections", exact=True).first
                if heading.count() > 0 and heading.is_visible():
                    heading.scroll_into_view_if_needed()
                    heading.click(timeout=10000)
                    self.page.wait_for_timeout(700)
                    print("Connections section opened inside All Filters.")
                    return True
            except Exception:
                pass

            print("ERROR: Connections section not found inside All Filters.")
            return False


        def find_degree_option(patterns):
            # Search ONLY inside the All Filters dialog after the Connections
            # section is open. Exact text matching prevents result names such
            # as "Esther Golda Karunakaran · 1st" from being selected.
            dialog = filter_dialog()

            if dialog is None:
                print("ERROR: Cannot locate All Filters dialog for degree selection.")
                return None

            wanted = {
                normalized_label(pattern)
                for pattern in patterns
                if pattern
            }

            selectors = (
                "label:visible",
                "[role='checkbox']:visible",
                "[role='option']:visible",
                "button:visible",
                "li:visible",
                "div:visible",
                "span:visible",
            )

            for selector in selectors:
                try:
                    loc = dialog.locator(selector)
                    for i in range(min(loc.count(), 1000)):
                        item = loc.nth(i)
                        try:
                            if not item.is_visible():
                                continue

                            label = normalized_label(label_for(item))

                            if label not in wanted:
                                continue

                            if len(label) > 30:
                                continue

                            return item
                        except Exception:
                            continue
                except Exception:
                    continue

            return None


        def degree_is_selected(item):

            try:

                for attr in (
                    "aria-checked",
                    "aria-selected",
                ):

                    value = (
                        item.get_attribute(attr)
                        or ""
                    ).strip().lower()

                    if value == "true":
                        return True


                try:

                    checkbox = (
                        item
                        .locator(
                            "input[type='checkbox']"
                        )
                        .first
                    )

                    if (
                        checkbox.count() > 0
                        and checkbox.is_checked()
                    ):
                        return True

                except Exception:
                    pass


                try:

                    cls = (
                        item.get_attribute("class")
                        or ""
                    ).lower()

                    if any(
                        token in cls
                        for token in (
                            "selected",
                            "checked",
                            "active",
                        )
                    ):
                        return True

                except Exception:
                    pass

            except Exception:
                pass

            return False


        def ensure_degree(
            label_patterns,
            wanted_words
        ):
            # Find ONLY the actual connection-degree option.

            item = find_degree_option(
                label_patterns
            )

            if item is None:

                print(
                    "ERROR: Connection-degree option "
                    "not found:",
                    label_patterns
                )

                return False


            try:

                label = (
                    label_for(item)
                    .strip()
                )


                if degree_is_selected(item):

                    print(
                        "Degree already selected:",
                        label
                    )

                    return True


                item.scroll_into_view_if_needed()

                item.click(
                    timeout=10000
                )

                self.page.wait_for_timeout(
                    500
                )


                # LinkedIn may replace the DOM node after
                # clicking, so locate it again.

                refreshed = find_degree_option(
                    label_patterns
                )


                if (
                    refreshed is not None
                    and degree_is_selected(
                        refreshed
                    )
                ):

                    print(
                        "Degree selected:",
                        label
                    )

                    return True


                # Some LinkedIn controls do not expose
                # selected state through ARIA.
                # The exact option was found and clicked,
                # so accept the click.

                print(
                    "Degree option clicked:",
                    label
                )

                return True


            except Exception as ex:

                print(
                    "Degree option click failed:",
                    label_patterns,
                    repr(ex)
                )

                return False


        def click_show_results():
            for selector in (
                "button:visible",
                "[role='button']:visible",
                "a:visible",
            ):
                try:
                    loc = self.page.locator(selector)
                    for i in range(loc.count()):
                        item = loc.nth(i)
                        if not item.is_visible():
                            continue
                        label = label_for(item).strip().lower()
                        if label == "show results" or label.endswith("show results"):
                            item.scroll_into_view_if_needed()
                            item.click(timeout=15000)
                            self.page.wait_for_timeout(5000)
                            print("Show results clicked.")
                            return True
                except Exception:
                    continue
            return False

        # ================================================================
        # CASE 1: company click already landed on people search
        # ================================================================
        if is_people_url(current_url):
            ids = company_ids(current_url)
            print("=" * 60)
            print("COMPANY PEOPLE-SEARCH PAGE ALREADY OPEN")
            print("=" * 60)
            print("Company scope:", ids)

            if not ids:
                print("ERROR: Current people-search page has no currentCompany.")
                return False

            # If LinkedIn already exposes a non-F network in the URL, keep it.
            try:
                from urllib.parse import urlsplit, parse_qs
                q = parse_qs(urlsplit(current_url).query, keep_blank_values=True)
                network = q.get("network", []) or q.get("Network", [])
                network_text = " ".join(network).lower()
            except Exception:
                network_text = ""

            if network_text and ("s" in network_text or "o" in network_text):
                print("Connection-degree filter: already broad enough")
                print("Company scope preserved:", ids)
                self._employee_search_scope_ready = True
                return True

            print("Connection-degree filter currently restricted.")
            print("Broadening through LinkedIn UI: 1st + 2nd + 3rd+.")

            # IMPORTANT:
            # Do not click the visible "Connections" chip on the results page.
            # LinkedIn can expose unrelated text such as "4 other mutual
            # connections", which is not the connection-degree filter.
            #
            # Use the authoritative All Filters UI and scope degree selection
            # to that dialog.
            print("Opening All Filters for connection-degree selection.")
            opened = click_all_filters_trigger()

            if not opened:
                print("ERROR: Could not open All Filters.")
                return False

            if not open_connections_section():
                print("ERROR: Could not open Connections section in All Filters.")
                return False

            # Keep 1st selected and add 2nd + 3rd+. This produces the
            # equivalent of an unrestricted network while preserving the
            # authenticated LinkedIn UI state.
            ok_1 = ensure_degree(("1st",), ("1st",))
            ok_2 = ensure_degree(("2nd",), ("2nd",))
            ok_3 = ensure_degree(("3rd+", "3rd +", "3rd"), ("3rd",))

            print("Connection option results (exact filter options):", ok_1, ok_2, ok_3)

            if not (ok_1 and ok_2 and ok_3):
                print("ERROR: Could not select all three connection degrees.")
                return False

            if not click_show_results():
                print("ERROR: Show results button not found after degree selection.")
                return False

            final_url = str(self.page.url or "").strip()
            print("Final employee-search URL:", final_url)

            if is_blocked_url(final_url) or not is_people_url(final_url):
                print("ERROR: LinkedIn UI filter navigation left the authenticated people search.")
                return False

            final_ids = company_ids(final_url)
            if final_ids != ids:
                print("ERROR: currentCompany changed during UI filter update.")
                print("Expected:", ids)
                print("Actual:", final_ids)
                return False

            # Do not accept a silently retained F-only search.
            try:
                from urllib.parse import urlsplit, parse_qs
                q = parse_qs(urlsplit(final_url).query, keep_blank_values=True)
                network = q.get("network", []) or q.get("Network", [])
                network_text = " ".join(network).lower()
            except Exception:
                network_text = ""

            body_text = ""
            try:
                body_text = (self.page.locator("body").inner_text(timeout=3000) or "").lower()
            except Exception:
                pass

            broad_network = (
                '"s"' in network_text
                or '"o"' in network_text
                or ("2nd" in body_text and ("3rd" in body_text or "3rd+" in body_text))
            )

            if not broad_network:
                print("ERROR: UI filter did not broaden the connection scope; refusing to continue with F-only results.")
                return False

            print("=" * 60)
            print("COMPANY PEOPLE SEARCH READY")
            print("=" * 60)
            print("Final URL:", final_url)
            print("Connection-degree filter: UI ALL (1st + 2nd + 3rd+)")
            print("Company scope preserved:", final_ids)
            self._employee_search_scope_ready = True
            return True

        # ================================================================
        # CASE 2: still on company page; use LinkedIn's own people link
        # ================================================================
        links = self.page.locator("a[href*='/search/results/people/']")
        count = links.count()
        print("People-search links found:", count)

        selected = None
        selected_href = ""
        selected_company_ids = company_ids(current_url)

        for i in range(count):
            try:
                link = links.nth(i)
                href = (link.get_attribute("href") or "").strip()
                if not href or "/search/results/people/" not in href.lower():
                    continue
                ids = company_ids(href)
                if not ids:
                    continue
                if selected_company_ids and ids != selected_company_ids:
                    continue
                selected = link
                selected_href = href
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
        print("Final employee-search URL:", final_url)

        if is_blocked_url(final_url) or not is_people_url(final_url):
            print("ERROR: LinkedIn did not open an authenticated company people search.")
            return False

        final_ids = company_ids(final_url)
        if selected_company_ids and final_ids != selected_company_ids:
            print("ERROR: currentCompany changed after opening employee search.")
            return False

        # Apply the same UI broadening logic now that the authenticated
        # company people-search page is open.
        return self.open_employees_page()

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

        profiles = []
        seen_urls = set()

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

            if (
                rendered_profile_links > 0
                or rendered_result_cards > 0
                or rendered_result_text
            ):

                print(
                    "Employee result DOM/text detected."
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

        if len(profiles) < 5:

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

                if len(profiles) >= 5:
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

                        if len(profiles) >= 5:
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
                                continue

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
                                enforce_location=False,
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

        print("=" * 60)

        return profiles

        # FINAL RESULT
        # ============================================================

        print("=" * 60)

        print(
            "EMPLOYEE PROFILES EXTRACTED:",
            len(profiles)
        )

        print("=" * 60)

        return profiles


    def next_page(self):
        """
        Move to the next company-scoped LinkedIn people-search page.

        Primary strategy:
        1. Build the next page URL from the current unfiltered company search.
        2. Open that exact URL in a fresh authenticated tab using the current
           search URL as Referer.
        3. Validate company scope, absence of network, expected page number,
           and rendered employee-result content.
        4. Only after the new page is validated do we replace self.page and
           close the previous employee-search tab.

        Fallback:
        Use LinkedIn's visible Next control only when direct URL navigation
        is not accepted.
        """
        try:
            from urllib.parse import (
                urlsplit,
                parse_qs,
                parse_qsl,
                urlencode,
                urlunsplit,
            )

            before_page = self.page
            before_url = str(before_page.url or "").strip()
            before_lower = before_url.lower()

            print("=" * 60)
            print("PAGINATION")
            print("=" * 60)
            print("Current URL:", before_url)

            if (
                "/search/results/people/" not in before_lower
                or "currentcompany=" not in before_lower
            ):
                print(
                    "NEXT ABORTED - current page is not company-scoped people search."
                )
                return False

            before_query = parse_qs(
                urlsplit(before_url).query,
                keep_blank_values=True,
            )

            company_ids = (
                before_query.get("currentCompany", [])
                or before_query.get("currentcompany", [])
            )

            expected_network = (
                before_query.get("network", [])
                or before_query.get("Network", [])
            )

            if not company_ids:
                print("NEXT ABORTED - currentCompany is missing.")
                return False

            print("Current company ID:", company_ids)

            current_page_number = 1
            try:
                raw_page = (
                    before_query.get("page", ["1"])
                    or ["1"]
                )[0]
                current_page_number = max(
                    1,
                    int(str(raw_page).strip()),
                )
            except Exception:
                current_page_number = 1

            target_page_number = current_page_number + 1

            parsed = urlsplit(before_url)
            pairs = []

            for key, value in parse_qsl(
                parsed.query,
                keep_blank_values=True,
            ):
                key_lower = key.lower()

                if key_lower == "page":
                    continue

                pairs.append((key, value))

            # Match the pagination parameters LinkedIn itself has been
            # observed adding in this workflow.
            existing_keys = {
                str(key).lower()
                for key, _ in pairs
            }

            if "spellcorrectionenabled" not in existing_keys:
                pairs.append(
                    ("spellCorrectionEnabled", "true")
                )

            if "prioritizemessage" not in existing_keys:
                pairs.append(
                    ("prioritizeMessage", "false")
                )

            pairs.append(
                ("page", str(target_page_number))
            )

            direct_next_url = urlunsplit(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    urlencode(pairs),
                    parsed.fragment,
                )
            )

            print(
                "Direct next-page URL:",
                direct_next_url,
            )

            def blocked(url):
                lower = str(url or "").lower()

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

            def parse_page_number(url):
                try:
                    query = parse_qs(
                        urlsplit(url).query,
                        keep_blank_values=True,
                    )
                    raw = (
                        query.get("page", ["1"])
                        or ["1"]
                    )[0]
                    return max(
                        1,
                        int(str(raw).strip()),
                    )
                except Exception:
                    return 1

            def is_valid_unfiltered_people_url(url):
                if not url or blocked(url):
                    return False

                lower = str(url).lower()

                if (
                    "/search/results/people/" not in lower
                    or "currentcompany=" not in lower
                ):
                    return False

                try:
                    query = parse_qs(
                        urlsplit(url).query,
                        keep_blank_values=True,
                    )

                    actual_company_ids = (
                        query.get("currentCompany", [])
                        or query.get("currentcompany", [])
                    )

                    actual_network = (
                        query.get("network", [])
                        or query.get("Network", [])
                    )

                except Exception:
                    return False

                def network_scope_matches():
                    if not expected_network:
                        return not actual_network

                    if not actual_network:
                        return True

                    expected_text = " ".join(expected_network).lower()
                    actual_text = " ".join(actual_network).lower()

                    expected_tokens = {
                        token
                        for token in re.findall(r'"([fso])"', expected_text)
                    }
                    actual_tokens = {
                        token
                        for token in re.findall(r'"([fso])"', actual_text)
                    }

                    if not expected_tokens:
                        return actual_text == expected_text

                    return expected_tokens.issubset(actual_tokens)

                return (
                    actual_company_ids == company_ids
                    and network_scope_matches()
                )

            def result_dom_ready(page):
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

                for attempt in range(1, 31):
                    try:
                        page.wait_for_timeout(500)
                    except Exception:
                        pass

                    try:
                        visible_links = page.locator(
                            "a[href*='/in/']"
                        ).count()
                    except Exception:
                        visible_links = 0

                    rendered_cards = 0

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
                            rendered_cards = max(
                                rendered_cards,
                                page.locator(selector).count(),
                            )
                        except Exception:
                            continue

                    rendered_result_text = False

                    try:
                        body_text = page.locator(
                            "body"
                        ).inner_text(timeout=2000)

                        normalized = re.sub(
                            r"\s+",
                            " ",
                            body_text or "",
                        ).strip().lower()

                        role_hits = sum(
                            1
                            for signal in role_signals
                            if signal in normalized
                        )

                        result_hits = sum(
                            1
                            for word in result_words
                            if word in normalized
                        )

                        rendered_result_text = (
                            len(normalized) >= 800
                            and role_hits >= 2
                            and result_hits >= 1
                        )

                    except Exception:
                        pass

                    print(
                        f"Direct next-page DOM wait {attempt}/30:",
                        visible_links,
                        "visible /in/ links;",
                        rendered_cards,
                        "result cards;",
                        rendered_result_text,
                        "employee-result text",
                    )

                    if (
                        visible_links > 0
                        or rendered_cards > 0
                        or rendered_result_text
                    ):
                        return True

                return False

            # ------------------------------------------------------------
            # PRIMARY PATH: direct URL in a fresh authenticated tab.
            # ------------------------------------------------------------
            navigation_page = None

            try:
                navigation_page = (
                    before_page.context.new_page()
                )

                print(
                    "Trying authenticated direct next-page navigation..."
                )

                print(
                    "Referer:",
                    before_url,
                )

                try:
                    navigation_page.goto(
                        direct_next_url,
                        wait_until="domcontentloaded",
                        timeout=60000,
                        referer=before_url,
                    )
                except Exception as ex:
                    print(
                        "Direct next-page goto raised:",
                        repr(ex),
                    )

                try:
                    navigation_page.wait_for_timeout(5000)
                except Exception:
                    pass

                candidate_url = str(
                    navigation_page.url or ""
                ).strip()

                print(
                    "Direct next-page final URL:",
                    candidate_url,
                )

                if (
                    is_valid_unfiltered_people_url(
                        candidate_url
                    )
                    and
                    parse_page_number(candidate_url)
                    >= target_page_number
                ):

                    if result_dom_ready(
                        navigation_page
                    ):

                        old_page = before_page
                        self.page = navigation_page

                        print(
                            "NEXT PAGE VALIDATED VIA DIRECT URL"
                        )
                        print(
                            "Company scope preserved:",
                            company_ids,
                        )
                        print(
                            "Network scope preserved/canonicalized:",
                            expected_network if expected_network else "UNRESTRICTED",
                        )
                        print(
                            "Page number:",
                            parse_page_number(candidate_url),
                        )

                        if old_page is not navigation_page:
                            try:
                                if not old_page.is_closed():
                                    old_page.close()
                                    print(
                                        "Previous employee-search tab "
                                        "closed after new page validation."
                                    )
                            except Exception as ex:
                                print(
                                    "Previous employee-search tab "
                                    "cleanup warning:",
                                    repr(ex),
                                )

                        navigation_page = None
                        return True

                print(
                    "Direct next-page navigation was not accepted."
                )

            except Exception as ex:
                print(
                    "Direct next-page recovery failed:",
                    repr(ex),
                )

            finally:
                if navigation_page is not None:
                    try:
                        if not navigation_page.is_closed():
                            navigation_page.close()
                    except Exception:
                        pass

            # ------------------------------------------------------------
            # FALLBACK: existing Next control.
            # ------------------------------------------------------------
            self.page = before_page

            selectors = (
                "button[data-testid='pagination-controls-next-button-visible']:visible",
                "nav[aria-label*='Pagination' i] button:visible",
                "nav[aria-label*='Pagination' i] a:visible",
                "div.artdeco-pagination button:visible",
                "div.artdeco-pagination a:visible",
            )

            next_control = None

            for selector in selectors:
                try:
                    controls = self.page.locator(selector)

                    for i in range(controls.count()):
                        control = controls.nth(i)

                        text = ""
                        aria = ""
                        title = ""

                        try:
                            text = (
                                control.inner_text(
                                    timeout=1000
                                ).strip()
                            )
                        except Exception:
                            pass

                        try:
                            aria = (
                                control.get_attribute(
                                    "aria-label"
                                )
                                or ""
                            ).strip()
                        except Exception:
                            pass

                        try:
                            title = (
                                control.get_attribute(
                                    "title"
                                )
                                or ""
                            ).strip()
                        except Exception:
                            pass

                        label = " ".join(
                            x
                            for x in (
                                text,
                                aria,
                                title,
                            )
                            if x
                        ).lower()

                        if "next" not in label:
                            continue

                        try:
                            if control.is_disabled():
                                continue
                        except Exception:
                            pass

                        if control.is_visible():
                            next_control = control

                            print(
                                "Fallback Next control found:",
                                selector,
                                "[",
                                i,
                                "]",
                            )

                            print(
                                "Fallback Next label:",
                                label,
                            )

                            break

                    if next_control is not None:
                        break

                except Exception as ex:
                    print(
                        "Fallback Next selector inspection failed:",
                        selector,
                        repr(ex),
                    )

            if next_control is None:
                print(
                    "No usable Next control found."
                )
                return False

            try:
                next_control.scroll_into_view_if_needed()
            except Exception:
                pass

            try:
                next_control.click(
                    timeout=15000
                )
            except Exception as ex:
                print(
                    "Fallback Next click failed:",
                    repr(ex),
                )
                return False

            for attempt in range(1, 31):
                self.page.wait_for_timeout(500)

                current_url = str(
                    self.page.url or ""
                ).strip()

                if blocked(current_url):
                    print(
                        "Fallback Next hit LinkedIn auth/SSR redirect."
                    )
                    print(
                        "Fallback Next URL:",
                        current_url,
                    )
                    return False

                if not is_valid_unfiltered_people_url(
                    current_url
                ):
                    continue

                if (
                    parse_page_number(current_url)
                    < target_page_number
                ):
                    continue

                if result_dom_ready(
                    self.page
                ):
                    print(
                        "NEXT PAGE VALIDATED VIA FALLBACK NEXT CONTROL"
                    )
                    return True

            print(
                "NEXT FAILED - neither direct URL navigation nor "
                "Next control produced a validated next page."
            )
            return False

        except Exception as ex:
            print(
                "Pagination failed:",
                repr(ex),
            )
            return False

