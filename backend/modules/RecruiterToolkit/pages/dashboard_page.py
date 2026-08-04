from pages.base_page import BasePage


class DashboardPage(BasePage):

    PROFILE_NAME = [
        ".profile-name",
        ".user-name",
        "header .name"
    ]

    LOGOUT_BUTTON = [
        "text=Logout",
        "button:has-text('Logout')",
        "#logout"
    ]

    def get_username(self):
        return self.text(self.PROFILE_NAME)

    def logout(self):
        self.click(self.LOGOUT_BUTTON)
