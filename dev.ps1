$env:Path += ";C:\Users\Avinash B\AppData\Local\Programs\Git\cmd"
$env:Path += ";D:\Tools\node-v24.18.1-win-x64\node-v24.18.1-win-x64"

Write-Host "Development environment ready!"
git --version
node --version
npm --version