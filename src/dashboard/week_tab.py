"""Week tab: last 7 days of active screen time as a bar chart + totals."""

import tkinter as tk
from datetime import date, timedelta

from src.dashboard.mock_data import DayStats
from src.utils.time_format import fmt_hm

BG = "#0f1420"
CARD = "#141a28"
FG = "#eaf0ff"
SUB = "#8b93a7"
ACCENT = "#4fc3f7"
TODAY_COLOR = "#ffd54f"


class WeekTab(tk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, bg=BG, **kw)
        self.days: list[DayStats] = []

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=24, pady=(16, 8))
        tk.Label(header, text="LAST 7 DAYS", bg=BG, fg=SUB,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.total_lbl = tk.Label(header, text="", bg=BG, fg=SUB,
                                  font=("Segoe UI", 10))
        self.total_lbl.pack(side="right")

        self.canvas = tk.Canvas(self, bg=CARD, height=230,
                                highlightthickness=0)
        self.canvas.pack(fill="x", padx=24, pady=(4, 8))
        self.canvas.bind("<Configure>", lambda e: self._draw())

        self.list_frame = tk.Frame(self, bg=BG)
        self.list_frame.pack(fill="both", expand=True, padx=24,
                             pady=(4, 16))

    def render(self, days: list[DayStats]) -> None:
        self.days = days
        total = sum(d.active_sec for d in days)
        self.total_lbl.config(
            text=f"7-day total {fmt_hm(total)}  •  "
                 f"avg {fmt_hm(total // max(1, len(days)))}")
        for w in self.list_frame.winfo_children():
            w.destroy()
        for d in reversed(days):
            label = d.day.strftime("%a %b %d")
            if d.day == date.today():
                label += "  (today)"
            row = tk.Frame(self.list_frame, bg=CARD)
            row.pack(fill="x", pady=(0, 6))
            tk.Label(row, text=label, bg=CARD, fg=FG,
                     font=("Segoe UI", 10)).pack(side="left", padx=14,
                                                 pady=6)
            tk.Label(row, text=fmt_hm(d.active_sec), bg=CARD, fg=FG,
                     font=("Segoe UI Semibold", 10)).pack(side="right",
                                                          padx=14, pady=6)

    def _draw(self) -> None:
        c = self.canvas
        c.delete("all")
        w = max(c.winfo_width(), 300)
        h = max(c.winfo_height(), 150)
        pad_b, pad_t = 26, 12
        plot_h = h - pad_b - pad_t
        peak = max(1, max((d.active_sec for d in self.days), default=1))
        bar_area = w / max(1, len(self.days))
        bar_w = max(8, int(bar_area * 0.5))

        # gridlines
        for g in range(5):
            y = pad_t + plot_h - plot_h * g / 4
            c.create_line(0, y, w, y, fill="#1a2130")

        for i, d in enumerate(self.days):
            x = i * bar_area + (bar_area - bar_w) / 2
            bh = plot_h * d.active_sec / peak
            color = TODAY_COLOR if d.day == date.today() else ACCENT
            if bh > 1:
                c.create_rectangle(x, pad_t + plot_h - bh,
                                   x + bar_w, pad_t + plot_h,
                                   fill=color, width=0)
            c.create_text(x + bar_w / 2, pad_t + plot_h - bh - 8,
                          text=fmt_hm(d.active_sec), fill=FG,
                          font=("Segoe UI", 8))
            c.create_text(x + bar_w / 2, h - pad_b / 2,
                          text=d.day.strftime("%a"), fill=SUB,
                          font=("Segoe UI", 9))
