"""Circular progress ring showing today's active screen time."""

import tkinter as tk


class TimeRing(tk.Canvas):
    """Digital-Wellbeing style ring: colored arc = active share of open time."""

    def __init__(self, master, size: int = 210, ring_width: int = 16,
                 bg="#0f1420", track="#1c2333", fill="#4fc3f7",
                 text_fg="#eaf0ff", sub_fg="#8b93a7"):
        super().__init__(master, width=size, height=size,
                         bg=bg, highlightthickness=0)
        self.size = size
        self.center = size / 2
        self.radius = (size - ring_width) / 2 - 2
        self.ring_width = ring_width
        self.track, self.fill = track, fill
        self.text_fg, self.sub_fg = text_fg, sub_fg
        self._frac, self._main, self._sub = 0.0, "", ""

    def set_data(self, fraction: float, main_text: str, sub_text: str) -> None:
        self._frac = max(0.0, min(1.0, fraction))
        self._main, self._sub = main_text, sub_text
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        c, r, w = self.center, self.radius, self.ring_width
        # track
        self.create_oval(c - r, c - r, c + r, c + r,
                         outline=self.track, width=w)
        # colored arc (starts at top, clockwise)
        if self._frac > 0:
            span = -360 * self._frac
            self.create_arc(c - r, c - r, c + r, c + r, start=90, extent=span,
                            outline=self.fill, width=w,
                            style="arc")
        # center texts
        self.create_text(c, c - 10, text=self._main, fill=self.text_fg,
                         font=("Segoe UI", 22, "bold"))
        self.create_text(c, c + 18, text=self._sub, fill=self.sub_fg,
                         font=("Segoe UI", 11))
