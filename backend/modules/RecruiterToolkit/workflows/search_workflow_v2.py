from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

from pages.company_page import CompanyPage
from pages.linkedin_profile_page_v2 import LinkedInProfilePageV2
from automation.exporter import Exporter
from automation.search_controller import should_stop


def normalize_company(value):
    value = str(value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def normalize_location(value):
    value = str(value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def canonical_profile_url(value):
    if not value:
        return ""
    value = str(value).strip()
    if value.startswith("/"):
        value = "https://www.linkedin.com" + value
    value = value.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    parsed = urlsplit(value)
    if parsed.netloc.lower() not in {"linkedin.com", "www.linkedin.com"}:
        return ""
    if not re.fullmatch(r"/in/[^/]+", parsed.path or "", flags=re.IGNORECASE):
        return ""
    return "https://www.linkedin.com" + parsed.path.lower()


class SearchWorkflowV2:

    def __init__(self, page):
        # One owner for the company/location employee search page.
        # Never create a reusable profile page here.
        self.page = page
        self.company_page = CompanyPage(self.page)

    def _restore_employee_search_page(self):
        """Restore page ownership without navigating any tab."""
        try:
            context = self.company_page.page.context
            pages = list(context.pages)
        except Exception as ex:
            print("SEARCH PAGE RESTORE FAILED:", repr(ex))
            return False

        valid = []
        for candidate in pages:
            try:
                if candidate.is_closed():
                    continue
                url = str(candidate.url or "").strip()
                lower = url.lower()
                if (
                    "/search/results/people/" in lower
                    and "currentcompany=" in lower
                    and not any(x in lower for x in ("/login", "/authwall", "/checkpoint", "/ssr-login", "remember-me-auto-login"))
                ):
                    valid.append(candidate)
            except Exception:
                continue

        if not valid:
            print("SEARCH PAGE RESTORE FAILED: no live company people-search page.")
            return False

        selected = None
        try:
            owned = self.company_page.page
            if owned in valid:
                selected = owned
        except Exception:
            pass

        if selected is None:
            for candidate in reversed(valid):
                try:
                    query = parse_qs(urlsplit(str(candidate.url or "")).query, keep_blank_values=True)
                    network = query.get("network", []) or query.get("Network", [])
                    if not network:
                        selected = candidate
                        break
                except Exception:
                    continue

        selected = selected or valid[-1]
        self.page = selected
        self.company_page.page = selected
        print("EMPLOYEE SEARCH PAGE RESTORED:", selected.url)
        return True

    def _validate_profile(self, data, company, location, row):
        requested_company = normalize_company(company)
        requested_location = normalize_location(location)

        actual_location_raw = str(data.get("location", "") or "").strip()
        actual_location = normalize_location(actual_location_raw)
        row_text = str(row.get("search_result_text", "") or "")
        row_location = normalize_location(row_text)

        if requested_location and requested_location not in actual_location:
            if not actual_location and requested_location in row_location:
                data["location"] = location
            else:
                print("REJECTED: profile location does not match requested location.")
                print("Profile location:", actual_location_raw)
                print("Requested location:", location)
                return False

        actual_company_raw = str(data.get("company", "") or "").strip()
        actual_company = normalize_company(actual_company_raw)

        selected_company_ids = []
        try:
            query = parse_qs(urlsplit(str(self.company_page.page.url or "")).query, keep_blank_values=True)
            selected_company_ids = query.get("currentCompany", []) or query.get("currentcompany", [])
            selected_company_ids = [x.strip('[]"') for x in selected_company_ids]
        except Exception:
            pass

        if actual_company:
            numeric_company_match = actual_company in {normalize_company(x) for x in selected_company_ids}
            named_company_match = bool(requested_company and requested_company in actual_company)
            if not (numeric_company_match or named_company_match):
                print("REJECTED: profile company does not match requested company.")
                print("Profile company:", actual_company_raw)
                print("Selected company ID(s):", selected_company_ids)
                print("Requested company:", company)
                return False
        else:
            # Empty company fields are acceptable only because the candidate came
            # from the authenticated currentCompany-scoped search page.
            if not selected_company_ids:
                print("REJECTED: profile company is blank and company scope is unavailable.")
                return False

        return True

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

        if not self.company_page.search_company(company):
            raise RuntimeError("Company search failed.")
        if not self.company_page.open_company_result(company):
            raise RuntimeError(f"Company '{company}' was not found.")
        if not self.company_page.open_employees_page():
            raise RuntimeError("Company-scoped employee search could not be opened.")
        if not self._restore_employee_search_page():
            raise RuntimeError("Authenticated company people-search page could not be established.")
        if not self.company_page.apply_location(location):
            raise RuntimeError("LinkedIn location filter was not successfully applied.")
        if not self._restore_employee_search_page():
            raise RuntimeError("Authenticated company people-search page was lost after location filtering.")

        while len(results) < max_profiles:
            if should_stop():
                print("STOP requested.")
                break

            print("=" * 60)
            print(f"Reading employee page {page_no}")
            print("=" * 60)

            if not self._restore_employee_search_page():
                break

            remaining = max_profiles - len(results)
            candidate_budget = min(100, max(20, remaining * 4))
            candidates = self.company_page.get_profiles(
                company,
                location,
                candidate_budget,
            )
            print("Candidates discovered on page:", len(candidates))

            for index, row in enumerate(candidates, start=1):
                if len(results) >= max_profiles or should_stop():
                    break

                requested_profile_url = canonical_profile_url(row.get("profile_url"))
                if not requested_profile_url:
                    print("Candidate skipped: invalid/non-person profile URL.")
                    continue
                if requested_profile_url in seen_urls:
                    print("Candidate skipped: duplicate profile URL.")
                    continue

                print("=" * 60)
                print(f"Processing candidate {index}/{len(candidates)}")
                print("Candidate profile URL:", requested_profile_url)
                print("=" * 60)

                profile = None
                try:
                    if not self._restore_employee_search_page():
                        continue
                    profile = LinkedInProfilePageV2(self.page)
                    if not profile.open_profile(requested_profile_url):
                        print("PROFILE PAGE COULD NOT BE OPENED.")
                        continue

                    data = profile.get_profile()
                    if not data:
                        continue

                    actual_url = canonical_profile_url(data.get("profile_url") or requested_profile_url)
                    if actual_url != requested_profile_url:
                        print("Candidate skipped: opened profile URL does not match requested URL.")
                        continue

                    data["profile_url"] = actual_url
                    if not self._validate_profile(data, company, location, row):
                        continue

                    data["search_company"] = company
                    data["search_location"] = location
                    if not data.get("location") and row.get("search_result_location"):
                        data["location"] = row["search_result_location"]

                    results.append(data)
                    seen_urls.add(actual_url)
                    print("VALID PROFILE COLLECTED")
                    print("Profiles collected so far:", len(results))

                    try:
                        autosave = Exporter.export_csv(results, f"{company}_{location}_v2_autosave.csv")
                        print("Autosave:", autosave)
                    except Exception as ex:
                        print("Autosave failed:", repr(ex))

                except Exception as ex:
                    print("Candidate processing failed:", repr(ex))
                finally:
                    # LinkedInProfilePageV2 cleanup normally closes the temporary
                    # tab; this guarantees that the search owner is restored even
                    # when extraction/validation throws.
                    try:
                        temporary = getattr(profile, "_temporary_profile_page", None) if profile else None
                        if temporary is not None and not temporary.is_closed():
                            temporary.close()
                    except Exception as ex:
                        print("PROFILE TAB CLEANUP WARNING:", repr(ex))
                    self._restore_employee_search_page()

            if len(results) >= max_profiles:
                break

            print("=" * 60)
            print("CURRENT EMPLOYEE PAGE EXHAUSTED")
            print("Profiles collected so far:", len(results))
            print("Trying next employee page...")
            print("=" * 60)

            if not self._restore_employee_search_page():
                break
            current_url = str(self.company_page.page.url or "").lower()
            if "/search/results/people/" not in current_url or "currentcompany=" not in current_url:
                print("SAFE STOP: page ownership invariant failed before pagination.")
                break

            if not self.company_page.next_page():
                print("No more employee pages.")
                break
            if not self._restore_employee_search_page():
                print("SAFE STOP: next page exists but ownership could not be restored.")
                break

            page_no += 1

        output_file = None
        if results:
            try:
                output_file = Exporter.export_csv(results, f"{company}_{location}_v2.csv")
                print("Final CSV:", output_file)
            except Exception as ex:
                print("Final export failed:", repr(ex))

        success = len(results) >= max_profiles
        print("=" * 70)
        print("V2 WORKFLOW FINISHED")
        print("=" * 70)
        print("Profiles collected:", len(results))
        print("Profiles required:", max_profiles)
        print("Success:", success)

        if not success:
            raise RuntimeError(
                f"LinkedIn V2 search incomplete: collected {len(results)} valid profiles, required {max_profiles}."
            )

        return {
            "results": results,
            "count": len(results),
            "required": max_profiles,
            "success": True,
            "csv": output_file,
        }
