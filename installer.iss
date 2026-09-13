; Inno Setup script for Digital Wellbeing
; Build the exe first (build_exe.bat), then compile this script with
; Inno Setup (free: https://jrsoftware.org/isinfo.php) to produce
; Output\DigitalWellbeing-Setup.exe - a normal Windows installer with
; Start Menu shortcut, optional autostart and a clean uninstaller.

#define MyAppName "Digital Wellbeing"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "Digital Wellbeing"
#define MyAppExeName "DigitalWellbeing.exe"

[Setup]
AppId={{7C6F1D4E-2A3B-4C5D-9E0F-A1B2C3D4E5F6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\DigitalWellbeing
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=DigitalWellbeing-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; not admin-only: installs per-machine if allowed, falls back otherwise
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Start Digital Wellbeing when I log in"; \
    GroupDescription: "Startup:"

[Files]
Source: "dist\DigitalWellbeing\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    Parameters: "--dashboard"
Name: "{group}\{#MyAppName} (Tracker)"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    Parameters: "--dashboard"; Tasks: desktopicon
; optional login autostart (per-user HKCU Run key, standard & transparent)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--dashboard"; \
    Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait \
    postinstall skipifsilent

[UninstallRun]
; note: the uninstaller cannot kill a running process itself; ask the user
; to exit from the tray icon first (Exit). Registry autostart written by
; the app's own toggle is under HKCU\...\Run "DigitalWellbeing".
