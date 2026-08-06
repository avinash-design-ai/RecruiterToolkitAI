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

                locators = self.page.locator(selector)

                count = locators.count()

                log.info(f"{selector} -> {count} matches")

                for i in range(count):

                    locator = locators.nth(i)

                    try:

                        if locator.is_visible():

                            log.success(
                                f"Visible locator found: {selector} [{i}]"
                            )

                            return locator

                    except Exception:
                        pass

            except Exception as e:

                last_error = e

        raise Exception(
            f"No visible locator matched.\n"
            f"Tried: {selectors}\n"
            f"{last_error}"
        )
