"""Main dashboard window: header (date nav) + tabview (Home/Apps/Sessions)."""

import tkinter as tk
from datetime import date, timedelta

import customtkinter as ctk

from src.dashboard import data_source
from src.dashboard.apps_tab import AppsTab
from src.dashboard.home_tab import HomeTab
from src.dashboard.sessions_tab import SessionsTab
from src.dashboard.week_tab import WeekTab
from src.utils.time_format import fmt_hm

BG = "#0f1420"
CARD = "#141a28"
FG = "#eaf0ff"
SUB = "#8b93a7"
ACCENT = "#4fc3f7"


class DigitalWellbeingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Digital Wellbeing")
        self.geometry("920x640")
        self.minsize(860, 600)
        self.configure(fg_color=BG)

        self.today = date.today()
        self.view_date = self.today

        self._build_header()
        self._build_tabs()
        self._refresh()

    # ---------------------------------------------------------------- UI ---
    def _build_header(self) -> None:
        header = tk.Frame(self, bg=CARD)
        header.pack(fill="x")

        left = tk.Frame(header, bg=CARD)
        left.pack(side="left", padx=20, pady=12)

        tk.Label(left, text="Digital Wellbeing", bg=CARD, fg=FG,
                 font=("Segoe UI Semibold", 15)).pack(side="left")
        self.today_chip = tk.Label(left, bg=CARD, fg=ACCENT,
                                   text="", font=("Segoe UI", 10))
        self.today_chip.pack(side="left", padx=(12, 0), pady=(4, 0))

        right = tk.Frame(header, bg=CARD)
        right.pack(side="right", padx=20, pady=10)

        self.btn_prev = tk.Button(
            right, text="<", width=3, relief="flat", cursor="hand2",
            bg=CARD, fg=FG, activebackground="#1c2333", activeforeground=FG,
            font=("Segoe UI", 11, "bold"), bd=0,
            command=lambda: self._shift_date(-1))
        self.btn_prev.pack(side="left", padx=(0, 6))

        self.date_lbl = tk.Label(right, bg=CARD, fg=FG, width=22,
                                 font=("Segoe UI Semibold", 11))
        self.date_lbl.pack(side="left")

        self.btn_next = tk.Button(
            right, text=">", width=3, relief="flat", cursor="hand2",
            bg=CARD, fg=FG, activebackground="#1c2333", activeforeground=FG,
            font=("Segoe UI", 11, "bold"), bd=0,
            command=lambda: self._shift_date(+1))
        self.btn_next.pack(side="left", padx=(6, 0))

        self.btn_today = tk.Button(
            right, text="Today", relief="flat", cursor="hand2", bd=0,
            bg=ACCENT, fg="#06263a", activebackground="#7ad4ff",
            font=("Segoe UI Semibold", 10), padx=14,
            command=self._go_today)
        self.btn_today.pack(side="left", padx=(12, 0), ipady=4)

    def _build_tabs(self) -> None:
        self.tabs = ctk.CTkTabview(
            self, fg_color=BG,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT,
            segmented_button_unselected_color=CARD,
            segmented_button_unselected_hover_color="#1c2333",
            text_color=FG)
        self.tabs.pack(fill="both", expand=True, padx=0, pady=0)
        self.tabs._segmented_button.configure(
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))

        home = self.tabs.add("Home")
        apps = self.tabs.add("Apps")
        sessions = self.tabs.add("Sessions")
        week = self.tabs.add("Week")
        self.home_tab = HomeTab(home)
        self.apps_tab = AppsTab(apps)
        self.sessions_tab = SessionsTab(sessions)
        self.week_tab = WeekTab(week)
        self.home_tab.pack(fill="both", expand=True)
        self.apps_tab.pack(fill="both", expand=True)
        self.sessions_tab.pack(fill="both", expand=True)
        self.week_tab.pack(fill="both", expand=True)
        self.bind("<Escape>", lambda e: self.destroy())
        self._auto_refresh()

    # ----------------------------------------------------------- actions ---
    def _shift_date(self, days: int) -> None:
        self.view_date += timedelta(days=days)
        self._refresh()

    def _go_today(self) -> None:
        self.view_date = self.today
        self._refresh()

    # ------------------------------------------------------------ render ---
    def _refresh(self) -> None:
        d = self.view_date
        weekday = d.strftime("%A")
        nice = "Today" if d == self.today else d.strftime("%a, %b %d")
        self.date_lbl.config(text=f"{weekday}  •  {nice}")
        future = d > self.today
        self.btn_next.config(state="disabled" if future else "normal")

        stats = data_source.get_day(d)
        self.today_chip.config(
            text=f"{fmt_hm(stats.active_sec)} active"
            if d == self.today else "")
        self.home_tab.render(stats)
        self.apps_tab.render(stats)
        self.sessions_tab.render(stats)
        self.week_tab.render(data_source.last_n_days(7))

    def _auto_refresh(self) -> None:
        """Re-render every 30s so a running tracker updates the view live."""
        try:
            if self.view_date == self.today:
                self._refresh_data_only()
            self.after(30000, self._auto_refresh)
        except Exception:
            self.after(30000, self._auto_refresh)

    def _refresh_data_only(self) -> None:
        stats = data_source.get_day(self.today)
        self.today_chip.config(text=f"{fmt_hm(stats.active_sec)} active")
        self.home_tab.render(stats)
        self.apps_tab.render(stats)
        self.sessions_tab.render(stats)
        # week view is date-independent; refresh it less often (2 min)
        if not hasattr(self, "_next_week"):
            self._next_week = 0
        self._next_week -= 30
        if self._next_week <= 0:
            self.week_tab.render(data_source.last_n_days(7))
            self._next_week = 120
