@echo off

echo Installing required packages...

pip install -r requirements.txt

playwright install chromium

if not exist exports mkdir exports
if not exist screenshots mkdir screenshots
if not exist profile mkdir profile

echo Installation Completed

pause