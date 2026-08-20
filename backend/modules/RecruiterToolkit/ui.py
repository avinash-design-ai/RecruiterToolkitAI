import threading
import traceback

from tkinter import *
from tkinter import messagebox, filedialog

import csv
from pathlib import Path

from automation.browser import BrowserManager
from workflows.search_workflow_v2 import SearchWorkflowV2


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

    def save_results_as(self, results, suggested_filename):

        if not results:
            messagebox.showwarning(
                "No Results",
                "No profiles were collected."
            )
            return

        file_path = filedialog.asksaveasfilename(
            title="Save LinkedIn Search Results",
            defaultextension=".csv",
            initialfile=suggested_filename,
            filetypes=[
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )

        if not file_path:
            self.status_var.set(
                "Completed - CSV not saved"
            )
            return

        try:

            fieldnames = []

            for row in results:

                for key in row.keys():

                    if key not in fieldnames:

                        fieldnames.append(key)

            with open(
                file_path,
                "w",
                newline="",
                encoding="utf-8-sig"
            ) as csv_file:

                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=fieldnames,
                    extrasaction="ignore"
                )

                writer.writeheader()

                writer.writerows(
                    results
                )

            self.status_var.set(
                f"Saved CSV: {Path(file_path).name}"
            )

            print(
                "User CSV saved:",
                file_path
            )

            messagebox.showinfo(
                "CSV Saved",
                f"CSV saved successfully:\n\n{file_path}"
            )

        except Exception as ex:

            traceback.print_exc()

            messagebox.showerror(
                "Save Error",
                f"Unable to save CSV:\n\n{ex}"
            )

    def wait_for_linkedin_login(self, page):

        print("=" * 60)
        print("CHECKING LINKEDIN LOGIN STATUS")
        print("=" * 60)

        current_url = page.url

        print(
            "Initial LinkedIn URL:",
            current_url
        )

        if "/feed" in current_url:

            print(
                "Existing LinkedIn session detected."
            )

            return True

        print(
            "LinkedIn login/verification required."
        )

        self.status_var.set(
            "Please complete LinkedIn login/verification..."
        )

        messagebox.showinfo(
            "LinkedIn Login Required",
            "LinkedIn requires you to log in or complete "
            "verification.\n\n"
            "Complete the process in the browser window. "
            "The search will continue automatically after "
            "LinkedIn returns to the feed."
        )

        for _ in range(180):

            try:

                current_url = page.url

                print(
                    "Waiting for LinkedIn:",
                    current_url
                )

                if "/feed" in current_url:

                    page.wait_for_timeout(
                        3000
                    )

                    print(
                        "LinkedIn authentication completed."
                    )

                    self.status_var.set(
                        "LinkedIn login successful. Starting search..."
                    )

                    return True

            except Exception as ex:

                print(
                    "Login status check failed:",
                    repr(ex)
                )

            page.wait_for_timeout(
                1000
            )

        self.status_var.set(
            "LinkedIn login timed out"
        )

        messagebox.showerror(
            "LinkedIn Login Timeout",
            "LinkedIn login or verification was not completed "
            "within the allowed time."
        )

        return False

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
                "https://www.linkedin.com/feed",
                wait_until="domcontentloaded"
            )

            page.wait_for_timeout(
                3000
            )

            print("Current URL:")
            print(page.url)

            if not self.wait_for_linkedin_login(
                page
            ):

                return

            workflow = SearchWorkflowV2(
                page
            )

            self.status_var.set(
                "Running workflow..."
            )

            result_data = workflow.run(
                company=company,
                location=location,
                max_profiles=max_profiles
            )

            results = result_data.get(
                "results",
                []
            )

            self.status_var.set(
                f"Completed ({len(results)})"
            )

            if results:

                safe_company = (
                    company
                    .replace("/", "_")
                    .replace("\\", "_")
                    .replace(":", "_")
                )

                safe_location = (
                    location
                    .replace("/", "_")
                    .replace("\\", "_")
                    .replace(":", "_")
                )

                suggested_filename = (
                    f"{safe_company}_{safe_location}_v2.csv"
                )

                self.root.after(
                    0,
                    lambda: self.save_results_as(
                        results,
                        suggested_filename
                    )
                )

            else:

                self.root.after(
                    0,
                    lambda: messagebox.showwarning(
                        "No Profiles",
                        "The search completed but no profiles "
                        "were collected."
                    )
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
