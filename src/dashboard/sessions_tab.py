"""Sessions tab: laptop open sessions timeline (restart-proof proof)."""

import tkinter as tk

from src.dashboard.mock_data import DayStats
from src.utils.time_format import fmt_clock, fmt_hm

BG = "#0f1420"
CARD = "#141a28"
FG = "#eaf0ff"
SUB = "#8b93a7"

REASON_LABEL = {
    "SHUTDOWN": "Shutdown",
    "RESTART": "Restart",
    "SLEEP": "Sleep",
    "LOCK": "Locked",
    "CRASH": "Unexpected end",
    "RUNNING": "Running now",
}


class SessionsTab(tk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, bg=BG, **kw)

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=24, pady=(16, 8))
        tk.Label(header, text="LAPTOP SESSIONS", bg=BG, fg=SUB,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(header, text="Open time is tracked across restarts — "
                              "each boot is its own session",
                 bg=BG, fg=SUB, font=("Segoe UI", 9)).pack(side="right")

        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scroll = tk.Scrollbar(self, orient="vertical",
                                   command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self.canvas_window, width=e.width - 4))
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True,
                         padx=(24, 0), pady=(0, 16))
        self.scroll.pack(side="right", fill="y", pady=(0, 16), padx=(6, 20))
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _on_wheel(self, event) -> None:
        if self.canvas.winfo_ismapped():
            self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    def render(self, stats: DayStats) -> None:
        for w in self.inner.winfo_children():
            w.destroy()
        for s in stats.sessions:
            card = tk.Frame(self.inner, bg=CARD)
            card.pack(fill="x", pady=(0, 10))

            top = tk.Frame(card, bg=CARD)
            top.pack(fill="x", padx=14, pady=(10, 2))
            tk.Label(top,
                     text=f"{fmt_clock(s.start_sec)}  –  {fmt_clock(s.end_sec)}",
                     bg=CARD, fg=FG,
                     font=("Segoe UI Semibold", 11)).pack(side="left")
            tk.Label(top, text=REASON_LABEL.get(s.reason, s.reason),
                     bg=CARD, fg=SUB, font=("Segoe UI", 9)).pack(side="right")

            bottom = tk.Frame(card, bg=CARD)
            bottom.pack(fill="x", padx=14, pady=(0, 12))
            tk.Label(bottom, text=f"Active {fmt_hm(s.active_sec)}",
                     bg=CARD, fg="#4fc3f7",
                     font=("Segoe UI", 10)).pack(side="left", padx=(0, 16))
            tk.Label(bottom, text=f"Idle {fmt_hm(s.idle_sec)}",
                     bg=CARD, fg=SUB, font=("Segoe UI", 10)).pack(
                side="left", padx=(0, 16))
            tk.Label(bottom,
                     text=f"Open {fmt_hm(s.end_sec - s.start_sec)}",
                     bg=CARD, fg=SUB, font=("Segoe UI", 10)).pack(side="left")
