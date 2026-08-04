from pages.company_page import CompanyPage
from automation.exporter import Exporter
from automation.search_controller import should_stop

class SearchWorkflow:

    def __init__(self, browser):

        self.browser = browser

        self.page = browser.new_page()

        self.company_page = CompanyPage(
            self.page
        )

    def run(
        self,
        company,
        location,
        max_profiles=250
    ):

        self.company_page.search_company(
            company
        )

        found = (
            self.company_page
            .open_company_result(company)
        )

        if not found:
            return []

        opened = (
            self.company_page
            .open_employees_page()
        )

        if not opened:
            return []

        self.company_page.apply_location(
            location
        )

        results = []

        seen_urls = set()

        page_no = 1

        while len(results) < max_profiles:

            # -------------------------------
            # Stop requested?
            # -------------------------------

            if should_stop():

                print("====================================")
                print("STOP requested by user.")
                print("Saving current results...")
                print("====================================")

                break

            print(
                f"Reading page {page_no}"
            )

            page_results = (
                self.company_page
                .get_profiles()
            )

            for row in page_results:

                if should_stop():

                    print("Stopping before next profile...")

                    break

                profile_url = row[
                    "profile_url"
                ]

                if (
                    profile_url
                    in seen_urls
                ):
                    continue

                seen_urls.add(
                    profile_url
                )

                results.append(
                    {
                        "company": company,
                        "search_location":
                            location,
                        "full_name":
                            row["full_name"],
                        "profile_url":
                            profile_url
                    }
                )

                if (
                    len(results)
                    >= max_profiles
                ):
                    break

            print(
                f"Current results: "
                f"{len(results)} / "
                f"{max_profiles}"
            )

            try:

                Exporter.export_csv(
                    results,
                    f"{company}_{location}_autosave.csv"
                )

            except Exception as ex:

                print(
                    "Autosave skipped:",
                    ex
                )

            if (
                len(results)
                >= max_profiles
            ):
                break

            has_next = (
                self.company_page
                .next_page()
            )

            print(
                f"Next page available: "
                f"{has_next}"
            )

            if not has_next:
                break

            page_no += 1

        output_file = Exporter.export_csv(
            results,
            f"{company}_{location}.csv"
        )

        print(f"CSV Saved: {output_file}")

        return {
            "results": results,
            "count": len(results),
            "csv": output_file
        }
