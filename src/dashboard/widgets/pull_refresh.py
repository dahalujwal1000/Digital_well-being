"""Facebook-style pull-to-refresh for the dashboard tabs.

Desktop has no touch, so the gesture is emulated with the mouse wheel:
scrolling UP while the view is already at the very top is an
"overscroll". Two overscroll ticks within ~0.7s trigger a refresh.
F5 also refreshes (bound in app.py) with the same animation.

The indicator is a small pill that slides down from the top of the
visible tab: "Pull again to refresh" on the first tick, then
"Refreshing…" with a spinning arc while the refresh runs, then
"Updated ✓" before sliding back up.
"""

import time
import tkinter as tk

CARD = "#141a28"
ACCENT = "#4fc3f7"


class PullRefresher:
    TICKS_NEEDED = 2          # wheel-up ticks at the top
    WINDOW_MS = 700           # ...within this window
    COOLDOWN_MS = 2000        # no re-trigger while showing result
    SPIN_MS = 45              # spinner rotation interval
    STEP_PX = 7               # pill slide pixels per frame
    FRAME_MS = 14             # pill slide frame interval

    def __init__(self, app, host_fn, refresh_fn):
        self.app = app
        self._host_fn = host_fn          # -> widget to place the pill on
        self._refresh_fn = refresh_fn
        self._ticks: list[float] = []
        self._last = 0.0
        self._busy = False
        self._pill: tk.Frame | None = None
        self._lbl: tk.Label | None = None
        self._spinner: tk.Canvas | None = None
        self._spinner_arc = None
        self._y = -50
        self._angle = 0
        self._hide_after = None
        self._spin_job = None
        self._slide_job = None

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

    # ---- F5 path: same animation, triggers immediately ----
    def refresh_now(self) -> None:
        if self._busy:
            return
        self._cancel_hide()
        self._go()

    # ------------------------------------------------------------ internals
    def _hint(self) -> None:
        self._show_pill("Pull again to refresh")
        self._cancel_hide()
        self._hide_after = self.app.after(900, self._hide_pill)

    def _go(self) -> None:
        self._busy = True
        self._last = time.time() * 1000
        self._show_pill("Refreshing…", spinning=True)

        def _do():
            try:
                self._refresh_fn()
            finally:
                self._stop_spin()
                self._show_pill("Updated ✓")
                self.app.after(700, self._finish)

        self.app.after(350, _do)

    def _finish(self) -> None:
        self._hide_pill()
        self._busy = False

    # ------------------------------------------------ pill + animations ---
    def _show_pill(self, text: str, spinning: bool = False) -> None:
        host = self._host_fn()
        if host is None:
            return
        if self._pill is not None and self._pill.winfo_exists():
            self._lbl.config(text=text)
            self._set_spin(spinning)
            return
        self._build_pill(host)
        self._lbl.config(text=text)
        self._set_spin(spinning)
        self._animate_in()

    def _build_pill(self, host) -> None:
        self._pill = tk.Frame(host, bg=CARD)
        self._spinner = tk.Canvas(self._pill, width=16, height=16,
                                  bg=CARD, highlightthickness=0)
        self._spinner_arc = self._spinner.create_arc(
            2, 2, 14, 14, start=0, extent=260, style="arc",
            outline=ACCENT, width=3)
        self._lbl = tk.Label(self._pill, text="", bg=CARD, fg=ACCENT,
                             font=("Segoe UI Semibold", 10))
        self._lbl.pack(side="left", padx=14, pady=6)
        self._y = -50
        self._pill.place(relx=0.5, y=self._y, anchor="n")

    def _animate_in(self) -> None:
        target = 10

        def _step():
            if self._pill is None or not self._pill.winfo_exists():
                return
            if self._y >= target:
                return
            self._y = min(target, self._y + self.STEP_PX)
            self._pill.place(relx=0.5, y=self._y, anchor="n")
            self._slide_job = self.app.after(self.FRAME_MS, _step)

        _step()

    def _hide_pill(self) -> None:
        self._cancel_hide()
        if self._pill is None or not self._pill.winfo_exists():
            self._pill = None
            return

        def _step():
            if self._pill is None or not self._pill.winfo_exists():
                return
            self._y -= self.STEP_PX
            if self._y <= -50:
                self._teardown_pill()
                return
            self._pill.place(relx=0.5, y=self._y, anchor="n")
            self._slide_job = self.app.after(self.FRAME_MS, _step)

        _step()

    def _teardown_pill(self) -> None:
        if self._slide_job is not None:
            try:
                self.app.after_cancel(self._slide_job)
            except Exception:
                pass
            self._slide_job = None
        self._stop_spin()
        if self._pill is not None and self._pill.winfo_exists():
            self._pill.destroy()
        self._pill = self._lbl = self._spinner = None
        self._spinner_arc = None

    # -------------------------------------------------------- spinner -----
    def _set_spin(self, on: bool) -> None:
        if self._spinner is None:
            return
        if on:
            self._spinner.pack(side="left", padx=(12, 0), pady=6,
                               before=self._lbl)
            self._spin()
        else:
            self._spinner.pack_forget()
            self._stop_spin()

    def _spin(self) -> None:
        self._angle = (self._angle - 30) % 360
        if self._spinner is not None and self._spinner.winfo_exists():
            self._spinner.itemconfigure(self._spinner_arc, start=self._angle)
            self._spin_job = self.app.after(self.SPIN_MS, self._spin)

    def _stop_spin(self) -> None:
        if self._spin_job is not None:
            try:
                self.app.after_cancel(self._spin_job)
            except Exception:
                pass
            self._spin_job = None

    def _cancel_hide(self) -> None:
        if self._hide_after is not None:
            try:
                self.app.after_cancel(self._hide_after)
            except Exception:
                pass
            self._hide_after = None

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
