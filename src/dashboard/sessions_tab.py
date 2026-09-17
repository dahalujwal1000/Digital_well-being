"""Readable chronological device sessions."""
import tkinter as tk
from src.dashboard.theme import Page, label, heading, BG, SURFACE, MUTED, ACCENT
from src.utils.time_format import fmt_clock, fmt_hm

REASONS = {"RUNNING": "In progress", "SLEEP": "Sleep", "SHUTDOWN": "Shutdown",
           "RESTART": "Restart", "CRASH": "Unexpected end", "LOGOFF": "Signed out",
           "MIDNIGHT": "New day", "LOCK": "Locked"}


class SessionsTab(Page):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        heading(self.content, "Your sessions",
                "A timeline of device use, from start to sleep or shutdown.")
        self.summary = label(self.content, "", color=MUTED)
        self.summary.pack(anchor="w", pady=(0, 18))
        self.rows = tk.Frame(self.content, bg=BG)
        self.rows.pack(fill="x")

    def render(self, stats):
        for w in self.rows.winfo_children():
            w.destroy()
        self.summary.configure(text=f"{len(stats.sessions)} sessions on this day")
        if not stats.sessions:
            label(self.rows, "No sessions recorded for this day.",
                  color=MUTED).pack(anchor="w", pady=24)
        for s in stats.sessions:
            row = tk.Frame(self.rows, bg=SURFACE, padx=20, pady=20)
            row.pack(fill="x", pady=(0, 12))
            top = tk.Frame(row, bg=SURFACE)
            top.pack(fill="x")
            label(top, f"{fmt_clock(s.start_sec)} — {fmt_clock(s.end_sec)}",
                  13, True).pack(side="left")
            label(top, REASONS.get(s.reason, s.reason), 10,
                  color=ACCENT if s.reason == "RUNNING" else MUTED).pack(side="right")
            label(row, f"Active {fmt_hm(s.active_sec)}     ·     "
                       f"Idle {fmt_hm(s.idle_sec)}     ·     "
                       f"Open {fmt_hm(max(0, s.end_sec-s.start_sec))}",
                  color=MUTED).pack(anchor="w", pady=(12, 0))
