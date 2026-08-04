@echo off

echo Installing required packages...
py -m pip install -r requirements.txt

echo.
echo Installing Playwright Chromium...
py -m playwright install chromium

echo.
echo Installation completed.
pause