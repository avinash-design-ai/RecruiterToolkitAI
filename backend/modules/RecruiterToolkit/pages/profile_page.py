from pages.base_page import BasePage


class ProfilePage(BasePage):

    def open_profile(self, url):

        self.page.goto(
            url,
            wait_until="load"
        )

        self.page.wait_for_timeout(5000)

    def get_name(self):

        selectors = [
            "h1",
            ".text-heading-xlarge",
            ".pv-text-details__left-panel h1"
        ]

        for selector in selectors:

            try:

                text = (
                    self.page
                    .locator(selector)
                    .first
                    .inner_text()
                    .strip()
                )

                if text:
                    return text

            except Exception:
                pass

        return ""

    def get_headline(self):

        selectors = [
            ".text-body-medium",
            ".pv-text-details__left-panel .text-body-medium"
        ]

        for selector in selectors:

            try:

                text = (
                    self.page
                    .locator(selector)
                    .first
                    .inner_text()
                    .strip()
                )

                if text:
                    return text

            except Exception:
                pass

        return ""

    def get_location(self):

        try:

            spans = self.page.locator("span")

            for i in range(spans.count()):

                try:

                    text = (
                        spans.nth(i)
                        .inner_text()
                        .strip()
                    )

                    if "," in text and len(text) < 100:
                        return text

                except Exception:
                    pass

        except Exception:
            pass

        return ""

    def get_profile_data(self):

        full_name = self.get_name()

        parts = full_name.split()

        first_name = ""
        last_name = ""

        if len(parts) >= 1:
            first_name = parts[0]

        if len(parts) >= 2:
            last_name = parts[-1]

        data = {
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "headline": self.get_headline(),
            "location": self.get_location(),
            "profile_url": self.page.url
        }

        print(data)

        return data
