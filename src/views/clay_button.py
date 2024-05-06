
from tkinter import ttk

from config import BUTTON_BG_COLOR, BUTTON_ACTIVE_BG_COLOR, BUTTON_FG_COLOR


class ClayButton(ttk.Button):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(style="Clay.TButton")

        style = ttk.Style()
        style.configure("Clay.TButton",
                        background=BUTTON_BG_COLOR,
                        foreground=BUTTON_FG_COLOR,
                        borderwidth=0,
                        focusthickness=0,
                        font=("Segoe UI", 12),
                        padding=10)
        style.map("Clay.TButton",
                  background=[("active", BUTTON_ACTIVE_BG_COLOR)],
                  foreground=[("active", BUTTON_FG_COLOR)])
