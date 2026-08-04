from pages.base_page import BasePage


class LinkedInLoginPage(BasePage):

    USERNAME = [
        "input[name='session_key']"
    ]

    PASSWORD = [
        "input[name='session_password']"
    ]

    LOGIN_BUTTON = [
        "button[type='submit']"
    ]

    def login(self, username, password):

        self.fill(self.USERNAME, username)

        self.fill(self.PASSWORD, password)

        self.click(self.LOGIN_BUTTON)
