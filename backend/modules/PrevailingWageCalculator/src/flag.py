from playwright.sync_api import sync_playwright
from .mappings import AREA_MAP


class FlagWebsite:

    def __init__(self):

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=False,
            slow_mo=300
        )

        self.page = self.browser.new_page()

    def search(self, occupation_code, state, county):

        page = self.page

        print("=" * 60)
        print("Searching FLAG Website")
        print("=" * 60)
        print("Occupation :", occupation_code)
        print("State      :", state)
        print("County     :", county)
        print()

        # --------------------------------------------------
        # Open Website
        # --------------------------------------------------

        page.goto("https://flag.dol.gov/wage-data/wage-search")

        page.wait_for_load_state("networkidle")

        # --------------------------------------------------
        # Wage Year
        # --------------------------------------------------

        page.get_by_label("dateSeries-select").select_option(
            "7/2026 - 6/2027"
        )

        # --------------------------------------------------
        # Occupation
        # --------------------------------------------------

        page.get_by_text("All Industries").click()

        textbox = page.get_by_role(
            "textbox",
            name="Type search term here"
        )

        textbox.click()
        textbox.fill(occupation_code)

        page.wait_for_timeout(1200)

        page.get_by_text(
            f"{occupation_code}.00"
        ).click()

        # --------------------------------------------------
        # State
        # --------------------------------------------------

        page.get_by_label("state-select").select_option(state)

        page.wait_for_timeout(1500)

        # --------------------------------------------------
        # County / Township
        # --------------------------------------------------

        page.get_by_text("County/ Township").click()

        # Give FLAG time to populate the Area dropdown
        page.wait_for_timeout(2500)

        # --------------------------------------------------
        # Area
        # --------------------------------------------------

        normalized_county = county.title()
        area = AREA_MAP[(state, normalized_county)]

        print("Selected Area :", area)

        page.get_by_label(
            "areaSelect-select"
        ).select_option(area)

        page.wait_for_timeout(1000)

        # --------------------------------------------------
        # Submit
        # --------------------------------------------------

        page.get_by_role(
            "button",
            name="Submit"
        ).click()

        page.wait_for_load_state("networkidle")

        page.wait_for_timeout(3000)

        # --------------------------------------------------
        # Read Wage Table
        # --------------------------------------------------

        table = page.locator("table").first.inner_text()

        print("Search completed.")

        return table

    def close(self):

        self.browser.close()

        self.playwright.stop()
