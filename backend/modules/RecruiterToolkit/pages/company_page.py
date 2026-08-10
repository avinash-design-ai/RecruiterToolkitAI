from pages.base_page import BasePage


class CompanyPage(BasePage):

    def __init__(self, page):
        super().__init__(page)

    def search_company(self, company):

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

                # Exact match only
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

        # Validation
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

    def open_employees_page(self):

        print("Looking for employee search URL...")

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

                if (
                    "/search/results/people/"
                    not in href
                ):
                    continue

                if (
                    "currentCompany"
                    not in href
                ):
                    continue

                candidate_urls.append(href)

            except Exception:
                pass

        if not candidate_urls:

            print(
                "Employee search URL not found"
            )

            return False

        print(
            f"Found {len(candidate_urls)} candidate URLs"
        )

        best_url = None

        for url in candidate_urls:

            score = 0

            if "schoolFilter" not in url:
                score += 1

            if "network=" not in url:
                score += 1

            if "origin=SCHOOL_HIRES" not in url:
                score += 1

            if "origin=SHARED_CONNECTIONS" not in url:
                score += 1

            if "origin=JOB_PAGE" not in url:
                score += 1

            if score >= 4:

                best_url = url
                break

        if not best_url:

            best_url = candidate_urls[0]

        remove_values = [

            "&network=%5B%22F%22%5D",
            "&network=%5B%22S%22%5D",
            "&network=%5B%22O%22%5D",

            "&schoolFilter=%5B%22%22%5D",

            "&origin=SCHOOL_HIRES_IN_COMPANY_CANNED_SEARCH",
            "&origin=SHARED_CONNECTIONS_IN_COMPANY_CANNED_SEARCH",
            "&origin=JOB_PAGE_CANNED_SEARCH"
        ]

        for value in remove_values:

            best_url = best_url.replace(
                value,
                ""
            )

        print("Using URL:")
        print(best_url)

        self.page.goto(
            best_url,
            wait_until="domcontentloaded"
        )

        self.page.wait_for_timeout(
            5000
        )

        print(
            "Employee page loaded:"
        )

        print(self.page.url)

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

    def get_profiles(self):

        profiles = []

        links = self.page.locator(
            "a[href*='/in/']:visible"
        )

        count = links.count()

        print(
            f"Profile links found: {count}"
        )

        seen = set()

        for i in range(count):

            try:

                link = links.nth(i)

                href = link.get_attribute(
                    "href"
                )

                if not href:
                    continue

                text = (
                    link.inner_text()
                    .strip()
                )

                if not text:
                    continue

                if "\n" in text:
                    continue

                if len(text) > 40:
                    continue

                clean_url = href.split("?")[0]

                if not clean_url.startswith("http"):

                    clean_url = (
                        "https://www.linkedin.com"
                        + clean_url
                  )

                if clean_url in seen:
                    continue

                # Skip obvious mutual connections

                if text.count(" ") > 4:
                    continue

                if len(text) > 40:
                    continue

                seen.add(
                    clean_url
                )
                
                profiles.append(
                    {
                        "full_name": text,
                        "profile_url": clean_url
                    }
                )

            except Exception:
                pass

        print(
            f"Profiles extracted: {len(profiles)}"
        )

        return profiles

    def next_page(self):

        try:

            print("Trying next page...")
            print("NEW NEXT_PAGE EXECUTING")

            buttons = self.page.locator("button")

            for i in range(buttons.count()):

                try:

                    btn = buttons.nth(i)

                    text = btn.inner_text().strip()

                    if text == "Next":

                        print("Clicking Next")

                        btn.click()

                        self.page.wait_for_timeout(5000)

                        print(
                            "Current URL after next:"
                        )

                        print(self.page.url)

                        return True

                except Exception:
                    pass

            print("Next button not found")

            return False

        except Exception as ex:

            print(
                "Next page failed:",
                ex
            )

            return False
