from automation.browser import BrowserManager
from pages.linkedin_profile_page_v2 import LinkedInProfilePageV2


PROFILE_URL = "https://www.linkedin.com/in/pavan-kumar-katta-/"


browser = BrowserManager()

try:

    page = browser.new_page()

    profile = LinkedInProfilePageV2(page)

    if profile.open_profile(PROFILE_URL):

        data = profile.get_profile()

        print("=" * 60)
        print("FINAL PROFILE DATA")
        print("=" * 60)

        for key, value in data.items():

            print(
                f"{key}: {value}"
            )

finally:

    browser.close()