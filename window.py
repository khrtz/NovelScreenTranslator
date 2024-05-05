import tkinter as tk
from tkinter import Toplevel, Canvas, Button, Text, font, Frame, Label, Checkbutton, IntVar
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
    rect_id = canvas.create_rectangle(0, 0, 0, 0, outline="blue", width=2, dash=(2, 2))

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

def main_app():
    main_root = tk.Tk()
    main_root.title("Screen Text Translator")
    app_font = font.Font(family="Helvetica", size=12)

    settings = load_settings()
    regions = settings["regions"]
    auto_translate_vars = [IntVar(value=int(x)) for x in settings.get("auto_translate", [False, False, False])]
    interval_var = IntVar(value=max(settings.get("interval", 1), 1))  # 最小間隔 1秒

    result_frame = Frame(main_root, bg="white", padx=20, pady=20)
    result_frame.pack(side=tk.LEFT, padx=20, pady=20, fill=tk.BOTH, expand=True)

    result_labels = []
    result_texts = []
    translated_text_boxes = []

    for i in range(3):
        frame = Frame(result_frame, bg="white", padx=10, pady=10, bd=1, relief=tk.SOLID)
        frame.pack(pady=10, fill=tk.X)

        label = Label(frame, text=f"選択範囲 {i+1}", font=app_font, bg="white")
        label.pack(side=tk.LEFT)

        auto_translate_checkbox = Checkbutton(frame, text="自動翻訳", variable=auto_translate_vars[i], font=app_font, bg="white")
        auto_translate_checkbox.pack(side=tk.LEFT)

        result_text = Text(frame, height=3, width=40, font=app_font, wrap=tk.WORD)
        result_text.pack(side=tk.LEFT, padx=10)

        translated_text_box = Text(frame, height=3, width=40, font=app_font, wrap=tk.WORD)
        translated_text_box.pack(side=tk.LEFT)

        result_labels.append(label)
        result_texts.append(result_text)
        translated_text_boxes.append(translated_text_box)

    def register_region(index):
        selection_window = create_selection_window()
        selected_region = select_region(selection_window)
        selection_window.destroy()

        if all(selected_region):
            regions[index] = selected_region
            save_settings({"regions": regions, "auto_translate": [var.get() for var in auto_translate_vars], "interval": interval_var.get()})

    def translate_region(index):
        region = regions[index]
        if region:
            x1, y1, x2, y2 = region
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            text = pytesseract.image_to_string(screenshot, lang='eng')
            translated_text = translate_text(text)
            result_texts[index].delete('1.0', tk.END)
            result_texts[index].insert('1.0', text)
            translated_text_boxes[index].delete('1.0', tk.END)
            translated_text_boxes[index].insert('1.0', translated_text)

    def auto_translate_regions():
        def update_texts(i, new_text, translated_text):
            result_texts[i].delete('1.0', tk.END)
            result_texts[i].insert('1.0', new_text)
            translated_text_boxes[i].delete('1.0', tk.END)
            translated_text_boxes[i].insert('1.0', translated_text)
            print(f"選択範囲 {i + 1}: 自動翻訳完了 (間隔: {interval_var.get()}秒)")

        with ThreadPoolExecutor() as executor:
            last_texts = [""] * 3
            while True:
                futures = []
                for i, region in enumerate(regions):
                    if auto_translate_vars[i].get() and region:
                        x1, y1, x2, y2 = region
                        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                        new_text = pytesseract.image_to_string(screenshot, lang='eng').strip().replace("\n", " ")

                        if new_text != last_texts[i]:
                            future = executor.submit(translate_text, new_text)
                            futures.append((i, new_text, future))
                            last_texts[i] = new_text

                for i, new_text, future in futures:
                    translated_text = future.result()
                    main_root.after(0, update_texts, i, new_text, translated_text)

                time.sleep(max(interval_var.get(), 5))

    control_frame = Frame(main_root, bg="white", padx=20, pady=20)
    control_frame.pack(side=tk.RIGHT, padx=20, pady=20, fill=tk.Y)

    for i in range(3):
        button_frame = Frame(control_frame, bg="white")
        button_frame.pack(pady=10, fill=tk.X)

        register_button = Button(button_frame, text=f"選択範囲 {i+1} を登録", command=lambda index=i: register_region(index), font=app_font, bg="gray", fg="white")
        register_button.pack(side=tk.LEFT, padx=5)

        translate_button = Button(button_frame, text=f"選択範囲 {i+1} を翻訳", command=lambda index=i: translate_region(index), font=app_font, bg="gray", fg="white")
        translate_button.pack(side=tk.LEFT)

    interval_frame = Frame(control_frame, bg="white")
    interval_frame.pack(pady=10, fill=tk.X)

    interval_label = Label(interval_frame, text="自動翻訳の間隔 (秒):", font=app_font, bg="white")
    interval_label.pack(side=tk.LEFT)

    interval_entry = tk.Entry(interval_frame, textvariable=interval_var, font=app_font, width=5)
    interval_entry.pack(side=tk.LEFT)

    auto_translate_thread = threading.Thread(target=auto_translate_regions, daemon=True)
    auto_translate_thread.start()

    main_root.mainloop()

if __name__ == "__main__":
    main_app()