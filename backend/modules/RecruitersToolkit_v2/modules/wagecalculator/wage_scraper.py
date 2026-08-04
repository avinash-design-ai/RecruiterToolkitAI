import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://flag.dol.gov/wage-data/wage-search")
    page.get_by_label("dateSeries-select").select_option("7/2026 - 6/2027")
    page.get_by_text("All Industries").click()
    page.get_by_role("textbox", name="Type search term here").click()
    page.get_by_role("textbox", name="Type search term here").fill("15-1252")
    page.get_by_text("15-1252.00 —— Software").click()
    page.get_by_label("state-select").select_option("TEXAS")
    page.get_by_text("County/ Township").click()
    page.get_by_label("areaSelect-select").select_option("DALLAS COUNTY - Dallas-Fort Worth-Arlington, TX")
    page.get_by_role("button", name="Submit").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
