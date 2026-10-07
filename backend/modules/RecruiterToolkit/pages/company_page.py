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

        # Preserve LinkedIn's exact selected company URL for later recovery.
        # This is used only to obtain LinkedIn's own unfiltered employee-search
        # link when the company click lands directly on network=["F"].
        self._selected_company_href = company_href

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
            """Return the live LinkedIn All Filters panel across UI variants."""

            # LinkedIn does not always expose All Filters as role=dialog or
            # .artdeco-modal. Some sessions render it as a drawer/section with
            # no modal semantics, so detection is based on Connections/degree
            # content plus common modal/filter containers.
            selectors = (
                "[role='dialog']:visible",
                "[aria-modal='true']:visible",
                "dialog[open]:visible",
                ".artdeco-modal:visible",
                ".artdeco-modal__content:visible",
                "[class*='modal']:visible",
                "[class*='drawer']:visible",
                "[class*='filter']:visible",
            )

            def panel_text(item):
                try:
                    return normalized_label(item.inner_text(timeout=1500) or "")
                except Exception:
                    return normalized_label(label_for(item))

            def looks_like_filter_panel(item):
                try:
                    if not item.is_visible():
                        return False

                    txt = panel_text(item)
                    if not txt:
                        return False

                    classes = (item.get_attribute("class") or "").lower()
                    has_connections = "connections" in txt
                    has_degrees = (
                        re.search(r"\b1st\b", txt) is not None
                        or re.search(r"\b2nd\b", txt) is not None
                        or re.search(r"\b3rd\+?\b", txt) is not None
                    )
                    has_filter_words = (
                        "all filters" in txt
                        or "filters" in txt
                        or "modal" in classes
                        or "drawer" in classes
                        or "filter" in classes
                    )

                    return has_connections and (has_filter_words or has_degrees)
                except Exception:
                    return False

            # The panel can be mid-transition immediately after clicking All Filters.
            # Reacquire it for several short attempts rather than assuming a 1-second
            # render time.
            for _ in range(8):
                for selector in selectors:
                    try:
                        loc = self.page.locator(selector)
                        for i in range(min(loc.count(), 40)):
                            item = loc.nth(i)
                            if looks_like_filter_panel(item):
                                return item
                    except Exception:
                        continue
                try:
                    self.page.wait_for_timeout(350)
                except Exception:
                    pass

            # Fallback: locate the authoritative visible Connections heading or
            # All Filters heading, then walk upward to a bounded ancestor that
            # contains the filter/degree UI. This covers LinkedIn variants without
            # dialog semantics.
            for exact_text in ("Connections", "All Filters", "All filters"):
                try:
                    loc = self.page.get_by_text(exact_text, exact=True)
                    for i in range(min(loc.count(), 30)):
                        node = loc.nth(i)
                        if not node.is_visible():
                            continue

                        current = node
                        for _ in range(10):
                            try:
                                if looks_like_filter_panel(current):
                                    return current

                                parent = current.locator("xpath=../").first
                                if parent.count() == 0 or not parent.is_visible():
                                    break
                                current = parent
                            except Exception:
                                break
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


        def _control_like_candidate(item, wanted=None):
            try:
                if not item.is_visible():
                    return False
                if wanted is not None:
                    label = normalized_label(label_for(item))
                    if label not in wanted:
                        return False
                role = (item.get_attribute("role") or "").strip().lower()
                tag = (item.evaluate("el => el.tagName") or "").strip().lower()
                if role in ("checkbox", "radio", "option", "button") or tag in ("label", "button"):
                    return True
                if item.locator("input[type='checkbox'], input[type='radio']").count() > 0:
                    return True
                node = item
                for _ in range(5):
                    parent = node.locator("xpath=../").first
                    if parent.count() == 0:
                        break
                    prole = (parent.get_attribute("role") or "").strip().lower()
                    ptag = (parent.evaluate("el => el.tagName") or "").strip().lower()
                    if prole in ("checkbox", "radio", "option", "button") or ptag in ("label", "button"):
                        return True
                    if parent.locator("input[type='checkbox'], input[type='radio']").count() > 0:
                        return True
                    node = parent
            except Exception:
                return False
            return False

        def _fresh_connections_scope():
            dialog = filter_dialog()
            if dialog is None:
                return None

            try:
                heading = dialog.get_by_text("Connections", exact=True).last
                if heading.count() and heading.is_visible():
                    try:
                        parent = heading.locator("xpath=.. ").first
                        if parent.count() and parent.is_visible():
                            txt = normalized_label(label_for(parent))
                            if len(txt) <= 300:
                                return parent
                    except Exception:
                        pass
            except Exception:
                pass

            return dialog

        def _degree_control_candidates(scope):
            if scope is None:
                return []
            selectors = (
                "label:visible",
                "[role='checkbox']:visible",
                "[role='radio']:visible",
                "[role='option']:visible",
                "button:visible",
                "li:visible",
                "span:visible",
                "div:visible",
            )
            candidates = []
            seen = set()
            for selector in selectors:
                try:
                    loc = scope.locator(selector)
                    for i in range(min(loc.count(), 1500)):
                        item = loc.nth(i)
                        if not item.is_visible():
                            continue
                        label = normalized_label(label_for(item))
                        if not label or len(label) > 80 or label in seen:
                            continue
                        if not _control_like_candidate(item):
                            continue
                        seen.add(label)
                        candidates.append(item)
                except Exception:
                    continue
            return candidates

        def _third_degree_semantic_candidate():
            scope = _fresh_connections_scope()
            candidates = _degree_control_candidates(scope)
            if not candidates:
                print("Third-degree resolver: no interactive Connections controls found.")
                return None

            patterns = (
                re.compile(r"^3(?:rd)?\\s*\\+?(?:\\s*(?:degree|degrees|connections?|network))?$", re.I),
                re.compile(r"^(?:third|third-degree|third degree)(?:\\s*\\+)?(?:\\s*(?:connections?|network))?$", re.I),
                re.compile(r"(?:3rd|third).*(?:degree|connection|network)", re.I),
                re.compile(r"(?:outside|out of).*network", re.I),
            )
            for item in candidates:
                label = normalized_label(label_for(item))
                if any(p.search(label) for p in patterns):
                    print("Third-degree control located semantically:", label_for(item).strip())
                    return item

            first = {"1st", "1st degree", "1st degree connections", "first"}
            second = {"2nd", "2nd degree", "2nd degree connections", "second"}
            unrelated = ("location", "industry", "company", "school", "followers")
            remaining = []
            for item in candidates:
                label = normalized_label(label_for(item))
                if label in first or label in second:
                    continue
                if any(term in label for term in unrelated):
                    continue
                remaining.append(item)

            if len(remaining) == 1:
                print("Third-degree control resolved as remaining Connections option:", label_for(remaining[0]).strip())
                return remaining[0]

            unselected = []
            for item in remaining:
                try:
                    if not degree_is_selected(item):
                        unselected.append(item)
                except Exception:
                    pass
            if len(unselected) == 1:
                print("Third-degree control resolved as only unselected Connections option:", label_for(unselected[0]).strip())
                return unselected[0]

            print("Third-degree resolver ambiguous; Connections candidates:", [label_for(x).strip() for x in candidates])
            return None

        def find_degree_option(patterns):
            wanted = {normalized_label(p) for p in patterns if p}

            if any(normalized_label(p) in {"3rd+", "3rd +", "3rd"} for p in patterns if p):
                semantic = _third_degree_semantic_candidate()
                if semantic is not None:
                    return semantic

            scopes = []
            live_scope = _fresh_connections_scope()
            if live_scope is not None:
                scopes.append(live_scope)
            dialog = filter_dialog()
            if dialog is not None and all(root is not dialog for root in scopes):
                scopes.append(dialog)

            for root in scopes:
                for selector in (
                    "label:visible",
                    "[role='checkbox']:visible",
                    "[role='radio']:visible",
                    "[role='option']:visible",
                    "button:visible",
                    "li:visible",
                    "span:visible",
                    "div:visible",
                ):
                    try:
                        loc = root.locator(selector)
                        for i in range(min(loc.count(), 1500)):
                            item = loc.nth(i)
                            if not item.is_visible():
                                continue
                            if normalized_label(label_for(item)) not in wanted:
                                continue
                            if _control_like_candidate(item, wanted):
                                print("Degree option located:", label_for(item).strip())
                                return item
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

            if network_text and any(x in network_text for x in ("s", "o")):
                print("Connection-degree filter: already broad enough")
                print("Company scope preserved:", ids)
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
            if not open_connections_section():
                print("ERROR: Connections section is not available.")
                return False

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
            return True

        # ================================================================
        # CASE 2: still on company page; use LinkedIn's genuine people-search
        # links, then validate the URL LinkedIn produces after the click.
        # ================================================================
        links = self.page.locator("a[href*='/search/results/people/']")
        count = links.count()
        print("People-search links found:", count)

        candidates = []
        for i in range(count):
            try:
                link = links.nth(i)
                if not link.is_visible():
                    continue
                href = (link.get_attribute("href") or "").strip()
                if not href or "/search/results/people/" not in href.lower():
                    continue

                parts = []
                for attr in ("aria-label", "title"):
                    value = (link.get_attribute(attr) or "").strip()
                    if value:
                        parts.append(value)
                try:
                    txt = (link.inner_text(timeout=1000) or "").strip()
                    if txt:
                        parts.append(txt)
                except Exception:
                    pass
                label = normalized_label(" ".join(parts))
                lower_href = href.lower()

                score = 10
                if "currentcompany=" in lower_href:
                    score += 100
                if any(token in lower_href for token in (
                    "company_hires", "company_employees", "company_people", "company_canned"
                )):
                    score += 70
                if any(token in label for token in (
                    "employees", "employee", "people", "team", "all employees", "see all"
                )):
                    score += 50
                if "pastcompany" in lower_href:
                    score -= 20

                candidates.append((score, i, label, href))
            except Exception:
                continue

        candidates.sort(key=lambda item: (-item[0], item[1]))
        print("Bounded people-search candidates:", len(candidates))

        company_page_url = current_url
        for position, (score, original_index, label, href) in enumerate(candidates[:8], start=1):
            print("Trying company employee-search link %d/8:" % position)
            print("Link score:", score)
            print("Link label:", label)
            print("Link href:", href)

            try:
                live = self.page.locator("a[href*='/search/results/people/']").nth(original_index)
                live.scroll_into_view_if_needed()
                live.click(timeout=15000)
                self.page.wait_for_timeout(5000)
            except Exception as ex:
                print("People-search candidate click failed:", repr(ex))
                try:
                    if str(self.page.url or "") != company_page_url:
                        self.page.go_back(wait_until="domcontentloaded", timeout=30000)
                        self.page.wait_for_timeout(2500)
                except Exception:
                    pass
                continue

            final_url = str(self.page.url or "").strip()
            print("Employee-search URL after click:", final_url)

            if is_blocked_url(final_url) or not is_people_url(final_url):
                print("Candidate did not resolve to an authenticated people search.")
                try:
                    self.page.go_back(wait_until="domcontentloaded", timeout=30000)
                    self.page.wait_for_timeout(2500)
                except Exception:
                    pass
                continue

            final_ids = company_ids(final_url)
            if not final_ids:
                print("Candidate people search has no currentCompany; trying next candidate.")
                try:
                    self.page.go_back(wait_until="domcontentloaded", timeout=30000)
                    self.page.wait_for_timeout(2500)
                except Exception:
                    pass
                continue

            print("Validated company-scoped people search:", final_ids)
            return self.open_employees_page()

        print("ERROR: No genuine company employee-search link produced an authenticated company-scoped people search.")
        print("Current URL:", self.page.url)
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
        Advance pagination using LinkedIn's own live Next control.

        This deliberately mirrors the proven desktop workflow:
        the current authenticated people-search page owns pagination, and
        LinkedIn performs the transition itself. We do NOT synthesize
        page=N URLs and do NOT replace the search page with a fresh tab.

        Why:
        LinkedIn's company-canned people search can accept a synthetic
        ``&page=2`` URL while still rendering an empty employee DOM in
        GitHub Actions. The real Next control changes LinkedIn's search
        state (including the origin/query state) before rendering the next
        result page. That transition is what we need to preserve.
        """

        from urllib.parse import parse_qs, urlsplit

        page = self.page
        before_url = str(getattr(page, "url", "") or "").strip()

        print("=" * 60)
        print("PAGINATION")
        print("=" * 60)
        print("Current URL:", before_url)

        def blocked(url):
            lower = str(url or "").lower()
            return any(
                marker in lower
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

        def query(url):
            return parse_qs(
                urlsplit(str(url or "")).query,
                keep_blank_values=True,
            )

        def company_ids(url):
            data = query(url)
            return data.get("currentCompany", []) or data.get("currentcompany", [])

        expected_company = company_ids(before_url)
        if not expected_company:
            print("ERROR: Pagination cannot start without currentCompany scope.")
            return False

        def page_number(url):
            values = query(url).get("page", [])
            if not values:
                return 1
            try:
                return max(1, int(str(values[0]).strip()))
            except Exception:
                return 1

        before_page = page_number(before_url)
        target_page = before_page + 1

        def result_signature(active_page):
            """Return a compact signature of the currently rendered result set."""
            pieces = []

            for selector in (
                "li.reusable-search__result-container:visible",
                "li[class*='reusable-search__result']:visible",
                "li.entity-result:visible",
                "div.entity-result:visible",
                "li.search-result:visible",
                "li[class*='search-result']:visible",
            ):
                try:
                    rows = active_page.locator(selector)
                    for i in range(min(rows.count(), 12)):
                        try:
                            txt = " ".join(
                                str(rows.nth(i).inner_text(timeout=800) or "").split()
                            ).strip()
                            if txt:
                                pieces.append(txt[:900])
                        except Exception:
                            continue
                    if pieces:
                        break
                except Exception:
                    continue

            try:
                links = active_page.locator("a[href*='/in/']:visible")
                for i in range(min(20, links.count())):
                    try:
                        href = (links.nth(i).get_attribute("href") or "").strip()
                        if href:
                            pieces.append(href.split("?", 1)[0].split("#", 1)[0].rstrip("/").lower())
                    except Exception:
                        continue
            except Exception:
                pass

            if not pieces:
                try:
                    body = " ".join(
                        str(active_page.locator("body").inner_text(timeout=1200) or "").split()
                    )
                    if body:
                        pieces.append(body[:5000])
                except Exception:
                    pass

            return "\n".join(pieces)

        def rendered_state(active_page):
            links = 0
            cards = 0
            has_employee_text = False
            explicit_no_results = False

            try:
                links = active_page.locator("a[href*='/in/']:visible").count()
            except Exception:
                pass

            for selector in (
                "li.reusable-search__result-container:visible",
                "li[class*='reusable-search__result']:visible",
                "li.entity-result:visible",
                "div.entity-result:visible",
                "li.search-result:visible",
                "li[class*='search-result']:visible",
            ):
                try:
                    cards = max(cards, active_page.locator(selector).count())
                except Exception:
                    continue

            try:
                body = " ".join(
                    str(active_page.locator("body").inner_text(timeout=1500) or "").split()
                ).lower()

                employee_markers = (
                    "view linkedin member",
                    "employees",
                    "people",
                    "connections",
                    "recruiter",
                    "talent acquisition",
                    "staffing",
                    "manager",
                    "engineer",
                    "analyst",
                    "consultant",
                )
                marker_hits = sum(1 for marker in employee_markers if marker in body)
                has_employee_text = len(body) >= 500 and marker_hits >= 2

                explicit_no_results = any(
                    marker in body
                    for marker in (
                        "no results",
                        "no people found",
                        "no results found",
                        "we couldn't find",
                    )
                )
            except Exception:
                pass

            return links, cards, has_employee_text, explicit_no_results

        def is_valid_search_page(url):
            lower = str(url or "").lower()
            if blocked(lower):
                return False
            if "/search/results/people/" not in lower:
                return False
            return company_ids(url) == expected_company

        def find_next_control(active_page):
            """Find LinkedIn's pagination Next control, not arbitrary page text."""
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
                    controls = active_page.locator(selector)
                    for i in range(min(30, controls.count())):
                        control = controls.nth(i)
                        if not control.is_visible():
                            continue

                        parts = []
                        for attr in ("aria-label", "title", "data-testid"):
                            try:
                                value = (control.get_attribute(attr) or "").strip()
                                if value:
                                    parts.append(value)
                            except Exception:
                                pass
                        try:
                            txt = (control.inner_text(timeout=500) or "").strip()
                            if txt:
                                parts.append(txt)
                        except Exception:
                            pass

                        label = " ".join(parts).lower()
                        if "next" not in label or "previous" in label:
                            continue

                        try:
                            if control.is_disabled():
                                continue
                        except Exception:
                            pass

                        if (control.get_attribute("aria-disabled") or "").strip().lower() == "true":
                            continue

                        return control
                except Exception:
                    continue

            return None

        before_signature = result_signature(page)
        print("Current result signature size:", len(before_signature))
        print("Target page number:", target_page)

        # Pagination controls live near the bottom of the LinkedIn results
        # page. Bring the live page to the pagination area before locating
        # Next; do not replace the page or construct a synthetic URL.
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(800)
        except Exception:
            pass

        # IMPORTANT: use the live authenticated page first. This is the
        # exact behavior that worked in the desktop version.
        next_control = find_next_control(page)
        if next_control is None:
            print("No enabled LinkedIn pagination Next control found.")
            print("Pagination end-of-results positively confirmed only if LinkedIn exposed no Next control.")
            return False

        try:
            next_control.scroll_into_view_if_needed()
        except Exception:
            pass

        try:
            label_parts = []
            for attr in ("aria-label", "title", "data-testid"):
                value = (next_control.get_attribute(attr) or "").strip()
                if value:
                    label_parts.append(value)
            try:
                txt = (next_control.inner_text(timeout=500) or "").strip()
                if txt:
                    label_parts.append(txt)
            except Exception:
                pass
            print("Clicking live LinkedIn Next control:", " | ".join(label_parts))
        except Exception:
            print("Clicking live LinkedIn Next control")

        try:
            next_control.click(timeout=15000, no_wait_after=True)
        except Exception as ex:
            print("Live Next click failed:", repr(ex))
            return False

        # LinkedIn may spend a few seconds changing the search origin and
        # replacing the virtualized result DOM. Wait for BOTH page transition
        # and actual rendered employee content. A URL containing page=2 by
        # itself is never considered success.
        for attempt in range(1, 81):
            try:
                page.wait_for_timeout(350)
            except Exception:
                pass

            current_url = str(page.url or "").strip()
            if blocked(current_url):
                print("Live Next redirected to an authentication/SSR page; refusing transition.")
                return False

            if not is_valid_search_page(current_url):
                continue

            current_page = page_number(current_url)
            current_signature = result_signature(page)
            links, cards, employee_text, no_results = rendered_state(page)

            url_advanced = current_page >= target_page
            content_changed = bool(current_signature) and current_signature != before_signature

            if attempt % 10 == 0:
                print(
                    f"Live Next validation {attempt}/80:",
                    "page=", current_page,
                    "url_advanced=", url_advanced,
                    "content_changed=", content_changed,
                    "links=", links,
                    "cards=", cards,
                    "employee_text=", employee_text,
                )

            # Never accept a synthetic/empty page transition. LinkedIn must
            # have actually rendered a NEW result set. A page-number change
            # plus the old DOM is not success.
            if url_advanced and content_changed and (links > 0 or cards > 0 or employee_text):
                    print("=" * 60)
                    print("NEXT PAGE VALIDATED VIA LIVE LINKEDIN CONTROL")
                    print("=" * 60)
                    print("Final next-page URL:", current_url)
                    print("Company scope preserved:", company_ids(current_url))
                    print("Page number:", current_page)
                    print(
                        "Rendered result state:",
                        links,
                        "visible /in/ links |",
                        cards,
                        "result cards |",
                        employee_text,
                        "employee-result text",
                    )
                    return True

            # LinkedIn explicitly saying no results is a genuine terminal state.
            if url_advanced and no_results and links == 0 and cards == 0 and not employee_text:
                print("End of LinkedIn results confirmed by the live search page.")
                return False

        print("ERROR: Live LinkedIn Next control did not produce a populated next result page.")
        print("Current URL after click:", page.url)
        return False
