from pages.company_page import CompanyPage
from pages.linkedin_profile_page_v2 import LinkedInProfilePageV2

from automation.exporter import Exporter
from automation.search_controller import should_stop


def normalize_company(value):
    import re
    value = str(value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def normalize_location(value):
    import re
    value = str(value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def canonical_profile_url(value):
    import re
    value = str(value or "").strip()
    if not value:
        return ""
    if value.startswith("/"):
        value = "https://www.linkedin.com" + value
    value = value.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    return re.sub(
        r"^https?://(?:www\.)?linkedin\.com",
        "https://www.linkedin.com",
        value,
        flags=re.IGNORECASE,
    )


class SearchWorkflowV2:

    def __init__(self, page):
        self.page = page
        self.company_page = CompanyPage(self.page)
        # Keep the proven desktop architecture: one dedicated profile page.
        self.profile_page = self.page.context.new_page()

    def _validate_profile(self, data, company, location, row=None):
        requested_company = normalize_company(company)
        requested_location = normalize_location(location)
        row = row or {}

        profile_location = str(data.get("location", "") or "").strip()
        row_location = str(row.get("search_result_location", "") or "").strip()
        actual_location = normalize_location(profile_location)
        search_location = normalize_location(row_location)
        if requested_location and requested_location not in actual_location:
            if not actual_location and requested_location in search_location:
                # The employee came from the authenticated LinkedIn search with
                # the requested geoUrn. Use that filter as location evidence
                # only when LinkedIn exposes no profile location at all.
                data["location"] = row_location or location
            else:
                print("REJECTED: profile location does not match requested location.")
                print("Profile location:", profile_location)
                print("Search-result location:", row_location)
                print("Requested location:", location)
                return False

        actual_company_raw = str(data.get("company", "") or "").strip()
        actual_company = normalize_company(actual_company_raw)
        selected_company_ids = []
        try:
            from urllib.parse import parse_qsl, urlsplit
            for key, value in parse_qsl(urlsplit(str(self.company_page.page.url or "")).query, keep_blank_values=True):
                if key.lower() == "currentcompany":
                    selected_company_ids.append(value.strip('[]"'))
        except Exception:
            pass

        if actual_company:
            if actual_company in {normalize_company(str(x)) for x in selected_company_ids}:
                return True
            if requested_company in actual_company:
                return True
            print("REJECTED: profile company does not match requested company.")
            print("Profile company:", actual_company_raw)
            print("Selected company ID(s):", selected_company_ids)
            print("Requested company:", company)
            return False

        return True

    def _process_link_candidate(self, row):
        profile_url = canonical_profile_url(row.get("profile_url"))
        if not profile_url:
            return None

        profile = LinkedInProfilePageV2(self.profile_page)
        if not profile.open_profile(profile_url):
            return None

        try:
            return profile.get_profile()
        finally:
            temp = getattr(profile, "_temporary_profile_page", None)
            if temp is not None:
                try:
                    if not temp.is_closed():
                        temp.close()
                except Exception:
                    pass
                profile._temporary_profile_page = None

    def _process_control_candidate(self, control_index):
        temp_page, actual_url = self.company_page.open_result_profile(control_index)
        if temp_page is None or not actual_url:
            return None

        profile = LinkedInProfilePageV2(temp_page)
        profile.profile_url = actual_url

        try:
            return profile.get_profile()
        finally:
            try:
                if not temp_page.is_closed():
                    temp_page.close()
            except Exception:
                pass

    def run(self, company, location, max_profiles=1):
        max_profiles = int(max_profiles)
        if max_profiles < 1:
            raise ValueError("max_profiles must be at least 1.")

        print("=" * 70)
        print("LINKEDIN SEARCH WORKFLOW V2")
        print("=" * 70)
        print("Company:", company)
        print("Location:", location)
        print("Maximum profiles:", max_profiles)

        results = []
        seen_urls = set()
        page_no = 1

        print("=" * 60)
        print("A - Searching company")
        print("=" * 60)
        if not self.company_page.search_company(company):
            raise RuntimeError("Company search failed.")

        print("=" * 60)
        print("B - Opening company")
        print("=" * 60)
        if not self.company_page.open_company_result(company):
            raise RuntimeError(f"Company '{company}' was not found.")

        print("=" * 60)
        print("C - Opening employees")
        print("=" * 60)
        if not self.company_page.open_employees_page():
            raise RuntimeError("Company-scoped employee search could not be opened.")

        print("=" * 60)
        print("D - Applying location")
        print("=" * 60)
        if not self.company_page.apply_location(location):
            raise RuntimeError("LinkedIn location filter was not successfully applied.")

        print("=" * 60)
        print("E - Collecting valid profiles")
        print("=" * 60)

        empty_page_streak = 0

        while len(results) < max_profiles:
            if should_stop():
                print("STOP requested.")
                break

            print("=" * 60)
            print(f"Reading employee page {page_no}")
            print("=" * 60)

            remaining = max_profiles - len(results)
            candidates = self.company_page.get_profiles(
                company,
                location,
                remaining,
            )

            print("Candidates discovered on page:", len(candidates))

            accepted_this_page = 0

            for index, row in enumerate(candidates, start=1):
                if len(results) >= max_profiles or should_stop():
                    break

                control_index = row.get("control_index")
                candidate_url = canonical_profile_url(row.get("profile_url"))

                print("=" * 60)
                print(f"Processing candidate {index}/{len(candidates)}")
                print("=" * 60)

                try:
                    if control_index is not None:
                        data = self._process_control_candidate(int(control_index))
                    else:
                        data = self._process_link_candidate(row)

                    if not data:
                        print("Candidate skipped: profile could not be opened.")
                        continue

                    actual_url = canonical_profile_url(
                        data.get("profile_url") or candidate_url
                    )
                    if not actual_url or "/in/" not in actual_url:
                        print("Candidate skipped: no real LinkedIn /in/ profile URL.")
                        continue

                    data["profile_url"] = actual_url

                    if actual_url in seen_urls:
                        print("Candidate skipped: duplicate profile URL.")
                        continue

                    if not self._validate_profile(data, company, location, row=row):
                        continue

                    data["search_company"] = company
                    data["search_location"] = location
                    if not data.get("location") and row.get("search_result_location"):
                        data["location"] = row.get("search_result_location")
                    results.append(data)
                    seen_urls.add(actual_url)
                    accepted_this_page += 1

                    print("VALID PROFILE COLLECTED")
                    print("Profiles collected so far:", len(results))

                    try:
                        autosave = Exporter.export_csv(
                            results,
                            f"{company}_{location}_v2_autosave.csv",
                        )
                        print("Autosave:", autosave)
                    except Exception as exc:
                        print("Autosave failed:", repr(exc))

                except Exception as exc:
                    print("Candidate processing failed:", repr(exc))
                    continue

            if len(results) >= max_profiles:
                break

            empty_page_streak = 0 if accepted_this_page else empty_page_streak + 1

            print(
                "Accepted on page:",
                accepted_this_page,
                "| Total:",
                len(results),
                "/",
                max_profiles,
            )

            if not self.company_page.next_page():
                print("No more employee pages.")
                break

            page_no += 1

        # Export partial data too, but never label an incomplete run as success.
        output_file = None
        if results:
            try:
                output_file = Exporter.export_csv(
                    results,
                    f"{company}_{location}_v2.csv",
                )
                print("Final CSV:", output_file)
            except Exception as exc:
                print("Final export failed:", repr(exc))

        success = len(results) >= max_profiles
        print("=" * 70)
        print("V2 WORKFLOW FINISHED")
        print("=" * 70)
        print("Profiles collected:", len(results))
        print("Profiles required:", max_profiles)
        print("Success:", success)

        if not success:
            raise RuntimeError(
                f"LinkedIn V2 search incomplete: collected {len(results)} "
                f"valid profiles, required {max_profiles}."
            )

        return {
            "results": results,
            "count": len(results),
            "required": max_profiles,
            "success": True,
            "csv": output_file,
        }
