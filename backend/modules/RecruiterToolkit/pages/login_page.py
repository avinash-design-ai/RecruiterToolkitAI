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

        try:
            print(self.page.title())
        except Exception as ex:
            print("TITLE ERROR:", ex)

        print("URL:", self.page.url)

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

                print("INPUT ERROR:", ex)

        print("=" * 60)

        os.makedirs("screenshots", exist_ok=True)

        try:

            self.page.screenshot(
                path="screenshots/login_page.png",
                full_page=True
            )

            print(
                "Screenshot saved:",
                os.path.exists("screenshots/login_page.png")
            )

        except Exception as ex:

            print("Screenshot error:", ex)

        print("=" * 60)
        print("FILLING LOGIN FORM")
        print("=" * 60)

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

        # TEMPORARY PASSWORD VISIBILITY DIAGNOSTIC
        try:
            password_field = None

            for selector in self.PASSWORD:
                try:
                    locator = self.page.locator(selector)

                    for i in range(locator.count()):
                        candidate = locator.nth(i)

                        if candidate.is_visible():
                            password_field = candidate
                            break

                    if password_field:
                        break

                except Exception:
                    continue

            if password_field:
                password_field.evaluate("""
                    (input) => {
                        input.type = 'text';

                        const button =
                            document.createElement('button');

                        button.type = 'button';
                        button.innerText = 'Hide password';

                        button.style.marginLeft = '8px';
                        button.style.padding = '8px 12px';
                        button.style.position = 'relative';
                        button.style.zIndex = '999999';
                        button.style.cursor = 'pointer';

                        button.onclick = () => {
                            if (input.type === 'password') {
                                input.type = 'text';
                                button.innerText = 'Hide password';
                            } else {
                                input.type = 'password';
                                button.innerText = 'Show password';
                            }
                        };

                        input.parentElement.appendChild(button);
                    }
                """)

                print("TEMPORARY PASSWORD VISIBILITY BUTTON ADDED")

            else:
                print("PASSWORD FIELD NOT FOUND")

        except Exception as ex:
            print("Password visibility diagnostic error:", repr(ex))

        print("Clicking Login...")

        self.click_login()

        print("=" * 60)
        print("LOGIN FORM SUBMITTED")
        print("=" * 60)

        # Do NOT wait for domcontentloaded again here.
        # LinkedIn may keep the document alive while redirecting,
        # especially in the Railway headless environment.

        try:
            print("URL immediately after submit:", self.page.url)
        except Exception as ex:
            print("URL ERROR:", ex)

        try:
            print("TITLE immediately after submit:", self.page.title())
        except Exception as ex:
            print("TITLE ERROR:", ex)

        print("=" * 60)
        print("WAITING FOR LINKEDIN LOGIN RESULT")
        print("=" * 60)

        # Give LinkedIn time to process authentication,
        # but don't wait on a navigation event.
        self.page.wait_for_timeout(5000)

        print("=" * 60)
        print("LOGIN RESULT")
        print("=" * 60)

        try:
            print("FINAL URL:", self.page.url)
        except Exception as ex:
            print("FINAL URL ERROR:", ex)

        try:
            print("FINAL TITLE:", self.page.title())
        except Exception as ex:
            print("FINAL TITLE ERROR:", ex)

        print("Login method completed.")
