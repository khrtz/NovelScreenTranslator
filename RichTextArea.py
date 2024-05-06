import tkinter as tk
from tkinter import font, ttk

BG_COLOR = "#E0E5EC"
FG_COLOR = "#000000"
ACCENT_COLOR = "#007ACC"
BUTTON_BG_COLOR = "#C9D1D9"
BUTTON_FG_COLOR = "#000000"
BUTTON_ACTIVE_BG_COLOR = "#A7B0B8"
ENTRY_BG_COLOR = "#FFFFFF"
TEXT_BG_COLOR = "#FFFFFF"
TEXT_FG_COLOR = "#000000"
SHADOW_COLOR = "#D1D9E6"
class RichTextArea(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack(fill=tk.BOTH, expand=True)

        self.create_background()

        self.text_frame = tk.Frame(self, bg=TEXT_BG_COLOR, bd=0, highlightthickness=0)
        self.text_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, relheight=0.7)

        self.text_area = tk.Text(self.text_frame, font=("Yu Gothic UI", 18), wrap=tk.WORD, bg=TEXT_BG_COLOR, fg=TEXT_FG_COLOR,
                                 padx=30, pady=30, highlightthickness=0, bd=0, relief=tk.FLAT, spacing2=10)
        self.text_area.pack(fill=tk.BOTH, expand=True)

        self.text_area.tag_configure("bold", font=("Yu Gothic UI", 18, "bold"))
        self.text_area.tag_configure("italic", font=("Yu Gothic UI", 18, "italic"))
        self.text_area.tag_configure("underline", font=("Yu Gothic UI", 18, "underline"))
        self.text_area.tag_configure("name", foreground=ACCENT_COLOR, font=("Yu Gothic UI", 18, "bold"))

        self.create_name_box()

        self.text_area.tag_configure("gradient", foreground=TEXT_FG_COLOR, elide=True)
        self.text_area.tag_configure("gradient1", foreground=ACCENT_COLOR)
        self.text_area.tag_configure("gradient2", foreground=BUTTON_BG_COLOR)

        self.text_area.tag_configure("glow", font=("Yu Gothic UI", 18, "overstrike"))
        self.text_area.tag_configure("shadow", foreground=SHADOW_COLOR, font=("Yu Gothic UI", 18))

        self.effect_canvas = tk.Canvas(self.text_frame, bg=TEXT_BG_COLOR, highlightthickness=0)
        self.effect_canvas.pack(fill=tk.BOTH, expand=True)

        self.text_scrollbar = ttk.Scrollbar(self.text_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        self.text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.config(yscrollcommand=self.text_scrollbar.set)

    def clear_text(self):
        self.text_area.delete('1.0', tk.END)

    def animate_text(self, text, delay=10):
        self.text_area.delete('1.0', tk.END)
        for i in range(len(text)):
            self.text_area.insert(tk.END, text[i])
            self.text_area.see(tk.END)
            self.update()
            self.after(delay)

    def create_background(self):
        self.bg_canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.bg_canvas.pack(fill=tk.BOTH, expand=True)

        width, height = self.bg_canvas.winfo_width(), self.bg_canvas.winfo_height()
        for x in range(0, width, 20):
            for y in range(0, height, 28):
                self.bg_canvas.create_oval(x, y, x + 10, y + 10, fill=SHADOW_COLOR, outline="")

        self.bg_canvas.bind("<Configure>", self.redraw_background)

    def redraw_background(self, event):
        self.bg_canvas.delete("background")
        width, height = self.bg_canvas.winfo_width(), self.bg_canvas.winfo_height()
        for x in range(0, width, 20):
            for y in range(0, height, 20):
                self.bg_canvas.create_oval(x, y, x + 10, y + 10, fill=SHADOW_COLOR, outline="", tags="background")

    def create_name_box(self):
        self.name_box = tk.Frame(self.text_frame, bg=TEXT_BG_COLOR, bd=0, highlightthickness=0)
        self.name_box.pack(side=tk.TOP, fill=tk.X)

        self.name_label = tk.Label(self.name_box, font=("Yu Gothic UI", 16, "bold"), fg=ACCENT_COLOR, bg=TEXT_BG_COLOR)
        self.name_label.pack(side=tk.LEFT, padx=10)

    def set_name(self, name):
        self.name_label.configure(text=name)

    def append_text(self, text, tags=None):
        self.text_area.insert(tk.END, text, tags)

    def toggle_bold(self):
        self.toggle_style("bold")

    def toggle_italic(self):
        self.toggle_style("italic")

    def toggle_underline(self):
        self.toggle_style("underline")

    def toggle_glow(self):
        self.toggle_style("glow")

    def toggle_shadow(self):
        self.toggle_style("shadow")

    def toggle_style(self, style):
        try:
            current_tags = self.text_area.tag_names(tk.SEL_FIRST)
            if style in current_tags:
                self.text_area.tag_remove(style, tk.SEL_FIRST, tk.SEL_LAST)
            else:
                self.text_area.tag_add(style, tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass

    def apply_text_effect(self, event):
        if not self.text_area.tag_ranges("sel"):
            return

        start, end = self.text_area.tag_ranges("sel")
        self.effect_canvas.delete("effect")

        for x in range(start, end):
            x1, y1, x2, y2 = self.text_area.bbox(x)
            if x1 is None or y1 is None or x2 is None or y2 is None:
                continue

            x1, y1 = self.text_area.coords(x)
            x2, y2 = self.text_area.coords(f"{x} + 1c")

            x1, y1 = self.text_area.bbox(x)[0], self.text_area.bbox(x)[1]
            x2, y2 = self.text_area.bbox(f"{x} + 1c")[2], self.text_area.bbox(f"{x} + 1c")[3]

            self.effect_canvas.create_line(x1, y1, x2, y2, fill=ACCENT_COLOR, width=2, tags="effect", smooth=True)