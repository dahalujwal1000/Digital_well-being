"""Weekly comparison with keyboard-accessible day navigation."""
import tkinter as tk
from datetime import date
from src.dashboard.theme import (
    Page, label, heading, button, BG, SURFACE, MUTED, TEXT, ACCENT, FONT)
from src.utils.time_format import fmt_hm


class WeekTab(Page):
    def __init__(self, master, on_day_click=None, **kw):
        super().__init__(master, **kw)
        self.on_day_click = on_day_click
        self.days = []
        heading(self.content, "Your week in perspective",
                "Compare the last seven days. Select a day to explore its usage.")
        self.total = label(self.content, "", 18, True)
        self.total.pack(anchor="w")
        self.average = label(self.content, "", color=MUTED)
        self.average.pack(anchor="w", pady=(6, 22))
        self.chart = tk.Canvas(self.content, bg=SURFACE, height=250,
                                highlightthickness=0)
        self.chart.pack(fill="x", pady=(0, 24))
        self.chart.bind("<Configure>", lambda e: self._draw())
        self.chart.bind("<Button-1>", self._click)
        self.rows = tk.Frame(self.content, bg=BG)
        self.rows.pack(fill="x")

    def render(self, days):
        self.days = days
        total = sum(d.active_sec for d in days)
        self.total.configure(text=f"{fmt_hm(total)} active this week")
        self.average.configure(text=f"{fmt_hm(total//max(1,len(days)))} daily average · Includes today so far")
        for w in self.rows.winfo_children():
            w.destroy()
        for d in reversed(days):
            row = tk.Frame(self.rows, bg=SURFACE, padx=16, pady=8)
            row.pack(fill="x", pady=(0, 2))
            text = d.day.strftime("%A, %d %b")
            if d.day == date.today():
                text += " · Today"
            button(row, text, lambda day=d.day: self._open(day)).pack(side="left")
            label(row, fmt_hm(d.active_sec), 12, True).pack(side="right")
        self._draw()

    def _draw(self):
        c = self.chart
        c.delete("all")
        width = max(c.winfo_width(), 300)
        step = (width-40)/max(1, len(self.days))
        peak = max(1, max((d.active_sec for d in self.days), default=1))
        for i, d in enumerate(self.days):
            x = 20 + step*(i+.5)
            height = 155*d.active_sec/peak
            c.create_rectangle(x-18, 205-height, x+18, 205,
                               fill=ACCENT if d.day == date.today() else "#7FA58D", width=0)
            c.create_text(x, 190-height, text=fmt_hm(d.active_sec),
                          fill=TEXT, font=(FONT, 10))
            c.create_text(x, 228, text=d.day.strftime("%a"),
                          fill=MUTED, font=(FONT, 10))
        c.configure(cursor="hand2")

    def _click(self, event):
        step = (max(self.chart.winfo_width(), 300)-40)/max(1, len(self.days))
        i = int((event.x-20)//step)
        if 0 <= i < len(self.days):
            self._open(self.days[i].day)

    def _open(self, day):
        if self.on_day_click:
            self.on_day_click(day)
