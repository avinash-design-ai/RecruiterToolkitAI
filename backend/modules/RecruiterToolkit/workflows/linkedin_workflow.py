class LinkedInWorkflow:

    def __init__(self, browser):

        self.page = browser.new_page()

        self.login = LinkedInLoginPage(self.page)

        self.home = LinkedInHomePage(self.page)

        self.profile = LinkedInProfilePage(self.page)

    def run(self):

        self.login.open(...)

        self.login.login(...)

        self.home.search(...)

        self.profile.open_contact_info()
