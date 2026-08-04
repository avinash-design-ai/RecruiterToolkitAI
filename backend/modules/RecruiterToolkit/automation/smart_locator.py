from automation.logger import log


class SmartLocator:

    def __init__(self, page):
        self.page = page

    def find(self, selectors):

        if isinstance(selectors, str):
            selectors = [selectors]

        last_error = None

        for selector in selectors:

            try:

                locator = self.page.locator(selector).first

                locator.wait_for(
                    state="visible",
                    timeout=10000
                )

                log.success(
                    f"Locator found: {selector}"
                )

                return locator

            except Exception as e:

                last_error = e

        raise Exception(
            f"No locator matched.\n"
            f"Tried: {selectors}\n"
            f"{last_error}"
        )
