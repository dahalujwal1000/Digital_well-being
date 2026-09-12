"""Apps tab: per-app time list, Android-Dashboard style."""

import tkinter as tk

from src.dashboard.mock_data import DayStats
from src.dashboard.widgets.app_row import AppRow

BG = "#0f1420"
SUB = "#8b93a7"


class AppsTab(tk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, bg=BG, **kw)

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=24, pady=(16, 8))
        tk.Label(header, text="TOP APPS", bg=BG, fg=SUB,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.total_lbl = tk.Label(header, text="", bg=BG, fg=SUB,
                                  font=("Segoe UI", 10))
        self.total_lbl.pack(side="right")

        # scrollable list
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
        # mouse-wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _on_wheel(self, event) -> None:
        # bind_all fires for every scroll event in the app; scroll only if
        # the widget under the mouse belongs to THIS tab's canvas.
        w = getattr(event, "widget", None)
        while w is not None:
            if w is self.canvas:
                self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")
                return
            w = getattr(w, "master", None)

    def render(self, stats: DayStats) -> None:
        for w in self.inner.winfo_children():
            w.destroy()
        total = max(1, sum(a.active_sec for a in stats.apps))
        self.total_lbl.config(text=f"Total active {total // 3600}h "
                                   f"{total % 3600 // 60}m")

        # --- TOP APPS ---
        tk.Label(self.inner, text="TOP APPS", bg=BG, fg=SUB,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))
        for app in stats.apps:
            row = AppRow(self.inner, name=app.name, process=app.process,
                         color=app.color, seconds=app.active_sec,
                         frac=app.active_sec / total)
            row.pack(fill="x", pady=(0, 8))

        # --- TOP WEBSITES (inside browsers) ---
        if stats.websites:
            web_total = max(1, sum(w.active_sec for w in stats.websites))
            tk.Label(self.inner, text="TOP WEBSITES  (inside browsers)",
                     bg=BG, fg=SUB,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w",
                                                        pady=(14, 6))
            for site in stats.websites:
                row = AppRow(self.inner, name=site.name, process="web page",
                             color=site.color, seconds=site.active_sec,
                             frac=site.active_sec / web_total)
                row.pack(fill="x", pady=(0, 8))
