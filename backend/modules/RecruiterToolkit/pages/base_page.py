from automation.smart_locator import SmartLocator


class BasePage:

    def __init__(self, page):

        self.page = page
        self.smart = SmartLocator(page)

    # ---------------------------
    # Navigation
    # ---------------------------

    def open(self, url):
        self.page.goto(url)

    def refresh(self):
        self.page.reload()

    def back(self):
        self.page.go_back()

    # ---------------------------
    # Mouse
    # ---------------------------

    def click(self, selectors):

        self.smart.find(selectors).click()

    def dblclick(self, selectors):

        self.smart.find(selectors).dblclick()

    def hover(self, selectors):

        self.smart.find(selectors).hover()

    # ---------------------------
    # Keyboard
    # ---------------------------

    def fill(self, selectors, value):

        self.smart.find(selectors).fill(value)

    def type(self, selectors, value):

        self.smart.find(selectors).type(value)

    def press(self, selectors, key):

        self.smart.find(selectors).press(key)

    # ---------------------------
    # Dropdown
    # ---------------------------

    def select(self, selectors, value):

        self.smart.find(selectors).select_option(value)

    # ---------------------------
    # Checkbox
    # ---------------------------

    def check(self, selectors):

        self.smart.find(selectors).check()

    def uncheck(self, selectors):

        self.smart.find(selectors).uncheck()

    # ---------------------------
    # Read
    # ---------------------------

    def text(self, selectors):

        return self.smart.find(selectors).inner_text().strip()

    def texts(self, selectors):

        return [
            x.inner_text().strip()
            for x in self.smart.find(selectors).all()
        ]

    def value(self, selectors):

        return self.smart.find(selectors).input_value()

    def html(self, selectors):

        return self.smart.find(selectors).inner_html()

    def attribute(self, selectors, name):

        return self.smart.find(selectors).get_attribute(name)

    # ---------------------------
    # State
    # ---------------------------

    def exists(self, selectors):

        return self.smart.find(selectors).count() > 0

    def visible(self, selectors):

        return self.smart.find(selectors).is_visible()

    def enabled(self, selectors):

        return self.smart.find(selectors).is_enabled()

    # ---------------------------
    # Wait
    # ---------------------------

    def wait(self, milliseconds):

        self.page.wait_for_timeout(milliseconds)

    # ---------------------------
    # Screenshot
    # ---------------------------

    def screenshot(self, file):

        self.page.screenshot(path=file)

    # ---------------------------
    # JavaScript
    # ---------------------------

    def js(self, script):

        return self.page.evaluate(script)
