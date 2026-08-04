from pages.base_page import BasePage


class SearchPage(BasePage):

    SEARCH_INPUT = [
        "input[placeholder*='looking']",
        "input[placeholder*='Looking']",
        "input[role='combobox']",
        ".search-global-typeahead__input",
        "input"
    ]

    def search_company(self, company):

        self.page.wait_for_timeout(3000)

        search_box = self.smart.find(
            self.SEARCH_INPUT
        )

        search_box.click()
        search_box.fill(company)
        search_box.press("Enter")

        self.page.wait_for_timeout(5000)

    def get_profile_urls(self):

        profile_links = self.page.locator(
            "a[href*='/in/']"
        )

        urls = set()

        count = profile_links.count()

        for i in range(count):

            try:

                href = profile_links.nth(i).get_attribute(
                    "href"
                )

                if not href:
                    continue

                if "/in/" not in href:
                    continue

                clean_url = href.split("?")[0]

                if not clean_url.startswith("http"):

                    clean_url = (
                        "https://www.linkedin.com"
                        + clean_url
                    )

                urls.add(clean_url)

            except Exception:
                pass

        return list(urls)
