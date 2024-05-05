import tkinter as tk
from tkinter import Toplevel, Canvas, Button, Text, font
from PIL import ImageGrab
import pytesseract
import requests
import ctypes
from ctypes import wintypes, windll
import config

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
    url = "https://api-free.deepl.com/v2/translate"
    params = {
        "auth_key": config.DEEPL_API_KEY,
        "text": text,
        "target_lang": target_lang
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

def main_app():
    main_root = tk.Tk()
    main_root.title("Screen Text Translator")
    app_font = font.Font(family="Helvetica", size=12)

    result_text = Text(main_root, height=5, width=50, font=app_font)
    translated_text_box = Text(main_root, height=5, width=50, font=app_font)
    result_text.pack(pady=20)
    translated_text_box.pack(pady=20)

    select_button = Button(main_root, text="範囲を選択", command=lambda: start_selection(), font=app_font, bg="gray", fg="white")
    select_button.pack(pady=20, ipadx=10, ipady=5)

    def start_selection():
        selection_window = create_selection_window()
        selected_region = select_region(selection_window)
        selection_window.destroy()

        if all(selected_region):
            x1, y1, x2, y2 = selected_region
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            original_text = pytesseract.image_to_string(screenshot, lang='eng+chi_sim+chi_tra')
            translated_text = translate_text(original_text)
            result_text.delete('1.0', tk.END)
            result_text.insert('1.0', original_text)
            translated_text_box.delete('1.0', tk.END)
            translated_text_box.insert('1.0', translated_text)

    main_root.mainloop()

if __name__ == "__main__":
    main_app()
