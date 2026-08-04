import os

print("Running:", os.path.abspath(__file__))
from automation.browser import BrowserManager
from workflows.login_workflow import LoginWorkflow
from workflows.search_workflow import SearchWorkflow


def main():

    browser = BrowserManager(profile="default")

    try:

        login = LoginWorkflow(browser)

        login.run(
            url="https://www.linkedin.com/login",
            username="YOUR_USERNAME",
            password="YOUR_PASSWORD"
        )

        workflow = SearchWorkflow(browser)

        results = workflow.run(
            company="TEKsystems",
            location="Dallas"
        )

        print(results)

    finally:

        input(
            "Press ENTER to close browser..."
        )

        browser.close()


if __name__ == "__main__":
    main()
