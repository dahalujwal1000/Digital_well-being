"""Friendly display names for known executables."""

FRIENDLY = {
    "code.exe": "VS Code",
    "chrome.exe": "Chrome",
    "msedge.exe": "Edge",
    "firefox.exe": "Firefox",
    "spotify.exe": "Spotify",
    "discord.exe": "Discord",
    "explorer.exe": "Explorer",
    "steam.exe": "Steam",
    "winword.exe": "Word",
    "excel.exe": "Excel",
    "powerpnt.exe": "PowerPoint",
    "outlook.exe": "Outlook",
    "devenv.exe": "Visual Studio",
    "pycharm64.exe": "PyCharm",
    "idea64.exe": "IntelliJ",
    "telegram.exe": "Telegram",
    "notion.exe": "Notion",
    "obsidian.exe": "Obsidian",
    "postman.exe": "Postman",
    "wt.exe": "Terminal",
    "windowsterminal.exe": "Terminal",
    "powershell.exe": "PowerShell",
    "cmd.exe": "Command Prompt",
}


def friendly_name(exe: str) -> str:
    return FRIENDLY.get(exe.lower(), exe.rsplit(".", 1)[0].title())
