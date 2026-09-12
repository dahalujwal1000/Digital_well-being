"""Facebook-style pull-to-refresh for the dashboard tabs.

Desktop has no touch, so the gesture is emulated with the mouse wheel:
scrolling UP while the view is already at the very top is an
"overscroll". Two overscroll ticks within ~0.7s trigger a refresh and
show a small "Refreshing…" pill at the top of the visible tab.
F5 also refreshes (bound in app.py).
"""

import time
import tkinter as tk

CARD = "#141a28"
ACCENT = "#4fc3f7"


class PullRefresher:
    TICKS_NEEDED = 2          # wheel-up ticks at the top
    WINDOW_MS = 700           # ...within this window
    COOLDOWN_MS = 2000        # no re-trigger while showing result

    def __init__(self, app, host_fn, refresh_fn):
        self.app = app
        self._host_fn = host_fn          # -> widget to place the pill on
        self._refresh_fn = refresh_fn
        self._ticks: list[float] = []
        self._last = 0.0
        self._busy = False
        self._lbl: tk.Label | None = None
        self._hide_after = None

    # ---- called by the tabs on an overscroll (wheel-up at top) tick ----
    def tick(self) -> None:
        now = time.time() * 1000
        if self._busy or now - self._last < self.COOLDOWN_MS:
            return
        self._ticks = [t for t in self._ticks if now - t <= self.WINDOW_MS]
        self._ticks.append(now)
        if len(self._ticks) >= self.TICKS_NEEDED:
            self._ticks.clear()
            self._go()
        else:
            self._hint()

    # ------------------------------------------------------------ internals
    def _hint(self) -> None:
        self._place("Pull again to refresh")
        if self._hide_after is not None:
            self.app.after_cancel(self._hide_after)
        self._hide_after = self.app.after(900, self._unplace)

    def _go(self) -> None:
        self._busy = True
        self._last = time.time() * 1000
        if self._hide_after is not None:
            self.app.after_cancel(self._hide_after)
            self._hide_after = None
        self._place("Refreshing…")

        def _do():
            try:
                self._refresh_fn()
            finally:
                self._place("Updated ✓")
                self.app.after(650, self._finish)

        self.app.after(350, _do)

    def _finish(self) -> None:
        self._unplace()
        self._busy = False

    def _place(self, text: str) -> None:
        host = self._host_fn()
        if host is None:
            return
        if self._lbl is not None and self._lbl.winfo_exists():
            self._lbl.config(text=text)
            self._lbl.lift()
            return
        self._lbl = tk.Label(host, text=text, bg=CARD, fg=ACCENT,
                             font=("Segoe UI Semibold", 10), padx=14, pady=5)
        self._lbl.place(relx=0.5, y=8, anchor="n")

    def _unplace(self) -> None:
        self._hide_after = None
        if self._lbl is not None and self._lbl.winfo_exists():
            self._lbl.destroy()
        self._lbl = None

    # ------------------------------------------------------------- helpers
    @staticmethod
    def install_on(frame: tk.Misc, refresher: "PullRefresher") -> None:
        """Generic hook for non-scrollable tabs (Home, Week): any wheel-up
        inside `frame` counts as an overscroll tick."""

        def _wheel(event) -> None:
            w = getattr(event, "widget", None)
            while w is not None:
                if w is frame:
                    if int(event.delta / 120) > 0:
                        refresher.tick()
                    return
                w = getattr(w, "master", None)

        frame.bind_all("<MouseWheel>", _wheel, add="+")
