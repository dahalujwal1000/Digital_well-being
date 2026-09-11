"""Non-intrusive hover tooltip for small (?) markers."""

import tkinter as tk


class ToolTip:
    def __init__(self, widget: tk.Widget, text: str, bg="#1c2333",
                 fg="#c7cfdf", delay: int = 400):
        self.widget = widget
        self.text = text
        self.bg, self.fg = bg, fg
        self.delay = delay
        self._after_id = None
        self._tip = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self) -> None:
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self) -> None:
        if self._tip:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 6
        y = self.widget.winfo_rooty() + self.widget.winfo_height() // 2 - 12
        self._tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, bg=self.bg, fg=self.fg,
                 font=("Segoe UI", 9), justify="left", padx=10, pady=6,
                 wraplength=220).pack()

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._tip:
            self._tip.destroy()
            self._tip = None
