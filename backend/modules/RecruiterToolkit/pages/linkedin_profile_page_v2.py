import re

from pages.base_page import BasePage


class LinkedInProfilePageV2(BasePage):

    def __init__(self, page):

        super().__init__(page)

        self.profile_url = ""

    # =====================================================
    # OPEN PROFILE
    # =====================================================

    def open_profile(self, profile_url):
        print("=" * 60)
        print("Opening LinkedIn profile")
        print(profile_url)
        print("=" * 60)

        try:
            self.profile_url = profile_url

            print("=" * 70)
            print("PROFILE NAVIGATION DIAGNOSTICS")
            print("=" * 70)
            print("Profile target:", profile_url)
            print("Current page URL:", self.page.url)
            print("Page count in context:", len(self.page.context.pages))

            for index, context_page in enumerate(
                self.page.context.pages
            ):
                print(
                    f"Page {index}: {context_page.url}"
                )

            print("=" * 70)

            # -------------------------------------------------
            # IMPORTANT:
            #
            # The profile page is already a separate page created
            # by SearchWorkflowV2 inside the SAME authenticated
            # browser context.
            #
            # First try normal navigation.
            #
            # If LinkedIn sends this page to /authwall, retry
            # through the authenticated context using a temporary
            # page and preserve the existing profile page.
            # -------------------------------------------------

            print("PROFILE NAVIGATION START")
            print("Target profile URL:", profile_url)
            print(
                "Profile page before goto:",
                self.page.url
            )
            print(
                "Context page count:",
                len(self.page.context.pages)
            )

            # -------------------------------------------------
            # Normalize profile URL
            # -------------------------------------------------

            if profile_url:
                profile_url = profile_url.strip()

            if not profile_url:
                print(
                    "Profile URL is empty."
                )
                return False

            if profile_url.startswith("/"):
                profile_url = (
                    "https://www.linkedin.com"
                    + profile_url
                )

            # -------------------------------------------------
            # FIRST ATTEMPT
            # -------------------------------------------------

            try:
                self.page.goto(
                    profile_url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                print(
                    "Profile page after goto:",
                    self.page.url
                )

                try:
                    print(
                        "Profile page title:",
                        self.page.title()
                    )
                except Exception:
                    pass

                self.page.wait_for_timeout(4000)

            except Exception as goto_ex:
                print(
                    "Direct profile navigation failed:",
                    repr(goto_ex)
                )

            current_url = self.page.url

            print(
                "Profile loaded:",
                current_url
            )

            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            if (
                "/in/" in current_url.lower()
                and "/authwall" not in current_url.lower()
                and "/login" not in current_url.lower()
            ):
                print(
                    "Valid LinkedIn profile page detected."
                )
                return True

            # -------------------------------------------------
            # AUTHWALL / LOGIN RECOVERY
            # -------------------------------------------------

            if (
                "/authwall" in current_url.lower()
                or "/login" in current_url.lower()
                or "/ssr-login/" in current_url.lower()
                or "remember-me-auto-login" in current_url.lower()
            ):

                print("=" * 60)
                print(
                    "PROFILE NAVIGATION REDIRECTED"
                )
                print("=" * 60)
                print(
                    "Blocked profile URL:",
                    current_url
                )

                print(
                    "Attempting authenticated-context "
                    "profile recovery..."
                )

                recovery_page = None

                try:
                    # -------------------------------------------------
                    # Create a temporary page in the SAME authenticated
                    # browser context.
                    # -------------------------------------------------

                    recovery_page = (
                        self.page.context.new_page()
                    )

                    print(
                        "Recovery page created."
                    )

                    print(
                        "Recovery page URL:",
                        recovery_page.url
                    )

                    recovery_page.goto(
                        profile_url,
                        wait_until="domcontentloaded",
                        timeout=60000
                    )

                    print(
                        "Recovery page after goto:",
                        recovery_page.url
                    )

                    recovery_page.wait_for_timeout(
                        5000
                    )

                    recovery_url = (
                        recovery_page.url
                    )

                    print(
                        "Recovery profile URL:",
                        recovery_url
                    )

                    # -------------------------------------------------
                    # Check whether recovery succeeded.
                    # -------------------------------------------------

                    if (
                        "/in/" in recovery_url.lower()
                        and "/authwall" not in recovery_url.lower()
                        and "/login" not in recovery_url.lower()
                    ):

                        print("=" * 60)
                        print(
                            "PROFILE RECOVERY SUCCESSFUL"
                        )
                        print("=" * 60)

                        # -------------------------------------------------
                        # We cannot replace the Playwright Page object
                        # stored in BasePage safely.
                        #
                        # Therefore copy the recovered page state into
                        # the existing profile page by navigating the
                        # existing page to the recovered final URL.
                        #
                        # This is intentionally done only after LinkedIn
                        # has successfully resolved the profile URL.
                        # -------------------------------------------------

                        resolved_url = (
                            recovery_url
                        )

                        try:
                            self.page.goto(
                                resolved_url,
                                wait_until="domcontentloaded",
                                timeout=60000
                            )

                            self.page.wait_for_timeout(
                                4000
                            )

                            final_url = self.page.url

                            print(
                                "Final profile page:",
                                final_url
                            )

                            if (
                                "/in/" in final_url.lower()
                                and "/authwall" not in final_url.lower()
                                and "/login" not in final_url.lower()
                            ):
                                print(
                                    "Valid LinkedIn profile page "
                                    "detected after recovery."
                                )
                                return True

                        except Exception as final_ex:
                            print(
                                "Final profile navigation failed:",
                                repr(final_ex)
                            )

                    else:
                        print(
                            "Recovery page was also blocked:"
                        )
                        print(
                            recovery_url
                        )

                except Exception as recovery_ex:
                    print(
                        "Authenticated profile recovery failed:",
                        repr(recovery_ex)
                    )

                finally:
                    # -------------------------------------------------
                    # Always close the temporary recovery page.
                    # -------------------------------------------------

                    if recovery_page:
                        try:
                            recovery_page.close()

                            print(
                                "Recovery page closed."
                            )

                        except Exception as close_ex:
                            print(
                                "Recovery page close failed:",
                                repr(close_ex)
                            )

                # -------------------------------------------------
                # Final cleanup.
                #
                # Do NOT touch the employee search page.
                # -------------------------------------------------

                try:
                    print(
                        "Resetting dedicated profile page..."
                    )

                    self.page.goto(
                        "about:blank",
                        wait_until="domcontentloaded",
                        timeout=30000
                    )

                    print(
                        "Profile page reset:",
                        self.page.url
                    )

                except Exception as reset_ex:
                    print(
                        "Profile page reset failed:",
                        repr(reset_ex)
                    )

                return False

            # -------------------------------------------------
            # Unexpected LinkedIn page
            # -------------------------------------------------

            print(
                "Not a LinkedIn profile page."
            )

            print(
                "Unexpected URL:",
                current_url
            )

            return False

        except Exception as ex:
            print(
                "Failed to open profile:",
                repr(ex)
            )

            return False

    # =====================================================
    # PROFILE DATA
    # =====================================================

    def get_profile(self):

        print("=" * 60)
        print(
            "Extracting publicly visible profile information"
        )
        print("=" * 60)

        result = {

            "full_name": "",

            "headline": "",

            "location": "",

            "company": "",

            "email": "",

            "email_source": "",

            "profile_url": self.profile_url,

        }

        try:

            # ---------------------------------------------
            # Capture rendered profile text
            # ---------------------------------------------

            body_text = self.page.locator(
                "body"
            ).inner_text()

            print(
                "Profile page text captured:",
                len(body_text),
                "characters"
            )

            # ---------------------------------------------
            # Name
            # ---------------------------------------------

            result["full_name"] = (
                self.extract_name()
            )

            # ---------------------------------------------
            # Headline
            # ---------------------------------------------

            result["headline"] = (
                self.extract_headline()
            )

            # ---------------------------------------------
            # Location
            # ---------------------------------------------

            result["location"] = (
                self.extract_location()
            )

            # ---------------------------------------------
            # Company
            # ---------------------------------------------

            result["company"] = (
                self.extract_company()
            )

            # ---------------------------------------------
            # Email
            #
            # Only search publicly visible content.
            # Do NOT open Contact Info.
            # ---------------------------------------------

            email_data = (
                self.extract_email_from_visible_content()
            )

            result["email"] = (
                email_data["email"]
            )

            result["linked_email_id"] = (
                email_data["linked_email_id"]
            )

            result["email_source"] = (
                email_data["email_source"]
            )

        except Exception as ex:

            print(
                "Profile extraction failed:",
                repr(ex)
            )

        print(
            "PROFILE:",
            result
        )

        return result

    # =====================================================
    # NAME
    # =====================================================

    def extract_name(self):

        try:

            # Current LinkedIn profile header renders
            # the person's name as an h2.

            locator = self.page.locator(
                "main h2"
            ).first

            if locator.count():

                value = locator.inner_text().strip()

                if value:

                    print(
                        "Name:",
                        value
                    )

                    return value

        except Exception as ex:

            print(
                "Name extraction failed:",
                repr(ex)
            )

        return ""

    # =====================================================
    # HEADLINE
    # =====================================================

    def extract_headline(self):

        try:

            paragraphs = self.page.locator(
                "main p"
            )

            count = paragraphs.count()

            # The current LinkedIn profile header normally has:
            #
            # h2 = name
            # p  = pronoun
            # p  = headline
            # p  = company / education
            # p  = location

            for i in range(count):

                try:

                    value = (
                        paragraphs
                        .nth(i)
                        .inner_text()
                        .strip()
                    )

                    if not value:

                        continue

                    # Skip pronouns.

                    if value in {
                        "He/Him",
                        "She/Her",
                        "They/Them"
                    }:

                        continue

                    lower = value.lower()

                    # Skip obvious non-headline content.

                    if (
                        "followers" in lower
                        or lower == "contact info"
                    ):

                        continue

                    # A headline is normally a reasonably
                    # short descriptive sentence.

                    if (
                        len(value) >= 10
                        and len(value) <= 250
                    ):

                        print(
                            "Headline:",
                            value
                        )

                        return value

                except Exception:

                    continue

        except Exception as ex:

            print(
                "Headline extraction failed:",
                repr(ex)
            )

        return ""

    # =====================================================
    # LOCATION
    # =====================================================

    def extract_location(self):

        try:

            paragraphs = self.page.locator(
                "main p"
            )

            count = paragraphs.count()

            for i in range(count):

                try:

                    value = (
                        paragraphs
                        .nth(i)
                        .inner_text()
                        .strip()
                    )

                    if not value:

                        continue

                    # Skip pronouns.

                    if value in {
                        "He/Him",
                        "She/Her",
                        "They/Them"
                    }:

                        continue

                    lower = value.lower()

                    # Skip obvious non-location content.

                    if (
                        "followers" in lower
                        or "contact info" in lower
                    ):

                        continue

                    # Current LinkedIn profile location is
                    # typically geographic text such as:
                    #
                    # Edison, New Jersey, United States

                    if (
                        "," in value
                        and len(value) <= 150
                    ):

                        # Avoid treating arbitrary long
                        # comma-separated content as location.

                        geographic_words = (
                            "united states",
                            "usa",
                            "canada",
                            "india",
                            "united kingdom",
                            "uk",
                            "australia",
                            "new jersey",
                            "california",
                            "texas",
                            "new york",
                            "florida"
                        )

                        if any(
                            word in lower
                            for word in geographic_words
                        ):

                            print(
                                "Location:",
                                value
                            )

                            return value

                except Exception:

                    continue

        except Exception as ex:

            print(
                "Location extraction failed:",
                repr(ex)
            )

        return ""

    # =====================================================
    # COMPANY
    # =====================================================

    def extract_company(self):

        try:

            # ---------------------------------------------
            # First try the profile header structure.
            # ---------------------------------------------

            paragraphs = self.page.locator(
                "main p"
            )

            count = paragraphs.count()

            for i in range(count):

                try:

                    value = (
                        paragraphs
                        .nth(i)
                        .inner_text()
                        .strip()
                    )

                    if not value:

                        continue

                    lower = value.lower()

                    # Skip pronouns.

                    if value in {
                        "He/Him",
                        "She/Her",
                        "They/Them"
                    }:

                        continue

                    # Skip location.

                    if "," in value:

                        continue

                    # Skip obvious unrelated content.

                    if (
                        "followers" in lower
                        or "contact info" in lower
                    ):

                        continue

                    # Current profile format commonly has
                    # company information such as:
                    #
                    # SmartWorks, LLC · Aurora's Scientific
                    # Technological and Research Academy

                    if " · " in value:

                        parts = [
                            part.strip()
                            for part in value.split("·")
                            if part.strip()
                        ]

                        if parts:

                            company = parts[0]

                            if (
                                len(company) <= 150
                                and len(company) >= 2
                            ):

                                print(
                                    "Company:",
                                    company
                                )

                                return company

                except Exception:

                    continue

            # ---------------------------------------------
            # Fallback:
            #
            # Search spans in the main profile header.
            # ---------------------------------------------

            spans = self.page.locator(
                "main span"
            )

            span_count = spans.count()

            for i in range(span_count):

                try:

                    value = (
                        spans
                        .nth(i)
                        .inner_text()
                        .strip()
                    )

                    if not value:

                        continue

                    if len(value) > 150:

                        continue

                    lower = value.lower()

                    if (
                        "followers" in lower
                        or "contact info" in lower
                    ):

                        continue

                    # Skip generic UI text.

                    if value in {
                        "Contact info",
                        "Follow",
                        "Message",
                        "More"
                    }:

                        continue

                    # Company names often contain corporate
                    # identifiers, but don't require them.

                    if any(
                        token in lower
                        for token in (
                            "llc",
                            "inc",
                            "corp",
                            "ltd",
                            "company",
                            "technologies",
                            "technology",
                            "solutions",
                            "systems"
                        )
                    ):

                        print(
                            "Company:",
                            value
                        )

                        return value

                except Exception:

                    continue

        except Exception as ex:

            print(
                "Company extraction failed:",
                repr(ex)
            )

        return ""

    # =====================================================
    # EMAIL
    # =====================================================

    def extract_email_from_visible_content(self):

        print(
            "Searching publicly visible profile content "
            "for email..."
        )

        result = {
            "email": "",
            "linked_email_id": "",
            "email_source": "",
        }

        try:

            # -------------------------------------------------
            # Collect ALL publicly visible email addresses.
            # Do not stop after the first match.
            # -------------------------------------------------

            discovered_emails = []

            # -------------------------------------------------
            # 1. Visible mailto links
            # -------------------------------------------------

            email_links = self.page.locator(
                "a[href^='mailto:']"
            )

            count = email_links.count()

            print(
                "Visible mailto links:",
                count
            )

            for i in range(count):

                try:

                    link = email_links.nth(i)

                    if not link.is_visible():
                        continue

                    href = (
                        link.get_attribute("href")
                    )

                    if not href:
                        continue

                    email = (
                        href
                        .replace("mailto:", "")
                        .split("?")[0]
                        .strip()
                    )

                    if self.is_valid_email(email):

                        discovered_emails.append(
                            email
                        )

                except Exception:

                    continue

            # -------------------------------------------------
            # 2. Scan visible rendered profile content
            #
            # This includes publicly rendered:
            # About / Featured / Experience / Posts /
            # comments / other visible profile content.
            # -------------------------------------------------

            body_text = self.page.locator(
                "body"
            ).inner_text()

            matches = re.findall(
                r"\b[A-Za-z0-9._%+-]+"
                r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
                body_text
            )

            discovered_emails.extend(
                matches
            )

            # -------------------------------------------------
            # Remove duplicates while preserving order
            # -------------------------------------------------

            unique_emails = []

            seen = set()

            for email in discovered_emails:

                email = email.strip()

                if not self.is_valid_email(email):
                    continue

                normalized = email.lower()

                if normalized in seen:
                    continue

                seen.add(normalized)

                unique_emails.append(email)

            print(
                "Unique publicly visible emails:",
                len(unique_emails)
            )

            for email in unique_emails:

                print(
                    "  Email discovered:",
                    email
                )

            if not unique_emails:

                print(
                    "No publicly visible email found."
                )

                return result

            # -------------------------------------------------
            # Determine profile owner's name
            # -------------------------------------------------

            profile_name = ""

            try:

                profile_name = (
                    self.extract_name()
                    .strip()
                )

            except Exception:

                profile_name = ""

            # -------------------------------------------------
            # Build name components
            # -------------------------------------------------

            name_parts = []

            if profile_name:

                cleaned_name = re.sub(
                    r"[^a-zA-Z0-9 ]",
                    " ",
                    profile_name
                )

                name_parts = [
                    part.lower()
                    for part in cleaned_name.split()
                    if len(part) >= 2
                ]

            first_name = (
                name_parts[0]
                if name_parts
                else ""
            )

            last_name = (
                name_parts[-1]
                if len(name_parts) >= 2
                else ""
            )

            # -------------------------------------------------
            # Classify emails
            #
            # IMPORTANT:
            #
            # We do NOT assume every email found on the page
            # belongs to the profile owner.
            #
            # Strong owner-name matches go into:
            #
            #     email
            #
            # Other publicly visible emails go into:
            #
            #     linked_email_id
            # -------------------------------------------------

            owner_email = ""

            linked_emails = []

            for email in unique_emails:

                local_part = (
                    email
                    .split("@", 1)[0]
                    .lower()
                )

                local_clean = re.sub(
                    r"[^a-z0-9]",
                    "",
                    local_part
                )

                first_clean = re.sub(
                    r"[^a-z0-9]",
                    "",
                    first_name
                )

                last_clean = re.sub(
                    r"[^a-z0-9]",
                    "",
                    last_name
                )

                owner_match = False

                # -------------------------------------------------
                # Strong first-name match
                #
                # Examples:
                #
                # vamshi.k
                # vamshikrishna
                # vamshi.kota
                # vamshikota
                # -------------------------------------------------

                if first_clean:

    # Full first name
                    if local_clean.startswith(
                        first_clean
                    ):

                        owner_match = True

                    # Common shortened first-name form.
                    #
                    # Example:
                    # Avinash -> avi
                    #
                    # Require at least 3 characters to
                    # avoid overly broad matches.

                    elif (
                        len(first_clean) >= 5
                        and len(local_clean) >= 3
                        and first_clean.startswith(
                            local_clean[:3]
                        )
                    ):

                        owner_match = True
                # -------------------------------------------------
                # Assign
                # -------------------------------------------------

                if owner_match and not owner_email:

                    owner_email = email

                else:

                    linked_emails.append(
                        email
                    )

            # -------------------------------------------------
            # IMPORTANT:
            #
            # If there is only one email and it doesn't have a
            # confident owner match, it goes into
            # linked_email_id rather than falsely becoming
            # the person's email.
            # -------------------------------------------------

            if owner_email:

                result["email"] = (
                    owner_email
                )

                result["email_source"] = (
                    "profile"
                )

            if linked_emails:

                result["linked_email_id"] = (
                    "; ".join(
                        linked_emails
                    )
                )

            print(
                "Primary email:",
                result["email"]
            )

            print(
                "Linked email IDs:",
                result["linked_email_id"]
            )

            return result

        except Exception as ex:

            print(
                "Profile email extraction failed:",
                repr(ex)
            )

            return result

    # =====================================================
    # EMAIL VALIDATION
    # =====================================================

    @staticmethod
    def is_valid_email(email):

        if not email:

            return False

        email = email.strip()

        if len(email) > 254:

            return False

        if "@" not in email:

            return False

        # Avoid obvious LinkedIn/system artifacts.

        blocked_domains = {

            "linkedin.com",

            "example.com",

        }

        domain = (
            email
            .rsplit("@", 1)[-1]
            .lower()
        )

        if domain in blocked_domains:

            return False

        return bool(
            re.match(
                r"^[A-Za-z0-9._%+-]+"
                r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
                email
            )
        )