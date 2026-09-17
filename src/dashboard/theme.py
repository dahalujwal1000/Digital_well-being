"""Shared desktop visual language inspired by Digital Wellbeing."""
import tkinter as tk

BG = "#F7F9F5"
SURFACE = "#FFFFFF"
TEXT = "#202A25"
MUTED = "#57665D"
ACCENT = "#246B4F"
TINT = "#E3EFE5"
LINE = "#DCE4DB"
IDLE = "#B9C9BF"
FONT = "Segoe UI"


def label(parent, text="", size=11, bold=False, color=TEXT, **kw):
    return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                    font=(FONT, size, "bold" if bold else "normal"), **kw)


def button(parent, text, command, primary=False, **kw):
    return tk.Button(
        parent, text=text, command=command, font=(FONT, 10, "bold"),
        bg=ACCENT if primary else TINT, fg="white" if primary else ACCENT,
        activebackground="#D2E4D7", activeforeground=TEXT,
        relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
        highlightthickness=1, highlightbackground=parent.cget("bg"),
        highlightcolor=ACCENT, takefocus=True, **kw)


def heading(parent, title, subtitle=""):
    label(parent, title, 20, True).pack(anchor="w")
    if subtitle:
        label(parent, subtitle, color=MUTED, wraplength=650,
              justify="left").pack(anchor="w", pady=(6, 18))


class Page(tk.Frame):
    """Scrollable page; wheel events only affect the visible hovered page."""
    def __init__(self, master, **kw):
        super().__init__(master, bg=BG, **kw)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        scroll = tk.Scrollbar(self, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=BG)
        self.window = self.canvas.create_window(0, 0, window=self.body,
                                                anchor="nw")
        self.body.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self.window, width=e.width))
        self.content = tk.Frame(self.body, bg=BG)
        self.content.pack(fill="both", expand=True, padx=28, pady=18)
        self.bind_all("<MouseWheel>", self._wheel, add="+")

    def _wheel(self, event):
        widget = event.widget
        while widget is not None:
            if widget is self:
                if self.body.winfo_height() > self.canvas.winfo_height():
                    self.canvas.yview_scroll(-int(event.delta / 120), "units")
                return
            widget = getattr(widget, "master", None)


def usage_row(parent, name, seconds, fraction, color=ACCENT):
    from src.utils.time_format import fmt_hm
    row = tk.Frame(parent, bg=SURFACE, padx=18, pady=14)
    row.pack(fill="x", pady=(0, 2))
    row.columnconfigure(0, weight=1)
    name_label = label(row, name, 11, True, anchor="w")
    name_label.grid(row=0, column=0, sticky="ew", padx=(0, 16))
    label(row, fmt_hm(seconds), 11, True).grid(row=0, column=1, sticky="e")
    bar = tk.Canvas(row, height=5, bg=TINT, highlightthickness=0)
    bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
    def draw(event):
        bar.delete("all")
        bar.create_rectangle(0, 0, event.width * min(1, max(0, fraction)),
                             5, fill=color, width=0)
        name_label.configure(wraplength=max(100, row.winfo_width() - 160))
    bar.bind("<Configure>", draw)
    return row
