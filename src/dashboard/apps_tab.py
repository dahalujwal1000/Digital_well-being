"""Searchable app and website usage."""
import tkinter as tk
from src.dashboard.theme import (
    Page, label, heading, button, usage_row, BG, SURFACE, TEXT,
    MUTED, ACCENT, TINT, LINE, FONT)
from src.utils.time_format import fmt_hm


class AppsTab(Page):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        heading(self.content, "Where your time goes",
                "Explore the apps and websites you used on the selected day.")
        controls = tk.Frame(self.content, bg=BG)
        controls.pack(fill="x", pady=(0, 14))
        self.kind = "Apps"
        self.buttons = {}
        for name in ("Apps", "Websites"):
            b = button(controls, name, lambda n=name: self._select(n))
            b.pack(side="left", padx=(0, 8))
            self.buttons[name] = b
        self.query = tk.StringVar()
        label(controls, "Search", color=MUTED).pack(side="left", padx=(16, 8))
        self.search = tk.Entry(controls, textvariable=self.query,
                               bg=SURFACE, fg=TEXT, insertbackground=ACCENT,
                               font=(FONT, 11), relief="flat",
                               highlightthickness=1, highlightbackground=LINE,
                               highlightcolor=ACCENT)
        self.search.pack(side="left", fill="x", expand=True, ipady=9)
        self.query.trace_add("write", lambda *_: self._draw())
        self.note = label(self.content, "", color=MUTED, anchor="w",
                           wraplength=620, justify="left")
        self.note.pack(fill="x", pady=(0, 18))
        self.rows = tk.Frame(self.content, bg=BG)
        self.rows.pack(fill="x")
        self.stats = None
        self._select("Apps")

    def _select(self, name):
        self.kind = name
        for key, b in self.buttons.items():
            b.configure(bg=ACCENT if key == name else TINT,
                        fg="white" if key == name else ACCENT)
        self._draw()

    def render(self, stats):
        self.stats = stats
        self._draw()

    def _draw(self):
        if self.stats is None:
            return
        for w in self.rows.winfo_children():
            w.destroy()
        items = self.stats.apps if self.kind == "Apps" else self.stats.websites
        total = sum(a.active_sec for a in items)
        self.note.configure(text=(
            f"{fmt_hm(total)} recorded across {len(items)} apps"
            if self.kind == "Apps" else
            "Website estimates come from browser window titles and are part of browser time."))
        matches = [a for a in items if self.query.get().casefold() in a.name.casefold()]
        for item in sorted(matches, key=lambda a: a.active_sec, reverse=True):
            usage_row(self.rows, item.name, item.active_sec,
                      item.active_sec/max(1, total))
        if not matches:
            label(self.rows, "No matching results." if self.query.get()
                  else "No usage recorded for this day.", color=MUTED).pack(
                      anchor="w", pady=28)
