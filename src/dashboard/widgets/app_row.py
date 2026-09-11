"""One row in the Top Apps list: color dot, name, time, progress bar."""

import tkinter as tk

from src.utils.time_format import fmt_hm


class AppRow(tk.Frame):
    BG = "#141a28"
    FG = "#eaf0ff"
    SUB = "#8b93a7"
    TRACK = "#1c2333"

    def __init__(self, master, name: str, process: str, color: str,
                 seconds: int, frac: float, **kw):
        super().__init__(master, bg=self.BG, **kw)
        frac = max(0.0, min(1.0, frac))
        self.color = color
        self.frac = frac

        top = tk.Frame(self, bg=self.BG)
        top.pack(fill="x", padx=14, pady=(10, 2))

        dot = tk.Canvas(top, width=10, height=10, bg=self.BG,
                        highlightthickness=0)
        dot.create_oval(1, 1, 9, 9, fill=color, width=0)
        dot.pack(side="left")

        tk.Label(top, text=name, bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 11)).pack(side="left", padx=8)
        tk.Label(top, text=process, bg=self.BG, fg=self.SUB,
                 font=("Segoe UI", 9)).pack(side="left", padx=2, pady=(2, 0))
        tk.Label(top, text=fmt_hm(seconds), bg=self.BG, fg=self.FG,
                 font=("Segoe UI Semibold", 11)).pack(side="right")

        self.bar = tk.Canvas(self, height=6, bg=self.BG,
                             highlightthickness=0)
        self.bar.pack(fill="x", padx=14, pady=(0, 10))
        self.bar.bind("<Configure>", lambda e: self._draw_bar())
        self.bind("<Configure>", lambda e: self._draw_bar())

    def _draw_bar(self) -> None:
        self.bar.delete("all")
        w = max(self.bar.winfo_width(), 10)
        h = 6
        self.bar.create_rectangle(0, 0, w, h, fill=self.TRACK, width=0)
        if self.frac > 0:
            self.bar.create_rectangle(0, 0, int(w * self.frac), h,
                                      fill=self.color, width=0)

