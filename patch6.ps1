$p="backend\modules\RecruiterToolkit\linkedin_runner.py"
$c=Get-Content $p -Raw

$old=@'
            # -------------------------------------------------
            # Credentials check
            # -------------------------------------------------

            if (
                not linkedin_email
                or not linkedin_password
            ):

                print(
                    "LinkedIn credentials missing"
                )

                return {

                    "success": False,

                    "login_required": True,

                    "message":
                        "LinkedIn credentials required."

                }

            # -------------------------------------------------
            # Login
            # -------------------------------------------------

            print(
                "Logging into LinkedIn..."
            )

            login = LoginPage(page)

            login.login(
                linkedin_email,
                linkedin_password
            )

            print(
                "Login form submitted."
            )

            # -------------------------------------------------
            # Wait for actual login result
            # -------------------------------------------------

            login_result = _wait_for_login_result(
                page,
                timeout_seconds=120
            )
'@

$new=@'
            # -------------------------------------------------
            # Authentication-only mode
            # -------------------------------------------------

            if authentication_only:

                print("=" * 60)
                print("6 - AUTHENTICATION-ONLY MODE")
                print("=" * 60)

                print(
                    "Manual LinkedIn authentication is required."
                )

                print(
                    "Waiting for LinkedIn authentication..."
                )

                login_result = _wait_for_login_result(
                    page,
                    timeout_seconds=300
                )

            else:

                # -------------------------------------------------
                # Credentials check
                # -------------------------------------------------

                if (
                    not linkedin_email
                    or not linkedin_password
                ):

                    print(
                        "LinkedIn credentials missing"
                    )

                    return {

                        "success": False,

                        "login_required": True,

                        "message":
                            "LinkedIn credentials required."

                    }

                # -------------------------------------------------
                # Login
                # -------------------------------------------------

                print(
                    "Logging into LinkedIn..."
                )

                login = LoginPage(page)

                login.login(
                    linkedin_email,
                    linkedin_password
                )

                print(
                    "Login form submitted."
                )

                # -------------------------------------------------
                # Wait for actual login result
                # -------------------------------------------------

                login_result = _wait_for_login_result(
                    page,
                    timeout_seconds=120
                )
'@

if(-not $c.Contains($old)){throw "PATCH6 TARGET NOT FOUND"}

$c=$c.Replace($old,$new)

[System.IO.File]::WriteAllText(
    (Join-Path (Get-Location) $p),
    $c,
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host "CHANGE 6 APPLIED SUCCESSFULLY" -ForegroundColor Green