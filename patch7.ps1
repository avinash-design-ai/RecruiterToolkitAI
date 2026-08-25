$p="backend\routes\linkedin.py"
$c=Get-Content $p -Raw

$old=@'
            linkedin_password=data.linkedin_password,
            authentication_only=True,
        )
'@

$new=@'
            linkedin_password=data.linkedin_password,
        )
'@

if(-not $c.Contains($old)){
    throw "V2 authentication_only call target not found"
}

$c=$c.Replace($old,$new)

[System.IO.File]::WriteAllText(
    (Join-Path (Get-Location) $p),
    $c,
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host "CHANGE 7 APPLIED SUCCESSFULLY" -ForegroundColor Green