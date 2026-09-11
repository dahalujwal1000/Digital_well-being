"""Hourly stacked bar chart (Active over Idle), drawn on a Canvas."""

import tkinter as tk

from src.utils.time_format import fmt_hm, hour_label


class HourlyBarChart(tk.Canvas):
    """24 bars (12a-11p). Bar height = active (solid) + idle (muted) seconds.
    Includes a y-axis with value labels on the gridlines."""

    def __init__(self, master, bg="#0f1420", active_color="#4fc3f7",
                 idle_color="#5b6379", grid_color="#1a2130",
                 label_fg="#8b93a7"):
        super().__init__(master, height=170, bg=bg, highlightthickness=0)
        self.colors = dict(bg=bg, active=active_color, idle=idle_color,
                           grid=grid_color, label=label_fg)
        self.active, self.idle = [0] * 24, [0] * 24
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, active: list[int], idle: list[int]) -> None:
        self.active, self.idle = list(active), list(idle)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 200)
        h = max(self.winfo_height(), 120)
        c = self.colors
        pad_l, pad_b, pad_t = 52, 22, 10
        plot_h = h - pad_b - pad_t
        plot_w = w - pad_l - 12
        peak = max(1, max(a + i for a, i in zip(self.active, self.idle)))
        bar_area = plot_w / 24
        bar_w = max(4, int(bar_area * 0.62))

        # horizontal gridlines with time-value labels (4 levels)
        for g in range(5):
            frac = g / 4
            y = pad_t + plot_h - plot_h * frac
            self.create_line(pad_l, y, w - 12, y, fill=c["grid"])
            value = int(peak * frac)
            self.create_text(pad_l - 6, y, text=fmt_hm(value),
                             fill=c["label"], font=("Segoe UI", 8),
                             anchor="e")

        for hour in range(24):
            a = self.active[hour]
            i = self.idle[hour]
            total = a + i
            x = pad_l + hour * bar_area + (bar_area - bar_w) / 2
            if total > 0:
                h_act = plot_h * a / peak
                h_idl = plot_h * i / peak
                # idle portion (bottom, muted slate)
                if h_idl > 0.5:
                    self.create_rectangle(x, pad_t + plot_h - h_idl,
                                          x + bar_w, pad_t + plot_h,
                                          fill=c["idle"], width=0)
                # active portion (top of idle)
                if h_act > 0.5:
                    self.create_rectangle(x, pad_t + plot_h - h_idl - h_act,
                                          x + bar_w, pad_t + plot_h - h_idl,
                                          fill=c["active"], width=0)
            # every-2-hour labels
            if hour % 2 == 0:
                lx = pad_l + hour * bar_area + bar_area / 2
                self.create_text(lx, h - pad_b / 2 + 1, text=hour_label(hour),
                                 fill=c["label"], font=("Segoe UI", 8))

