from pages.base_page import BasePage


class ResultsPage(BasePage):

    JOBS = [
        ".job-card"
    ]

    NEXT = [
        ".next"
    ]

    def get_results(self):

        return self.smart.find(self.JOBS).all()

    def next_page(self):

        self.click(self.NEXT)
