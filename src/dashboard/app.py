"""Digital Wellbeing desktop dashboard."""
import ctypes
import logging
import tkinter as tk
from datetime import date, timedelta

from src.dashboard import data_source
from src.dashboard.theme import BG, SURFACE, TEXT, MUTED, ACCENT, TINT, LINE
from src.dashboard.theme import label, button
from src.dashboard.home_tab import HomeTab
from src.dashboard.apps_tab import AppsTab
from src.dashboard.sessions_tab import SessionsTab
from src.dashboard.week_tab import WeekTab

log = logging.getLogger("wellbeing.dashboard")


class DigitalWellbeingApp(tk.Tk):
    def __init__(self):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass
        super().__init__()
        self.title("Digital Wellbeing")
        self.geometry("1080x780")
        self.minsize(780, 560)
        self.configure(bg=BG)
        self.today = date.today()
        self.view_date = self.today
        self._refresh_job = None
        self._selected = "Overview"
        self._build_shell()
        self._refresh()
        self._auto_refresh()
        self.bind("<F5>", lambda e: self._refresh())
        self.bind("<Alt-Left>", lambda e: self._shift_date(-1))
        self.bind("<Alt-Right>", lambda e: self._shift_date(1))
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_shell(self):
        header = tk.Frame(self, bg=SURFACE, padx=28, pady=12)
        header.pack(fill="x")
        label(header, "Digital Wellbeing", 17, True).pack(side="left")
        label(header, "Your time, at a glance", color=MUTED).pack(
            side="right")
        tk.Frame(self, bg=LINE, height=1).pack(fill="x")

        toolbar = tk.Frame(self, bg=BG, padx=28, pady=10)
        toolbar.pack(fill="x")
        button(toolbar, "‹", lambda: self._shift_date(-1)).pack(side="left")
        self.date_lbl = label(toolbar, size=12, bold=True, width=22)
        self.date_lbl.pack(side="left", padx=8)
        self.btn_next = button(toolbar, "›", lambda: self._shift_date(1))
        self.btn_next.pack(side="left")
        button(toolbar, "Today", self._go_today).pack(side="left", padx=12)
        button(toolbar, "Refresh", self._refresh).pack(side="right")

        nav = tk.Frame(self, bg=BG, padx=28)
        nav.pack(fill="x", pady=(0, 6))
        self.nav_buttons = {}
        for name in ("Overview", "Apps & websites", "Sessions", "Weekly"):
            btn = button(nav, name, lambda n=name: self._show(n))
            btn.pack(side="left", padx=(0, 8))
            self.nav_buttons[name] = btn

        self.status = label(self, "", size=10, color=MUTED, anchor="w",
                            padx=28, pady=6)
        self.status.pack(fill="x")
        self.bind("<Configure>", self._resize)
        host = tk.Frame(self, bg=BG)
        host.pack(fill="both", expand=True)
        host.rowconfigure(0, weight=1)
        host.columnconfigure(0, weight=1)
        self.home_tab = HomeTab(host)
        self.apps_tab = AppsTab(host)
        self.sessions_tab = SessionsTab(host)
        self.week_tab = WeekTab(host, on_day_click=self._go_to_date)
        self.pages = dict(zip(self.nav_buttons, (
            self.home_tab, self.apps_tab, self.sessions_tab, self.week_tab)))
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self._show("Overview")

    def _resize(self, event):
        if event.widget is self:
            self.status.configure(wraplength=max(200, event.width-60))

    def _show(self, name):
        self._selected = name
        for key, page in self.pages.items():
            if key == name:
                page.grid()
                page.tkraise()
            else:
                page.grid_remove()
        for key, btn in self.nav_buttons.items():
            selected = key == name
            btn.configure(bg=ACCENT if selected else BG,
                          fg="white" if selected else MUTED)
        self.date_lbl.configure(
            text="Last 7 days" if name == "Weekly"
            else self._date_text())

    def _date_text(self):
        prefix = "Today" if self.view_date == self.today else self.view_date.strftime("%a")
        return prefix + " · " + self.view_date.strftime("%d %B")

    def _sync_today(self):
        current = date.today()
        if current == self.today:
            return False
        following_today = self.view_date == self.today
        self.today = current
        if following_today:
            self.view_date = current
        return True

    def _shift_date(self, days):
        self._sync_today()
        self.view_date = min(self.today, self.view_date + timedelta(days=days))
        if self._selected == "Weekly":
            self._show("Overview")
        self._refresh()

    def _go_today(self):
        self._sync_today()
        self.view_date = self.today
        self._show("Overview")
        self._refresh()

    def _go_to_date(self, day):
        self._sync_today()
        self.view_date = min(day, self.today)
        self._show("Overview")
        self._refresh()

    def _refresh(self):
        self._sync_today()
        try:
            stats = data_source.get_day(self.view_date)
            demo = data_source.mode() == "mock"
            self.home_tab.render(stats)
            self.apps_tab.render(stats)
            self.sessions_tab.render(stats)
            self.week_tab.render(data_source.last_n_days(7))
            self.status.configure(
                text=("Preview · Sample data. Start the tracker from the system tray to record your usage."
                      if demo else "Saved on this device · Refreshes every 30 seconds"),
                fg=MUTED)
        except Exception:
            log.exception("Dashboard refresh failed")
            self.status.configure(
                text="Could not load usage. Select Refresh to try again.",
                fg="#9C352B")
        self.date_lbl.configure(
            text="Last 7 days" if self._selected == "Weekly" else self._date_text())
        self.btn_next.configure(
            state="disabled" if self.view_date >= self.today else "normal")

    def _auto_refresh(self):
        self._refresh_job = self.after(30000, self._on_refresh_timer)

    def _on_refresh_timer(self):
        self._refresh()
        self._auto_refresh()

    def _close(self):
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
        self.destroy()
