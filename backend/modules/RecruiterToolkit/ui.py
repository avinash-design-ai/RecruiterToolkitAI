import threading
import traceback

from tkinter import *
from tkinter import messagebox

from automation.browser import BrowserManager
from workflows.search_workflow import SearchWorkflow


class RecruiterUI:

    def __init__(self):

        self.root = Tk()

        self.root.title("Recruiter Toolkit")

        self.root.geometry("600x300")

        Label(
            self.root,
            text="Company"
        ).pack(pady=(10, 0))

        self.company_entry = Entry(
            self.root,
            width=50
        )

        self.company_entry.pack()

        Label(
            self.root,
            text="Location"
        ).pack(pady=(10, 0))

        self.location_entry = Entry(
            self.root,
            width=50
        )

        self.location_entry.pack()

        Label(
            self.root,
            text="Max Profiles"
        ).pack(pady=(10, 0))

        self.max_profiles_entry = Entry(
            self.root,
            width=20
        )

        self.max_profiles_entry.insert(
            0,
            "250"
        )

        self.max_profiles_entry.pack()

        self.status_var = StringVar()

        self.status_var.set("Ready")

        Label(
            self.root,
            textvariable=self.status_var
        ).pack(pady=20)

        Button(
            self.root,
            text="Run Search",
            command=self.start_search
        ).pack()

    def start_search(self):

        threading.Thread(
            target=self.run_search,
            daemon=True
        ).start()

    def run_search(self):

        browser = None

        try:

            company = (
                self.company_entry
                .get()
                .strip()
            )

            location = (
                self.location_entry
                .get()
                .strip()
            )

            max_profiles = int(
                self.max_profiles_entry
                .get()
                .strip()
            )

            self.status_var.set(
                "Launching browser..."
            )

            browser = BrowserManager(
                profile="default"
            )

            page = browser.new_page()

            page.goto(
                "https://www.linkedin.com/feed"
            )

            page.wait_for_timeout(3000)

            print("Current URL:")
            print(page.url)

            workflow = SearchWorkflow(
                browser
            )

            self.status_var.set(
                "Running workflow..."
            )

            results = workflow.run(
                company=company,
                location=location,
                max_profiles=max_profiles
            )

            self.status_var.set(
                f"Completed ({len(results)})"
            )

            messagebox.showinfo(
                "Done",
                f"Collected {len(results)} profiles"
            )

        except Exception as ex:

            traceback.print_exc()

            self.status_var.set(
                "Failed"
            )

            messagebox.showerror(
                "Error",
                str(ex)
            )

        finally:

            input(
                "Press ENTER to close browser..."
            )

            if browser:

                try:
                    browser.close()
                except:
                    pass

    def run(self):

        self.root.mainloop()


if __name__ == "__main__":

    RecruiterUI().run()
