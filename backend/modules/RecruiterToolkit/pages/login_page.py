from pages.base_page import BasePage


class LoginPage(BasePage):

    USERNAME = [
        "#username",
        "input[name='session_key']",
        "input[name='username']"
    ]

    PASSWORD = [
        "#password",
        "input[name='session_password']",
        "input[name='password']"
    ]

    LOGIN = [
        "button[type='submit']"
    ]

    def login(self, username, password):

        self.page.wait_for_load_state("domcontentloaded")

        self.page.screenshot(
            path="screenshots/login_page.png"
        )

        self.fill(
            self.USERNAME,
            username
        )

        self.fill(
            self.PASSWORD,
            password
        )

        self.click(
            self.LOGIN
        )

        self.page.wait_for_timeout(5000)
