"""Per-website tracking via browser window titles (no extension needed).

Browsers put the page title in the window title, e.g.
    "Lo-fi beats - YouTube - Google Chrome"
    "Inbox (12) - Gmail - Microsoft Edge"
We classify the title with keyword rules into a site label.
Unrecognized pages count as "Other web".
"""

import re

BROWSERS = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",
    "opera_gx.exe", "vivaldi.exe", "arc.exe",
}

OTHER_WEB = "Other web"

# (regex on full window title, site label) - first match wins
_RULES = [
    (r"youtube", "YouTube"),
    (r"gmail|mail\.google", "Gmail"),
    (r"google docs", "Google Docs"),
    (r"google sheets", "Google Sheets"),
    (r"google slides", "Google Slides"),
    (r"google drive", "Google Drive"),
    (r"google calendar", "Google Calendar"),
    (r"google maps", "Google Maps"),
    (r"chatgpt|openai", "ChatGPT"),
    (r"gemini", "Gemini"),
    (r"github", "GitHub"),
    (r"stack overflow|stackoverflow", "Stack Overflow"),
    (r"reddit", "Reddit"),
    (r"\bx\b.*twitter|twitter|\bX - ", "X (Twitter)"),
    (r"linkedin", "LinkedIn"),
    (r"instagram", "Instagram"),
    (r"facebook", "Facebook"),
    (r"whatsapp", "WhatsApp Web"),
    (r"telegram web", "Telegram Web"),
    (r"discord", "Discord"),
    (r"netflix", "Netflix"),
    (r"prime video", "Prime Video"),
    (r"hotstar|jiocinema", "Streaming (IN)"),
    (r"amazon\.", "Amazon"),
    (r"flipkart", "Flipkart"),
    (r"amazon\.in|amazon shopping", "Amazon"),
    (r"wikipedia", "Wikipedia"),
    (r"notion\.so|notion - ", "Notion"),
    (r"figma", "Figma"),
    (r"canva", "Canva"),
    (r"coursera", "Coursera"),
    (r"udemy", "Udemy"),
    (r"leetcode", "LeetCode"),
    (r"geeksforgeeks", "GeeksforGeeks"),
    (r"hackerrank", "HackerRank"),
    (r"twitch", "Twitch"),
    (r"spotify web|open\.spotify", "Spotify"),
    (r"zomato|swiggy", "Food delivery"),
    (r"irctc|makemytrip|booking\.com", "Travel booking"),
]

_SITE_COLORS = {
    "YouTube": "#ef5350",
    "Gmail": "#e57373",
    "Google Docs": "#4fc3f7",
    "Google Sheets": "#81c784",
    "Google Slides": "#ffb74d",
    "Google Drive": "#4dd0e1",
    "Google Calendar": "#7986cb",
    "Google Maps": "#aed581",
    "ChatGPT": "#26a69a",
    "Gemini": "#9575cd",
    "GitHub": "#b0bec5",
    "Stack Overflow": "#ffb74d",
    "Reddit": "#ff8a65",
    "X (Twitter)": "#90a4ae",
    "LinkedIn": "#64b5f6",
    "Instagram": "#f06292",
    "Facebook": "#5c6bc0",
    "WhatsApp Web": "#66bb6a",
    "Telegram Web": "#4fc3f7",
    "Discord": "#b39ddb",
    "Netflix": "#e57373",
    "Amazon": "#ffb74d",
    "Other web": "#5b6379",
}

_COLOR_CYCLE = ["#4fc3f7", "#ffd54f", "#81c784", "#f48fb1", "#b39ddb",
                "#90caf9", "#a5d6a7", "#ef9a9a", "#ce93d8", "#4dd0e1"]

_COMPILED = [(re.compile(p, re.IGNORECASE), label) for p, label in _RULES]


def is_browser(exe: str) -> bool:
    return exe.lower() in BROWSERS


def parse_site(title: str) -> str:
    """Classify a browser window title into a site label (best effort)."""
    t = title or ""
    for rx, label in _COMPILED:
        if rx.search(t):
            return label
    return OTHER_WEB


def site_color(site: str, index: int = 0) -> str:
    if site in _SITE_COLORS:
        return _SITE_COLORS[site]
    return _COLOR_CYCLE[index % len(_COLOR_CYCLE)]
