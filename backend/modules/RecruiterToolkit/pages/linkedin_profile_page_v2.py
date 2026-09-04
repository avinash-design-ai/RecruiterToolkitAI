import re

from pages.base_page import BasePage


class LinkedInProfilePageV2(BasePage):

    def __init__(self, page):

        super().__init__(page)
        self._original_profile_page = page
        self._temporary_profile_page = None

        self.profile_url = ""

    # =====================================================
    # OPEN PROFILE
    # =====================================================

    def open_profile(self, profile_url):
        """
        Open an employee profile through the authenticated LinkedIn
        employee-search page.

        Direct profile goto() can trigger LinkedIn authwall even when
        the profile is accessible from the authenticated employee
        search results.

        Therefore the preferred path is:

            authenticated search page
                -> exact /in/ employee link
                -> Ctrl-click
                -> new tab
                -> extract existing profile data

        The existing email extraction remains unchanged.
        """

        print("=" * 60)
        print("OPENING EMPLOYEE PROFILE")
        print("=" * 60)

        print(
            "Requested profile URL:",
            profile_url
        )

        if not profile_url:
            print("Profile URL is empty.")
            return False

        def canonical(url):

            if not url:
                return ""

            url = url.strip()

            if url.startswith("/"):
                url = (
                    "https://www.linkedin.com"
                    + url
                )

            url = (
                url
                .split("?")[0]
                .split("#")[0]
                .rstrip("/")
            )

            return url.lower()

        requested = canonical(profile_url)

        # --------------------------------------------------------
        # Restore the original search page if a previous temporary
        # profile tab is still active.
        # --------------------------------------------------------

        temporary_page = getattr(
            self,
            "_temporary_profile_page",
            None
        )

        original_page = getattr(
            self,
            "_original_profile_page",
            None
        )

        if temporary_page is not None:

            try:
                if not temporary_page.is_closed():
                    temporary_page.close()
            except Exception:
                pass

        self._temporary_profile_page = None

        if original_page is not None:

            try:
                self.page = original_page
            except Exception:
                pass

        # --------------------------------------------------------
        # Find the authenticated employee-search page in the SAME
        # Playwright browser context.
        # --------------------------------------------------------

        search_page = None

        try:

            for candidate in self.page.context.pages:

                try:

                    url = candidate.url.lower()

                    if (
                        "/search/results/people/"
                        in url
                        and "currentcompany="
                        in url
                    ):

                        search_page = candidate
                        break

                except Exception:
                    continue

        except Exception as ex:

            print(
                "Could not inspect browser pages:",
                repr(ex)
            )

        # --------------------------------------------------------
        # Preferred path: exact profile link already rendered on
        # authenticated search results.
        # --------------------------------------------------------

        if search_page is not None:

            print(
                "Authenticated employee search page found:"
            )

            print(
                search_page.url
            )

            try:

                links = search_page.locator(
                    "a[href*='/in/']:visible"
                )

                count = links.count()

                print(
                    "Visible employee profile links:",
                    count
                )

                matching_link = None

                for i in range(count):

                    try:

                        link = links.nth(i)

                        href = canonical(
                            link.get_attribute(
                                "href"
                            )
                        )

                        if (
                            href
                            and href == requested
                        ):

                            matching_link = link
                            break

                    except Exception:
                        continue

                if matching_link is not None:

                    print(
                        "Exact employee profile link "
                        "found on authenticated search page."
                    )

                    print(
                        "Opening employee profile in new tab..."
                    )

                    try:

                        with (
                            search_page.context.expect_page(
                                timeout=15000
                            )
                            as page_info
                        ):

                            matching_link.click(
                                modifiers=["Control"],
                                timeout=15000
                            )

                        profile_page = page_info.value

                        profile_page.wait_for_load_state(
                            "domcontentloaded",
                            timeout=30000
                        )

                        profile_page.wait_for_timeout(
                            3000
                        )

                        print(
                            "Profile tab URL:",
                            profile_page.url
                        )

                        current_url = (
                            profile_page.url.lower()
                        )

                        # ------------------------------------------------
                        # Reject LinkedIn auth/login/remember-me pages.
                        # ------------------------------------------------

                        if (
                            "/authwall"
                            in current_url
                            or "/login"
                            in current_url
                            or "/ssr-login/"
                            in current_url
                        ):

                            print(
                                "PROFILE TAB HIT AUTH/LOGIN PAGE."
                            )

                            try:
                                profile_page.close()
                            except Exception:
                                pass

                            return False

                        if "/in/" not in current_url:

                            print(
                                "PROFILE TAB DID NOT OPEN "
                                "A REAL /in/ PROFILE."
                            )

                            try:
                                profile_page.close()
                            except Exception:
                                pass

                            return False

                        # ------------------------------------------------
                        # Keep the authenticated search page alive.
                        # Temporarily switch self.page to the profile tab.
                        # ------------------------------------------------

                        self._original_profile_page = (
                            search_page
                        )

                        self._temporary_profile_page = (
                            profile_page
                        )

                        self.page = profile_page

                        print(
                            "Authenticated employee profile "
                            "opened successfully."
                        )

                        return True

                    except Exception as ex:

                        print(
                            "Authenticated profile-tab "
                            "opening failed:",
                            repr(ex)
                        )

                else:

                    print(
                        "Exact employee profile URL was "
                        "not found among visible search links."
                    )

            except Exception as ex:

                print(
                    "Authenticated search-page profile "
                    "lookup failed:",
                    repr(ex)
                )

        # --------------------------------------------------------
        # Controlled fallback.
        #
        # This preserves the old behavior if LinkedIn changes the
        # search-page markup and the exact link cannot be found.
        # --------------------------------------------------------

        print(
            "Trying controlled direct profile navigation fallback..."
        )

        try:

            self.page.goto(
                profile_url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            self.page.wait_for_timeout(
                4000
            )

            current_url = (
                self.page.url.lower()
            )

            print(
                "Profile navigation URL:",
                self.page.url
            )

            if (
                "/authwall"
                in current_url
                or "/login"
                in current_url
                or "/ssr-login/"
                in current_url
            ):

                print(
                    "AUTHWALL / LOGIN DETECTED."
                )

                return False

            if "/in/" not in current_url:

                print(
                    "Profile URL is not a LinkedIn /in/ profile."
                )

                return False

            print(
                "Direct profile navigation succeeded."
            )

            return True

        except Exception as ex:

            print(
                "Profile navigation failed:",
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


# ============================================================
# Temporary profile-tab cleanup wrapper
# ============================================================

_OriginalLinkedInProfilePageV2GetProfile = (
    LinkedInProfilePageV2.get_profile
)

def _LinkedInProfilePageV2GetProfileWithCleanup(self):
    try:
        return _OriginalLinkedInProfilePageV2GetProfile(self)
    finally:
        temporary_page = getattr(
            self,
            "_temporary_profile_page",
            None
        )

        original_page = getattr(
            self,
            "_original_profile_page",
            None
        )

        if temporary_page is not None:
            try:
                if not temporary_page.is_closed():
                    temporary_page.close()
            except Exception as ex:
                print(
                    "Temporary profile-tab cleanup failed:",
                    repr(ex)
                )

        self._temporary_profile_page = None

        if original_page is not None:
            try:
                self.page = original_page
            except Exception as ex:
                print(
                    "Original search-page restoration failed:",
                    repr(ex)
                )

LinkedInProfilePageV2.get_profile = (
    _LinkedInProfilePageV2GetProfileWithCleanup
)
