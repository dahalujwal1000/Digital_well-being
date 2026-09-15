"""Hourly stacked bar chart (Active over Idle), drawn on a Canvas.

Interactive: hovering a bar highlights it and shows a tooltip with that
hour's active/idle split.
"""

import tkinter as tk

from src.utils.time_format import fmt_hm, hour_label

HOVER_LIGHTEN = "#7fd7ff"   # active bar when hovered
HOVER_IDLE = "#7a849e"      # idle bar when hovered


class HourlyBarChart(tk.Canvas):
    """24 bars (12a-11p). Bar height = active (solid) + idle (muted) seconds.
    Includes a y-axis with value labels on the gridlines and hover tooltips."""

    def __init__(self, master, bg="#0f1420", active_color="#4fc3f7",
                 idle_color="#5b6379", grid_color="#1a2130",
                 label_fg="#8b93a7"):
        super().__init__(master, height=170, bg=bg, highlightthickness=0)
        self.colors = dict(bg=bg, active=active_color, idle=idle_color,
                           grid=grid_color, label=label_fg)
        self.active, self.idle = [0] * 24, [0] * 24
        self._hover = None          # hour currently hovered
        self._tip = None            # tooltip canvas item id
        self._geo = None            # (pad_l, bar_area, bar_w, pad_t, plot_h)
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", lambda e: self._set_hover(None))

    def set_data(self, active: list[int], idle: list[int]) -> None:
        self.active, self.idle = list(active), list(idle)
        self._draw()

    # ------------------------------------------------------------ drawing --
    def _draw(self) -> None:
        self.delete("all")
        self._tip = None
        w = max(self.winfo_width(), 200)
        h = max(self.winfo_height(), 120)
        c = self.colors
        pad_l, pad_b, pad_t = 52, 22, 10
        plot_h = h - pad_b - pad_t
        plot_w = w - pad_l - 12
        peak = max(1, max(a + i for a, i in zip(self.active, self.idle)))
        bar_area = plot_w / 24
        bar_w = max(4, int(bar_area * 0.62))
        self._geo = (pad_l, bar_area, bar_w, pad_t, plot_h, h, peak)

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
            hovered = self._hover == hour
            act_c = HOVER_LIGHTEN if hovered else c["active"]
            idl_c = HOVER_IDLE if hovered else c["idle"]
            if total > 0:
                h_act = plot_h * a / peak
                h_idl = plot_h * i / peak
                # idle portion (bottom, muted slate)
                if h_idl > 0.5:
                    self.create_rectangle(x, pad_t + plot_h - h_idl,
                                          x + bar_w, pad_t + plot_h,
                                          fill=idl_c, width=0)
                # active portion (top of idle)
                if h_act > 0.5:
                    self.create_rectangle(x, pad_t + plot_h - h_idl - h_act,
                                          x + bar_w, pad_t + plot_h - h_idl,
                                          fill=act_c, width=0)
            # every-2-hour labels
            if hour % 2 == 0:
                lx = pad_l + hour * bar_area + bar_area / 2
                self.create_text(lx, h - pad_b / 2 + 1, text=hour_label(hour),
                                 fill=c["label"], font=("Segoe UI", 8))

    # --------------------------------------------------------- interaction --
    def _hour_at(self, x: int) -> int | None:
        if not self._geo:
            return None
        pad_l, bar_area, bar_w, _, _, _, _ = self._geo
        hour = int((x - pad_l) // bar_area)
        if 0 <= hour < 24 and abs(x - (pad_l + hour * bar_area
                                       + bar_area / 2)) <= bar_area:
            return hour
        return None

    def _on_motion(self, event) -> None:
        if not self._geo:
            return
        pad_l, bar_area, bar_w, pad_t, plot_h, h, peak = self._geo
        if not (pad_t <= event.y <= pad_t + plot_h):
            self._set_hover(None)
            return
        hour = self._hour_at(event.x)
        if hour != self._hover:
            self._set_hover(hour)

    def _set_hover(self, hour: int | None) -> None:
        changed = self._hover != hour
        self._hover = hour
        if changed:
            self._draw()
        self._show_tip(hour)

    def _show_tip(self, hour: int | None) -> None:
        if self._tip is not None:
            self.delete(self._tip)
            self._tip = None
        if hour is None or not self._geo:
            return
        a, i = self.active[hour], self.idle[hour]
        if a + i == 0:
            return
        _, bar_area, _, pad_t, _, _, _ = self._geo
        cx = 52 + hour * bar_area + bar_area / 2
        lines = (f"{hour_label(hour)}\n"
                 f"Active {fmt_hm(a)}   •   Idle {fmt_hm(i)}")
        self._tip = self.create_text(
            cx, pad_t + 4, text=lines, fill="#eaf0ff",
            font=("Segoe UI", 9), anchor="nw", justify="left")

