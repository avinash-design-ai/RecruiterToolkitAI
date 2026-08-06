from pages.base_page import BasePage
import os


class LoginPage(BasePage):

    USERNAME = [
        "input[autocomplete='username']",
        "input[type='email']",
        "#username",
        "input[name='session_key']"
    ]

    PASSWORD = [
        "input[autocomplete='current-password']",
        "input[type='password']",
        "#password",
        "input[name='session_password']"
    ]

    def click_login(self):

        print("=" * 60)
        print("Searching for LinkedIn Sign In button")
        print("=" * 60)

        # Preferred ARIA selector
        try:

            self.page.get_by_role(
                "button",
                name="Sign in"
            ).click(timeout=3000)

            print("Clicked Sign In using role")

            return

        except Exception:
            pass

        # Exact visible text
        try:

            self.page.get_by_text(
                "Sign in",
                exact=True
            ).click(timeout=3000)

            print("Clicked Sign In using text")

            return

        except Exception:
            pass

        # Final fallback
        buttons = self.page.locator("button")

        for i in range(buttons.count()):

            try:

                btn = buttons.nth(i)

                if not btn.is_visible():
                    continue

                text = btn.inner_text().strip()

                print(i, text)

                if text.lower() == "sign in":

                    btn.click()

                    print("Clicked Sign In button")

                    return

            except Exception:
                pass

        raise Exception("LinkedIn Sign In button not found.")

    def login(self, username, password):

        print("=" * 60)
        print("Waiting for LinkedIn login page...")
        print("=" * 60)

        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_timeout(3000)

        print("=" * 60)
        print("PAGE TITLE")
        print("=" * 60)
        print(self.page.title())
        print(self.page.url)

        print("=" * 60)
        print("INPUT ELEMENTS")
        print("=" * 60)

        inputs = self.page.locator("input")

        count = inputs.count()

        print("INPUT COUNT:", count)

        for i in range(count):

            try:

                el = inputs.nth(i)

                print(
                    i,
                    {
                        "id": el.get_attribute("id"),
                        "name": el.get_attribute("name"),
                        "type": el.get_attribute("type"),
                        "placeholder": el.get_attribute("placeholder"),
                        "visible": el.is_visible()
                    }
                )

            except Exception as ex:

                print(ex)

        print("=" * 60)

        os.makedirs("screenshots", exist_ok=True)

        self.page.screenshot(
            path="screenshots/login_page.png",
            full_page=True
        )

        print(
            "Screenshot saved:",
            os.path.exists("screenshots/login_page.png")
        )

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

        self.click_login()

        print("Waiting after login...")

        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_timeout(5000)

        print("Login completed.")
