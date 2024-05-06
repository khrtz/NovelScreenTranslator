import tkinter as tk
from tkinter import Toplevel, Canvas, ttk
from PIL import ImageGrab, ImageTk, Image
import pytesseract
import requests
import ctypes
from ctypes import wintypes, windll
import config
import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from RichTextArea import RichTextArea

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

def set_dpi_awareness():
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except AttributeError:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)

def get_cursor_position():
    point = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y

def select_region(root):
    set_dpi_awareness()
    canvas = Canvas(root, cursor="cross", bg="black", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    rect_id = canvas.create_rectangle(0, 0, 0, 0, outline=ACCENT_COLOR, width=2, dash=(4, 4))

    region = [None, None, None, None]
    dragging = False

    def on_mouse_down(event):
        nonlocal dragging
        region[:2] = get_cursor_position()
        region[2:] = region[:2]
        dragging = True

    def on_mouse_move(event):
        if dragging:
            region[2:] = get_cursor_position()
            canvas.coords(rect_id, *region)

    def on_mouse_up(event):
        nonlocal dragging
        if dragging:
            dragging = False
            region[2:] = get_cursor_position()
            root.quit()

    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_move)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)

    root.mainloop()
    return region

def translate_text(text, target_lang="JA", context_before="", context_after=""):
    if not text.strip():
        return text

    url = "https://api-free.deepl.com/v2/translate"
    params = {
        "auth_key": config.DEEPL_API_KEY,
        "text": context_before + text + context_after,
        "target_lang": target_lang,
        "split_sentences": "1",
        "formality": "prefer_more"
    }
    response = requests.post(url, data=params)
    if response.status_code == 200:
        translations = response.json()['translations']
        translated_sentences = [t['text'] for t in translations]
        return "".join(translated_sentences)
    else:
        print("Failed to translate:", response.text)
        return "Translation failed."

def create_selection_window():
    root = Toplevel()
    root.attributes('-alpha', 0.3)
    root.attributes('-fullscreen', True)
    root.wait_visibility(root)
    root.wm_attributes('-topmost', 1)
    return root

def load_settings():
    if os.path.exists("settings.json"):
        with open("settings.json", "r") as f:
            return json.load(f)
    else:
        return {"regions": [None, None, None], "auto_translate": [False, False, False], "interval": 1}

def save_settings(settings):
    with open("settings.json", "w") as f:
        json.dump(settings, f)

def create_round_rectangle(canvas, x1, y1, x2, y2, radius=25, **kwargs):
    points = [x1 + radius, y1,
              x1 + radius, y1,
              x2 - radius, y1,
              x2 - radius, y1,
              x2, y1,
              x2, y1 + radius,
              x2, y1 + radius,
              x2, y2 - radius,
              x2, y2 - radius,
              x2, y2,
              x2 - radius, y2,
              x2 - radius, y2,
              x1 + radius, y2,
              x1 + radius, y2,
              x1, y2,
              x1, y2 - radius,
              x1, y2 - radius,
              x1, y1 + radius,
              x1, y1 + radius,
              x1, y1]

    return canvas.create_polygon(points, **kwargs, smooth=True)

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

class ScreenTranslator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Screen Text Translator")
        self.configure(bg=BG_COLOR)
        self.highlight_windows = [None] * 3

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", font=("Segoe UI", 12), background=BG_COLOR, foreground=FG_COLOR)
        style.configure("AccentLabel.TLabel", font=("Segoe UI", 14, "bold"), background=BG_COLOR, foreground=ACCENT_COLOR)
        style.configure("TCheckbutton", font=("Segoe UI", 12), background=BG_COLOR, foreground=FG_COLOR)
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TEntry", fieldbackground=ENTRY_BG_COLOR, foreground=FG_COLOR, padding=5)
        style.configure("Text", font=("Yu Gothic UI", 12), background=TEXT_BG_COLOR, foreground=TEXT_FG_COLOR,
                        borderwidth=0, highlightthickness=1, highlightcolor=ACCENT_COLOR, highlightbackground=BG_COLOR,
                        padx=10, pady=10)

        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        result_frame = ttk.Frame(main_frame)
        result_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.settings = load_settings()
        self.regions = self.settings["regions"]
        self.auto_translate_vars = [tk.IntVar(value=int(x)) for x in self.settings.get("auto_translate", [False, False, False])]
        self.interval_var = tk.IntVar(value=max(self.settings.get("interval", 1), 1))

        self.result_labels = []
        self.result_texts = []
        self.translated_text_boxes = []
        self.region_buttons = []

        for i in range(3):
            frame = ttk.Frame(result_frame, padding=15)
            frame.pack(pady=10, fill=tk.X)

            label_frame = ttk.Frame(frame)
            label_frame.pack(side=tk.LEFT, padx=10)

            label = ttk.Label(label_frame, text=f"選択範囲 {i + 1}", anchor="w", style="AccentLabel.TLabel")
            label.pack(side=tk.TOP)
            label.bind("<Button-1>", lambda event, index=i: self.highlight_selected_region(index))

            auto_translate_check = ttk.Checkbutton(label_frame, text="自動翻訳", variable=self.auto_translate_vars[i])
            auto_translate_check.pack(side=tk.BOTTOM, pady=5)

            text_frame = ttk.Frame(frame)
            text_frame.pack(side=tk.LEFT, padx=6, fill=tk.BOTH, expand=True)

            text_box = tk.Text(text_frame, height=4, wrap=tk.WORD, borderwidth=0, highlightthickness=1,
                               highlightcolor=ACCENT_COLOR, highlightbackground=BG_COLOR)
            text_box.pack(fill=tk.BOTH, expand=True, pady=5)

            translated_text_box = tk.Text(text_frame, height=4, wrap=tk.WORD, state="disabled", borderwidth=0,
                                          highlightthickness=1, highlightcolor=ACCENT_COLOR, highlightbackground=BG_COLOR)
            translated_text_box.pack(fill=tk.BOTH, expand=True, pady=5)

            self.result_labels.append(label)
            self.result_texts.append(text_box)
            self.translated_text_boxes.append(translated_text_box)

            button_frame = ttk.Frame(frame)
            button_frame.pack(side=tk.LEFT, padx=10)

            register_button = ClayButton(button_frame, text="登録", command=lambda index=i: self.register_region(index))
            register_button.pack(side=tk.TOP, pady=5)

            translate_button = ClayButton(button_frame, text="翻訳", command=lambda index=i: self.translate_region(index))
            translate_button.pack(side=tk.BOTTOM, pady=5)

            self.region_buttons.append((register_button, translate_button))

        interval_frame = ttk.Frame(main_frame)
        interval_frame.pack(pady=15, fill=tk.X)

        interval_label = ttk.Label(interval_frame, text="自動翻訳の間隔 (秒):")
        interval_label.pack(side=tk.LEFT)

        interval_entry = ttk.Entry(interval_frame, textvariable=self.interval_var, width=5)
        interval_entry.pack(side=tk.LEFT, padx=10)

        self.minsize(800, 650)
        self.auto_translate_thread = None
        self.after(100, self.start_auto_translate)

    def highlight_selected_region(self, index):
        region = self.regions[index]
        if region:
            x1, y1, x2, y2 = region
            highlight_window = Toplevel(self)
            highlight_window.overrideredirect(True)
            highlight_window.attributes("-topmost", True)
            highlight_window.geometry(f"{x2 - x1}x{y2 - y1}+{x1}+{y1}")
            highlight_window.configure(background="")

            canvas = tk.Canvas(highlight_window, highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)

            def animate_highlight():
                alpha = 0.5
                while alpha > 0:
                    canvas.delete("all")
                    canvas.create_rectangle(0, 0, x2 - x1, y2 - y1, fill=ACCENT_COLOR, outline="", stipple="gray50")
                    highlight_window.attributes("-alpha", alpha)
                    highlight_window.update()
                    alpha -= 0.02
                    time.sleep(0.01)
                highlight_window.destroy()

            highlight_window.after(0, animate_highlight)

    def highlight_region(self, region, translated_text):
        if not hasattr(self, 'rich_text_area'):
            self.rich_text_area = RichTextArea(self)
            self.rich_text_area.pack(fill=tk.BOTH, expand=True)

        self.rich_text_area.clear_text()
        self.rich_text_area.animate_text(translated_text)

    def register_region(self, index):
        selection_window = create_selection_window()
        selected_region = select_region(selection_window)
        selection_window.destroy()

        if all(selected_region):
            self.regions[index] = selected_region
            self.save_settings()

    def get_context(self, index, text):
        context_before = ""
        context_after = ""

        if index > 0:
            context_before = self.result_texts[index - 1].get("1.0", tk.END).strip()

        if index < len(self.result_texts) - 1:
            context_after = self.result_texts[index + 1].get("1.0", tk.END).strip()

        return context_before, context_after

    def translate_region(self, index):
        region = self.regions[index]
        if region:
            x1, y1, x2, y2 = region
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            text = pytesseract.image_to_string(screenshot, lang='eng')
            context_before, context_after = self.get_context(index, text)
            translated_text = translate_text(text, context_before=context_before, context_after=context_after)
            self.result_texts[index].delete('1.0', tk.END)
            self.result_texts[index].insert('1.0', text)
            self.translated_text_boxes[index].configure(state="normal")
            self.translated_text_boxes[index].delete('1.0', tk.END)
            self.translated_text_boxes[index].insert('1.0', translated_text)
            self.translated_text_boxes[index].configure(state="disabled")

            self.highlight_region(region, translated_text)

    def start_auto_translate(self):
        if self.auto_translate_thread is None or not self.auto_translate_thread.is_alive():
            self.auto_translate_thread = threading.Thread(target=self.auto_translate_regions, daemon=True)
            self.auto_translate_thread.start()
        self.after(100, self.start_auto_translate)

    def update_texts(self, i, new_text, translated_text):
        self.result_texts[i].delete('1.0', tk.END)
        self.result_texts[i].insert('1.0', new_text)
        self.translated_text_boxes[i].configure(state="normal")
        self.translated_text_boxes[i].delete('1.0', tk.END)
        self.translated_text_boxes[i].insert('1.0', translated_text)
        self.translated_text_boxes[i].configure(state="disabled")
        print(f"選択範囲 {i + 1}: 自動翻訳完了 (間隔: {self.interval_var.get()}秒)")

    def auto_translate_regions(self):
        last_texts = [""] * 3
        while True:
            with ThreadPoolExecutor() as executor:
                futures = []
                for i, region in enumerate(self.regions):
                    if self.auto_translate_vars[i].get() and region:
                        x1, y1, x2, y2 = region
                        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                        new_text = pytesseract.image_to_string(screenshot, lang='eng').strip().replace("\n", " ")

                        if new_text and new_text != last_texts[i]:
                            context_before, context_after = self.get_context(i, new_text)
                            future = executor.submit(translate_text, new_text, context_before=context_before,
                                                     context_after=context_after)
                            futures.append((i, new_text, future))
                            last_texts[i] = new_text
                        elif not new_text:
                            pass
                        else:
                            pass

                for i, new_text, future in futures:
                    translated_text = future.result()
                    self.after_idle(self.update_texts, i, new_text, translated_text)
                    self.highlight_region(self.regions[i], translated_text)

            time.sleep(max(self.interval_var.get(), 5))

    def save_settings(self):
        settings = {
            "regions": self.regions,
            "auto_translate": [var.get() for var in self.auto_translate_vars],
            "interval": self.interval_var.get()
        }
        with open("settings.json", "w") as f:
            json.dump(settings, f)

if __name__ == "__main__":
    app = ScreenTranslator()
    app.mainloop()