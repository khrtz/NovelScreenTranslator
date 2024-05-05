import tkinter as tk
from tkinter import Toplevel, Canvas, ttk
from PIL import ImageGrab
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

DEFAULT_FONT = ("Helvetica", 12)
BG_COLOR = "#272727"
FG_COLOR = "#DDDDDD"
ACCENT_COLOR = "#0AB8A3"
BUTTON_FG_COLOR = "#FFFFFF"

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
    rect_id = canvas.create_rectangle(0, 0, 0, 0, outline=ACCENT_COLOR, width=2, dash=(2, 2))

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

def translate_text(text, target_lang="JA"):
    if not text.strip():
        return text

    url = "https://api-free.deepl.com/v2/translate"
    params = {
        "auth_key": config.DEEPL_API_KEY,
        "text": text,
        "target_lang": target_lang,
        "split_sentences": "0",
        "formality": "prefer_more"
    }
    response = requests.post(url, data=params)
    if response.status_code == 200:
        return response.json()['translations'][0]['text']
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

class ScreenTranslator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Screen Text Translator")
        self.configure(bg=BG_COLOR)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", font=DEFAULT_FONT, background=BG_COLOR, foreground=FG_COLOR)
        style.configure("TCheckbutton", font=DEFAULT_FONT, background=BG_COLOR, foreground=FG_COLOR)
        style.configure("TButton", font=DEFAULT_FONT, padding=8, foreground=BUTTON_FG_COLOR, background=BG_COLOR)
        style.map("TButton", foreground=[("active", ACCENT_COLOR)], background=[("active", BG_COLOR)])
        style.configure("TFrame", background=BG_COLOR)
        style.configure("TEntry", fieldbackground=BG_COLOR, foreground=FG_COLOR)
        style.configure("Text", background=BG_COLOR, foreground=FG_COLOR)

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
            frame = ttk.Frame(result_frame, padding=10, borderwidth=1, relief="solid")
            frame.pack(pady=10, fill=tk.X)

            label = ttk.Label(frame, text=f"選択範囲 {i+1}", anchor="w")
            label.pack(side=tk.LEFT, padx=5)

            auto_translate_check = ttk.Checkbutton(frame, text="自動翻訳", variable=self.auto_translate_vars[i])
            auto_translate_check.pack(side=tk.LEFT, padx=5)

            text_box = tk.Text(frame, height=3, width=30, font=DEFAULT_FONT, wrap=tk.WORD, borderwidth=0, highlightthickness=1, highlightcolor=ACCENT_COLOR, bg=BG_COLOR, fg=FG_COLOR)
            text_box.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)

            translated_text_box = tk.Text(frame, height=3, width=30, font=DEFAULT_FONT, wrap=tk.WORD, borderwidth=0, highlightthickness=1, highlightcolor=ACCENT_COLOR, state="disabled", bg=BG_COLOR, fg=FG_COLOR)
            translated_text_box.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)

            self.result_labels.append(label)
            self.result_texts.append(text_box)
            self.translated_text_boxes.append(translated_text_box)

            button_frame = ttk.Frame(frame)
            button_frame.pack(side=tk.LEFT, padx=5)

            register_button = ttk.Button(button_frame, text="登録", command=lambda index=i: self.register_region(index))
            register_button.pack(side=tk.TOP, pady=2)

            translate_button = ttk.Button(button_frame, text="翻訳", command=lambda index=i: self.translate_region(index))
            translate_button.pack(side=tk.BOTTOM, pady=2)

            self.region_buttons.append((register_button, translate_button))

        interval_frame = ttk.Frame(main_frame)
        interval_frame.pack(pady=10, fill=tk.X)

        interval_label = ttk.Label(interval_frame, text="自動翻訳の間隔 (秒):")
        interval_label.pack(side=tk.LEFT)

        interval_entry = ttk.Entry(interval_frame, textvariable=self.interval_var, width=5)
        interval_entry.pack(side=tk.LEFT)

        self.minsize(800, 600)
        self.auto_translate_thread = threading.Thread(target=self.auto_translate_regions, daemon=True)
        self.auto_translate_thread.start()

    def register_region(self, index):
        selection_window = create_selection_window()
        selected_region = select_region(selection_window)
        selection_window.destroy()

        if all(selected_region):
            self.regions[index] = selected_region
            self.save_settings()

    def translate_region(self, index):
        region = self.regions[index]
        if region:
            x1, y1, x2, y2 = region
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            text = pytesseract.image_to_string(screenshot, lang='eng')
            translated_text = translate_text(text)
            self.result_texts[index].delete('1.0', tk.END)
            self.result_texts[index].insert('1.0', text)
            self.translated_text_boxes[index].configure(state="normal")
            self.translated_text_boxes[index].delete('1.0', tk.END)
            self.translated_text_boxes[index].insert('1.0', translated_text)
            self.translated_text_boxes[index].configure(state="disabled")

    def auto_translate_regions(self):
        def update_texts(i, new_text, translated_text):
            self.result_texts[i].delete('1.0', tk.END)
            self.result_texts[i].insert('1.0', new_text)
            self.translated_text_boxes[i].configure(state="normal")
            self.translated_text_boxes[i].delete('1.0', tk.END)
            self.translated_text_boxes[i].insert('1.0', translated_text)
            self.translated_text_boxes[i].configure(state="disabled")
            print(f"選択範囲 {i + 1}: 自動翻訳完了 (間隔: {self.interval_var.get()}秒)")

        with ThreadPoolExecutor() as executor:
            last_texts = [""] * 3
            while True:
                futures = []
                for i, region in enumerate(self.regions):
                    if self.auto_translate_vars[i].get() and region:
                        x1, y1, x2, y2 = region
                        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                        new_text = pytesseract.image_to_string(screenshot, lang='eng').strip().replace("\n", " ")

                        if new_text != last_texts[i]:
                            future = executor.submit(translate_text, new_text)
                            futures.append((i, new_text, future))
                            last_texts[i] = new_text

                for i, new_text, future in futures:
                    translated_text = future.result()
                    self.after_idle(update_texts, i, new_text, translated_text)

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