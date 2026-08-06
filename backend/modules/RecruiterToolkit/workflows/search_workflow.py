from pages.company_page import CompanyPage
from automation.exporter import Exporter
from automation.search_controller import should_stop


class SearchWorkflow:

    def __init__(self, page):

        self.page = page

        self.company_page = CompanyPage(
            self.page
        )

    def run(
        self,
        company,
        location,
        max_profiles=250
    ):

        print("=" * 60)
        print("A - SearchWorkflow started")
        print("=" * 60)

        # -------------------------------------------------
        # Search Company
        # -------------------------------------------------

        print("B - Searching company...")

        self.company_page.search_company(
            company
        )

        print("C - Company search completed")

        # -------------------------------------------------
        # Open Company
        # -------------------------------------------------

        print("D - Opening company page...")

        found = (
            self.company_page
            .open_company_result(company)
        )

        print("Company Found:", found)

        if not found:

            print("Company not found.")

            return {

                "results": [],

                "count": 0,

                "csv": ""

            }

        # -------------------------------------------------
        # Open Employees
        # -------------------------------------------------

        print("E - Opening Employees page...")

        opened = (
            self.company_page
            .open_employees_page()
        )

        print("Employees Page:", opened)

        if not opened:

            print("Employees page not found.")

            return {

                "results": [],

                "count": 0,

                "csv": ""

            }

        # -------------------------------------------------
        # Apply Location
        # -------------------------------------------------

        print("F - Applying location...")

        self.company_page.apply_location(
            location
        )

        print("Location applied.")

        # -------------------------------------------------
        # Collect Profiles
        # -------------------------------------------------

        results = []

        seen_urls = set()

        page_no = 1

        while len(results) < max_profiles:

            if should_stop():

                print("STOP requested.")

                break

            print("=" * 50)
            print(f"Reading LinkedIn page {page_no}")
            print("=" * 50)

            page_results = (

                self.company_page

                .get_profiles()

            )

            print(
                "Profiles extracted:",
                len(page_results)
            )

            for row in page_results:

                if should_stop():

                    print("Stopping...")

                    break

                profile_url = row["profile_url"]

                if profile_url in seen_urls:

                    continue

                seen_urls.add(profile_url)

                results.append({

                    "company": company,

                    "search_location": location,

                    "full_name": row["full_name"],

                    "profile_url": profile_url

                })

                if len(results) >= max_profiles:

                    break

            print(

                f"Collected {len(results)} profiles"

            )

            try:

                Exporter.export_csv(

                    results,

                    f"{company}_{location}_autosave.csv"

                )

                print("Autosave completed.")

            except Exception as ex:

                print(

                    "Autosave failed:",

                    ex

                )

            if len(results) >= max_profiles:

                break

            has_next = (

                self.company_page

                .next_page()

            )

            print(

                "Next page:",

                has_next

            )

            if not has_next:

                print("No more pages.")

                break

            page_no += 1

        # -------------------------------------------------
        # Export Final CSV
        # -------------------------------------------------

        print("=" * 60)
        print("Exporting Final CSV")
        print("=" * 60)

        output_file = Exporter.export_csv(

            results,

            f"{company}_{location}.csv"

        )

        print("CSV Saved:", output_file)

        print("=" * 60)
        print("Workflow Finished")
        print("=" * 60)

        return {

            "results": results,

            "count": len(results),

            "csv": output_file

        }
