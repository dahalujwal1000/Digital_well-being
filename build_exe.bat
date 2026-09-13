@echo off
REM Builds the single DigitalWellbeing app with PyInstaller.
REM Output: dist\DigitalWellbeing\DigitalWellbeing.exe  (tracker + tray,
REM         pass --dashboard to open the dashboard window)
REM Uses --onedir (folder output) - starts faster and is far less likely to
REM be flagged by antivirus than a self-extracting onefile exe.
REM Requires: this project's venv activated (or python on PATH).

setlocal
cd /d "%~dp0"

python -m pip install --quiet pyinstaller || goto :err

python -m PyInstaller --noconfirm --clean ^
  --name DigitalWellbeing ^
  --collect-all customtkinter ^
  --hidden-import win32timezone ^
  run_app.py || goto :err

echo.
echo BUILD OK:
echo   dist\DigitalWellbeing\DigitalWellbeing.exe
echo   (wrap the folder with installer.iss using Inno Setup to publish)
goto :eof

:err
echo BUILD FAILED - see output above.
exit /b 1
