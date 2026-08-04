import re

from pages.base_page import BasePage


class DetailsPage(BasePage):

    TITLE = [
        "h1"
    ]

    COMPANY = [
        ".company"
    ]

    LOCATION = [
        ".location"
    ]

    DESCRIPTION = [
        ".description"
    ]

    def get_email(self):

        text = self.page.locator("body").inner_text()

        match = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            text
        )

        if match:
            return match.group()

        return ""

    def get_data(self):

        return {

            "Title": self.text(self.TITLE),

            "Company": self.text(self.COMPANY),

            "Location": self.text(self.LOCATION),

            "Email": self.get_email(),

            "Description": self.text(self.DESCRIPTION)

        }
