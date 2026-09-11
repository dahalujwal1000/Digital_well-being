"""Home tab: ring + stat cards (accent-linked) + top-app mini card + chart."""

import tkinter as tk

from src.dashboard.mock_data import DayStats, summary_line
from src.dashboard.widgets.bar_chart import HourlyBarChart
from src.dashboard.widgets.time_ring import TimeRing
from src.dashboard.widgets.tooltip import ToolTip
from src.utils.time_format import fmt_clock, fmt_hm

BG = "#0f1420"
CARD = "#141a28"
FG = "#eaf0ff"
SUB = "#8b93a7"
ACCENT = "#4fc3f7"      # active / ring color
IDLE = "#5b6379"        # muted slate - idle time
NEUTRAL = "#9aa3b8"     # unlocks / neutral metrics


class HomeTab(tk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, bg=BG, **kw)

        # --- top row: ring + stat cards + top-app mini card --------------
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=24, pady=(18, 6))

        self.ring = TimeRing(top, fill=ACCENT)
        self.ring.pack(side="left", padx=(4, 24))

        self.cards = tk.Frame(top, bg=BG)
        self.cards.pack(side="left", fill="both", expand=True)

        self.card_open = self._stat_card(self.cards, "Laptop open",
                                         accent=ACCENT)
        self.card_open.pack(fill="x", pady=(6, 10))
        self.card_idle = self._stat_card(self.cards, "Idle time",
                                         accent=IDLE)
        self.card_idle.pack(fill="x", pady=10)
        self.card_unlocks = self._stat_card(self.cards, "", accent=NEUTRAL)
        self._make_unlocks_title(self.card_unlocks)
        self.card_unlocks.pack(fill="x", pady=10)

        # top-app mini card fills the right column
        self.top_app_card = self._top_app_card(top)
        self.top_app_card.pack(side="left", fill="both", expand=True,
                               padx=(16, 0))

        # --- summary line ------------------------------------------------
        self.summary = tk.Label(self, text="", bg=BG, fg=SUB,
                                font=("Segoe UI", 10), anchor="w")
        self.summary.pack(fill="x", padx=28, pady=(4, 10))

        # --- hourly chart -------------------------------------------------
        chart_card = tk.Frame(self, bg=CARD)
        chart_card.pack(fill="both", expand=True, padx=24, pady=(0, 18))
        tk.Label(chart_card, text="Hourly activity", bg=CARD, fg=SUB,
                 font=("Segoe UI", 10)).pack(anchor="w", padx=14,
                                             pady=(10, 0))
        legend = tk.Frame(chart_card, bg=CARD)
        legend.pack(anchor="w", padx=14, pady=(2, 0))
        for txt, col in (("Active", ACCENT), ("Idle (no input)", IDLE)):
            tk.Frame(legend, bg=col, width=10, height=10).pack(
                side="left", padx=(0, 4))
            tk.Label(legend, text=txt, bg=CARD, fg=SUB,
                     font=("Segoe UI", 9)).pack(side="left", padx=(0, 12))
        self.chart = HourlyBarChart(chart_card, active_color=ACCENT,
                                    idle_color=IDLE)
        self.chart.pack(fill="both", expand=True, padx=10, pady=(4, 12))

    # ------------------------------------------------------------ builders --
    @staticmethod
    def _stat_card(parent, title: str, accent: str) -> tk.Frame:
        """Card with a 3px colored left strip linking it to the ring/chart."""
        card = tk.Frame(parent, bg=CARD)
        strip = tk.Frame(card, bg=accent, width=3)
        strip.pack(side="left", fill="y", padx=(0, 4), pady=2)
        body = tk.Frame(card, bg=CARD)
        body.pack(side="left", fill="both", expand=True)
        title_lbl = tk.Label(body, text=title.upper(), bg=CARD, fg=SUB,
                             font=("Segoe UI", 9))
        title_lbl.pack(anchor="w", padx=12, pady=(10, 0))
        lbl = tk.Label(body, text="", bg=CARD, fg=FG,
                       font=("Segoe UI", 22, "bold"), anchor="w")
        lbl.pack(anchor="w", padx=12, pady=(0, 10))
        card.value_label = lbl
        card.title_lbl = title_lbl
        return card

    @staticmethod
    def _make_unlocks_title(card: tk.Frame) -> None:
        """Rebuild the unlocks card title as 'UNLOCKS (?)' with a tooltip."""
        body = card.winfo_children()[1]
        title_lbl = card.title_lbl
        row = tk.Frame(body, bg=CARD)
        row.pack(anchor="w", padx=12, pady=(10, 0))
        title_lbl.pack_forget()
        title_lbl.config(text="UNLOCKS")
        title_lbl.pack(in_=row, side="left")
        q = tk.Label(row, text="(?)", bg=CARD, fg=SUB,
                     font=("Segoe UI", 9), cursor="hand2")
        q.pack(side="left", padx=(6, 0))
        ToolTip(q, "Times you woke the laptop from the lock screen "
                   "(sign-in / Win+L unlock). Moving the mouse after an "
                   "idle break does not count.")

    @staticmethod
    def _top_app_card(parent) -> tk.Frame:
        card = tk.Frame(parent, bg=CARD)
        tk.Label(card, text="TOP APP TODAY", bg=CARD, fg=SUB,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=14,
                                            pady=(10, 0))
        row = tk.Frame(card, bg=CARD)
        row.pack(anchor="w", padx=14, pady=(6, 2))
        dot = tk.Canvas(row, width=12, height=12, bg=CARD,
                        highlightthickness=0)
        dot.pack(side="left")
        card.dot = dot
        card.name_lbl = tk.Label(row, text="—", bg=CARD, fg=FG,
                                 font=("Segoe UI", 15, "bold"))
        card.name_lbl.pack(side="left", padx=8)
        card.time_lbl = tk.Label(card, text="", bg=CARD, fg=SUB,
                                 font=("Segoe UI", 11), anchor="w")
        card.time_lbl.pack(anchor="w", padx=14, pady=(0, 10))
        card.bar = tk.Canvas(card, height=6, bg=CARD, highlightthickness=0)
        card.bar.pack(fill="x", padx=14, pady=(0, 12))
        card._frac, card._color = 0.0, ACCENT

        def _draw_bar() -> None:
            card.bar.delete("all")
            w = max(card.bar.winfo_width(), 10)
            card.bar.create_rectangle(0, 0, w, 6, fill="#1c2333", width=0)
            if card._frac > 0:
                card.bar.create_rectangle(0, 0, int(w * card._frac), 6,
                                          fill=card._color, width=0)

        card._draw_bar = _draw_bar
        card.bar.bind("<Configure>", lambda e: _draw_bar())
        card.bind("<Configure>", lambda e: _draw_bar())
        _draw_bar()
        return card

    # ------------------------------------------------------------ render ---
    def render(self, stats: DayStats) -> None:
        frac = stats.active_sec / stats.open_sec if stats.open_sec else 0
        # ring sub-text ties the % to the "Laptop open" card
        self.ring.set_data(frac, fmt_hm(stats.active_sec),
                           f"active of {fmt_hm(stats.open_sec)} open")

        self.card_open.value_label.config(text=fmt_hm(stats.open_sec))
        self.card_idle.value_label.config(text=fmt_hm(stats.idle_sec))
        self.card_unlocks.value_label.config(text=str(stats.unlocks))

        # top-app mini card
        card = self.top_app_card
        top = self._top_app(stats)
        if top is not None:
            name, color, sec = top
            pct = round(100 * sec / max(1, stats.active_sec))
            card.name_lbl.config(text=name)
            card.time_lbl.config(text=f"{fmt_hm(sec)}  •  {pct}% of active")
            card._color, card._frac = color, sec / max(1, stats.active_sec)
            card.dot.delete("all")
            card.dot.create_oval(1, 1, 11, 11, fill=color, width=0)
        else:
            card.name_lbl.config(text="—")
            card.time_lbl.config(text="no data")
            card._frac = 0.0
        card._draw_bar()

        self.summary.config(text=f"{summary_line(stats)}   •   "
                                 f"{self._first_last(stats)}")
        self.chart.set_data(stats.hourly_active, stats.hourly_idle)

    # ------------------------------------------------------------ helpers --
    @staticmethod
    def _top_app(stats: DayStats):
        if not stats.apps:
            return None
        a = max(stats.apps, key=lambda app: app.active_sec)
        return a.name, a.color, a.active_sec

    @staticmethod
    def _first_last(stats: DayStats) -> str:
        first = (f"First used {fmt_clock(stats.first_used_sec)}"
                 if stats.first_used_sec is not None else "First used —")
        last = (f"Last used {fmt_clock(stats.last_used_sec)}"
                if stats.last_used_sec is not None else "Last used —")
        return f"{first}   •   {last}"


def _top_app_draw_bar(card: tk.Frame) -> None:
    card.bar.delete("all")
    w = max(card.bar.winfo_width(), 10)
    card.bar.create_rectangle(0, 0, w, 6, fill="#1c2333", width=0)
    if card._frac > 0:
        card.bar.create_rectangle(0, 0, int(w * card._frac), 6,
                                  fill=card._color, width=0)
