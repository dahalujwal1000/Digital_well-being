; Inno Setup script for Digital Wellbeing
; Build the exe first (build_exe.bat), then compile this script with
; Inno Setup (free: https://jrsoftware.org/isinfo.php) to produce
; Output\DigitalWellbeing-Setup.exe - a normal Windows installer with
; Start Menu shortcut, optional autostart and a clean uninstaller.

#define MyAppName "Digital Wellbeing"
#define MyAppVersion "1.3.2"
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
; autostart is implemented as a Windows Task Scheduler "on logon" task
; (30s after logon, never stopped by battery mode, restarted by Windows if it
; crashes). The app owns both mechanisms in src/utils/autostart.py - the
; installer only asks it to switch it on, so the installer and the tray
; toggle can never desync into two autostart entries.
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
; autostart is owned by the app (src/utils/autostart.py): the installer only
; asks it to switch on the Windows Task Scheduler "on logon" task, which needs
; the elevated process the installer already has - and enabling it also clears
; a legacy HKCU Run key value left by v1.2 setups, so there is exactly one
; autostart entry at all times.

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Parameters: "--enable-autostart --autostart-mode task"; \
    Flags: runhidden; Tasks: autostart; \
    StatusMsg: "Registering the 'start at logon' task..."
Filename: "{app}\{#MyAppExeName}"; \
    Flags: nowait runasoriginaluser skipifsilent; \
    StatusMsg: "Starting Digital Wellbeing..."
Filename: "{app}\{#MyAppExeName}"; Parameters: "--dashboard"; \
    Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait \
    postinstall runasoriginaluser skipifsilent

[UninstallRun]
; Let the app undo its own autostart entry (the same code the tray toggle
; calls), then let schtasks clean up even if the exe was locked by a running
; tracker and therefore could not be run above.
Filename: "{app}\{#MyAppExeName}"; Parameters: "--disable-autostart"; \
    Flags: runhidden; RunOnceId: "DwAutostartOff"
Filename: "{sys}\schtasks.exe"; \
    Parameters: "/delete /tn ""DigitalWellbeing"" /f"; \
    Flags: runhidden; RunOnceId: "DwAutostartTaskCleanup"
