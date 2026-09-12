@echo off
REM Builds standalone Windows executables with PyInstaller.
REM Output: dist\DigitalWellbeingTracker.exe   (background tracker + tray)
REM         dist\DigitalWellbeingDashboard.exe (the dashboard window)
REM Requires: this project's venv activated (or python on PATH).

setlocal
cd /d "%~dp0"

python -m pip install --quiet pyinstaller || goto :err

python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name DigitalWellbeingTracker ^
  --collect-all customtkinter ^
  --hidden-import win32timezone ^
  run_tracker.py || goto :err

python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name DigitalWellbeingDashboard ^
  --collect-all customtkinter ^
  run_dashboard.py || goto :err

echo.
echo BUILD OK:
echo   dist\DigitalWellbeingTracker.exe
echo   dist\DigitalWellbeingDashboard.exe
goto :eof

:err
echo BUILD FAILED - see output above.
exit /b 1
