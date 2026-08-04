from pages.login_page import LoginPage


class LoginWorkflow:

    def __init__(self, browser):

        self.browser = browser
        self.page = browser.new_page()

        self.login_page = LoginPage(
            self.page
        )

    def run(self):

        self.page.goto(
            "https://www.linkedin.com/login"
        )

        print(
            "Please complete LinkedIn login in browser."
        )

        while True:

            self.page.wait_for_timeout(2000)

            current_url = self.page.url

            print(current_url)

            if "feed" in current_url:

                print(
                    "LinkedIn login successful."
                )

                return self.page
