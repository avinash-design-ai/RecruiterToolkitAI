from pages.base_page import BasePage


class LoginPage(BasePage):

    USERNAME = [

        "#username",

        "input[name='session_key']",

        "input#username",

        "input[autocomplete='username']",

        "input[type='email']"

    ]

    PASSWORD = [

        "#password",

        "input[name='session_password']",

        "input#password",

        "input[autocomplete='current-password']",

        "input[type='password']"

    ]

    LOGIN = [

        "button[type='submit']",

        "button[data-litms-control-urn]",

        "button"

    ]

    def login(self, username, password):

        print("=" * 60)
        print("Waiting for LinkedIn login page...")
        print("=" * 60)

        self.page.wait_for_load_state("networkidle")
        print("=" * 60)
        print(self.page.content()[:5000])
        inputs = self.page.locator("input")

        print("INPUT COUNT:", inputs.count())

        for i in range(inputs.count()):

            try:
                print(
                    i,
                    inputs.nth(i).evaluate(
                        """el => ({
                            id: el.id,
                            name: el.name,
                            type: el.type,
                            placeholder: el.placeholder
                        })"""
                    )
                )
            except Exception as e:
                print(e)
        print("=" * 60)

        self.page.wait_for_timeout(3000)

        self.page.screenshot(
            path="screenshots/login_page.png",
            full_page=True
        )

        import os

        print("Screenshot Exists:",
              os.path.exists("/tmp/login_page.png"))
        print("Page title :", self.page.title())

        print("Current URL:", self.page.url)

        print("Filling username...")

        self.fill(
            self.USERNAME,
            username
        )

        print("Filling password...")

        self.fill(
            self.PASSWORD,
            password
        )

        print("Clicking Login...")

        self.click(
            self.LOGIN
        )

        self.page.wait_for_load_state("networkidle")

        self.page.wait_for_timeout(5000)
