from playwright.sync_api import sync_playwright

from .config import (
    WAGE_YEAR,
    HEADLESS,
    SLOW_MO,
    SHORT_WAIT,
    LONG_WAIT,
)

from .occupations import STATE_MAP

from .exceptions import COUNTY_FIXES, SPECIAL_AREAS


class FlagWebsite:

    def __init__(self):

        self.playwright = sync_playwright().start()
        print("HEADLESS =", HEADLESS)
        print("Playwright launching Chromium...")
        self.browser = self.playwright.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        self.page = self.browser.new_page()

    def search(self, occupation_code, city, county):

        page = self.page

        # --------------------------------------------------
        # Get State from City
        # --------------------------------------------------

        state_code = city.split(",")[-1].strip()

        state = STATE_MAP[state_code]

        print("=" * 60)
        print("Searching FLAG Website")
        print("=" * 60)
        print("Occupation :", occupation_code)
        print("State      :", state)
        print("County     :", county)
        print()

        # --------------------------------------------------
        # Fix known county names
        # --------------------------------------------------

        if county:

            county = COUNTY_FIXES.get(county, county)

        search_text = SPECIAL_AREAS.get(
            (state, county),
            county
        ).strip()

        # --------------------------------------------------
        # Open Website
        # --------------------------------------------------

        page.goto("https://flag.dol.gov/wage-data/wage-search")

        page.wait_for_load_state("networkidle")

        # --------------------------------------------------
        # Wage Year
        # --------------------------------------------------

        page.get_by_label(
            "dateSeries-select"
        ).select_option(WAGE_YEAR)

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

        page.wait_for_timeout(SHORT_WAIT)

        page.get_by_text(
            f"{occupation_code}.00"
        ).click()

        # --------------------------------------------------
        # State
        # --------------------------------------------------

        page.get_by_label(
            "state-select"
        ).select_option(state)

        page.wait_for_timeout(SHORT_WAIT)

        # --------------------------------------------------
        # County / Township
        # --------------------------------------------------

        page.get_by_text(
            "County/ Township"
        ).click()

        page.wait_for_timeout(LONG_WAIT)

        # --------------------------------------------------
        # Find Area Automatically
        # --------------------------------------------------

        options = page.locator("#areaSelect option")

        count = options.count()

        selected = False

        
        print("Searching Area :", search_text)

        for i in range(count):

            option = options.nth(i)

            text = option.inner_text().strip()

            if search_text.upper() in text.upper():

                print("Selected Area :", text)

                value = option.get_attribute("value")

                page.get_by_label(
                    "areaSelect-select"
                ).select_option(value=value)

                selected = True

                break

        if not selected:

            print("\nAvailable Areas:\n")

            for i in range(count):

                print("-", options.nth(i).inner_text())

            raise Exception(

                f"{county} not found for {state}"

            )

        page.wait_for_timeout(SHORT_WAIT)

        # --------------------------------------------------
        # Submit
        # --------------------------------------------------

        page.get_by_role(
            "button",
            name="Submit"
        ).click()

        page.wait_for_load_state("networkidle")

        page.wait_for_timeout(LONG_WAIT)

        # --------------------------------------------------
        # Read Level II Wage
        # --------------------------------------------------

        rows = page.locator("table tbody tr")

        row_count = rows.count()

        level2 = None

        for i in range(row_count):

            row = rows.nth(i)

            text = row.inner_text()

            if text.startswith("II"):

                cells = row.locator("td")

                level2 = cells.nth(2).inner_text().strip()

                break

        if level2 is None:

            raise Exception(

                "Level II wage not found."

            )

        level2 = (

            level2
            .replace("US$", "")
            .replace(",", "")
            .replace(".00", "")
            .strip()

        )

        print("Level II Wage :", level2)

        return level2

    def close(self):

        self.browser.close()

        self.playwright.stop()
