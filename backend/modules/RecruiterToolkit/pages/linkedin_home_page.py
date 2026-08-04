from pages.base_page import BasePage


class LinkedInHomePage(BasePage):

    SEARCH_BOX = [
        "input[placeholder='Search']"
    ]

    def search(self, text):

        self.fill(self.SEARCH_BOX, text)

        self.press(self.SEARCH_BOX, "Enter")
