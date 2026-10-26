@echo off
setlocal
cd /d "%~dp0"
title My Switcher Builder
echo Installing Python dependencies...
py -3 -m pip install --upgrade pip
if errorlevel 1 goto fail
py -3 -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Checking Python syntax...
py -3 -m py_compile my_switcher.py
if errorlevel 1 goto fail
echo Building MySwitcher.exe...
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name MySwitcher my_switcher.py
if errorlevel 1 goto fail
echo Done: dist\MySwitcher.exe
pause
exit /b 0
:fail
echo Build failed. Please take a screenshot of this window and send it.
pause
exit /b 1
