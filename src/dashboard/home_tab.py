"""Overview: active share, daily context, and hourly activity."""
import tkinter as tk
from src.dashboard.theme import (
    Page, label, heading, usage_row, BG, SURFACE, TEXT, MUTED,
    ACCENT, TINT, IDLE, LINE, FONT)
from src.dashboard.widgets.bar_chart import HourlyBarChart
from src.utils.time_format import fmt_hm, fmt_clock


class HomeTab(Page):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        p = self.content
        heading(p, "Your digital day", "A little awareness goes a long way.")
        summary = tk.Frame(p, bg=SURFACE, padx=24, pady=18)
        summary.pack(fill="x")
        self.ring = tk.Canvas(summary, width=226, height=226,
                              bg=SURFACE, highlightthickness=0)
        self.ring.pack(side="left", padx=(0, 28))
        details = tk.Frame(summary, bg=SURFACE)
        details.pack(side="left", fill="both", expand=True)
        self._stacked = False
        def reflow(event):
            stacked = event.width < 680
            if stacked == self._stacked:
                return
            self._stacked = stacked
            self.ring.pack_forget()
            details.pack_forget()
            self.ring.pack(side="top" if stacked else "left",
                           padx=0 if stacked else (0, 28),
                           pady=(0, 16) if stacked else 0)
            details.pack(side="top" if stacked else "left",
                         fill="both", expand=True)
        summary.bind("<Configure>", reflow)
        label(details, "Time on your device", 14, True).pack(anchor="w", pady=(6, 18))
        self.metrics = {}
        for key in ("Device open", "Idle time", "Unlocks"):
            row = tk.Frame(details, bg=SURFACE)
            row.pack(fill="x", pady=8)
            label(row, key, color=MUTED).pack(side="left")
            value = label(row, "", 12, True)
            value.pack(side="right", padx=(16, 0))
            self.metrics[key] = value
        self.context = label(p, "", color=MUTED, anchor="w")
        self.context.pack(fill="x", pady=(12, 18))
        label(p, "Activity through the day", 15, True).pack(anchor="w")
        label(p, "Green: active   ·   Pale green: idle", color=MUTED).pack(
            anchor="w", pady=(6, 12))
        self.chart = HourlyBarChart(
            p, bg=BG, active_color=ACCENT, idle_color=IDLE,
            grid_color=LINE, label_fg=MUTED)
        self.chart.configure(height=190)
        self.chart.pack(fill="x", pady=(0, 26))
        label(p, "Most used apps", 15, True).pack(anchor="w", pady=(0, 14))
        self.top_apps = tk.Frame(p, bg=BG)
        self.top_apps.pack(fill="x")
        label(p, "Active time is based on keyboard and mouse activity.\n"
                 "After 60 seconds without input, time is recorded as idle.",
              size=10, color=MUTED, justify="left").pack(
                  anchor="w", pady=(22, 0))

    def render(self, stats):
        c = self.ring
        c.delete("all")
        c.create_oval(14, 14, 212, 212, outline=TINT, width=15)
        fraction = min(1, stats.active_sec / stats.open_sec) if stats.open_sec else 0
        if fraction >= .999:
            c.create_oval(14, 14, 212, 212, outline=ACCENT, width=15)
        elif fraction > 0:
            c.create_arc(14, 14, 212, 212, start=90, extent=-360*fraction,
                         style="arc", outline=ACCENT, width=15)
        c.create_text(113, 103, text=fmt_hm(stats.active_sec),
                      font=(FONT, 27, "bold"), fill=TEXT)
        c.create_text(113, 135, text="Active time", font=(FONT, 11), fill=MUTED)
        self.metrics["Device open"].configure(text=fmt_hm(stats.open_sec))
        self.metrics["Idle time"].configure(text=fmt_hm(stats.idle_sec))
        self.metrics["Unlocks"].configure(text=str(stats.unlocks))
        first = fmt_clock(stats.first_used_sec) if stats.first_used_sec is not None else "—"
        last = fmt_clock(stats.last_used_sec) if stats.last_used_sec is not None else "—"
        self.context.configure(text=(
            f"First activity {first}   ·   Last activity {last}"
            if stats.open_sec else "No usage recorded for this day yet."))
        self.chart.set_data(stats.hourly_active or [0]*24,
                            stats.hourly_idle or [0]*24)
        for w in self.top_apps.winfo_children():
            w.destroy()
        total = max(1, sum(a.active_sec for a in stats.apps))
        for app in sorted(stats.apps, key=lambda a: a.active_sec, reverse=True)[:3]:
            usage_row(self.top_apps, app.name, app.active_sec, app.active_sec/total)
        if not stats.apps:
            label(self.top_apps, "Your most used apps will appear here.",
                  color=MUTED).pack(anchor="w", pady=12)
