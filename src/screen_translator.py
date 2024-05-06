import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab
import pytesseract
import requests
import config
import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from tkinter import Toplevel, Canvas

from services.translation_service import translate_text
from RichTextArea import RichTextArea
from selection_window import SelectionWindow
from services.pytesseract_ocr_service import PytesseractOCRService
from views.clay_button import ClayButton
from config import TEXT_FG_COLOR, BUTTON_BG_COLOR, BUTTON_ACTIVE_BG_COLOR, BUTTON_FG_COLOR, FG_COLOR, ACCENT_COLOR, BG_COLOR, TEXT_BG_COLOR, ENTRY_BG_COLOR
from controllers.settings_controller import SettingsController


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

        self.settings_controller = SettingsController()
        self.settings = self.settings_controller.load_settings()
        self.regions = self.settings.regions
        self.auto_translate_vars = [tk.IntVar(value=int(x)) for x in self.settings.auto_translate]
        self.interval_var = tk.IntVar(value=max(self.settings.interval, 1))
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

    def auto_translate_regions(self):
        last_texts = [""] * 3
        while True:
            with ThreadPoolExecutor() as executor:
                futures = []
                for i, region in enumerate(self.regions):
                    if self.auto_translate_vars[i].get() and region:
                        ocr_service = PytesseractOCRService()
                        new_text, success = ocr_service.get_text_from_region(region)

                        if success and new_text != last_texts[i]:
                            context_before, context_after = self.get_context(i, new_text)
                            future = executor.submit(translate_text, new_text, context_before=context_before,
                                                     context_after=context_after)
                            futures.append((i, new_text, future))
                            last_texts[i] = new_text

                for i, new_text, future in futures:
                    translated_text = future.result()
                    self.after_idle(self.update_texts, i, new_text, translated_text)
                    self.highlight_region(self.regions[i], translated_text)

            time.sleep(max(self.interval_var.get(), 5))


    def start_auto_translate(self):
        if self.auto_translate_thread is None or not self.auto_translate_thread.is_alive():
            self.auto_translate_thread = threading.Thread(target=self.auto_translate_regions, daemon=True)
            self.auto_translate_thread.start()
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
        selection_window = SelectionWindow(self)
        selected_region = selection_window.get_selected_region()

        if all(selected_region):
            self.settings.regions[index] = selected_region
            self.settings_controller.save_settings(self.settings)

    def get_context(self, index, text):
        context_before = ""
        context_after = ""

        if index > 0:
            context_before = self.result_texts[index - 1].get("1.0", tk.END).strip()

        if index < len(self.result_texts) - 1:
            context_after = self.result_texts[index + 1].get("1.0", tk.END).strip()

        return context_before, context_after


    def update_texts(self, i, new_text, translated_text):
        self.result_texts[i].delete('1.0', tk.END)
        self.result_texts[i].insert('1.0', new_text)
        self.translated_text_boxes[i].configure(state="normal")
        self.translated_text_boxes[i].delete('1.0', tk.END)
        self.translated_text_boxes[i].insert('1.0', translated_text)
        self.translated_text_boxes[i].configure(state="disabled")
        print(f"選択範囲 {i + 1}: 自動翻訳完了 (間隔: {self.interval_var.get()}秒)")

    def translate_region(self, index):
        region = self.regions[index]
        if region:
            ocr_service = PytesseractOCRService()
            text, success = ocr_service.get_text_from_region(region)
            if success:
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
                                custom_config = r'--oem 3 --psm 6 -l eng'

                                new_text = pytesseract.image_to_string(screenshot,
                                                                       config=custom_config).strip().replace("\n", " ")

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

if __name__ == "__main__":
    app = ScreenTranslator()
    app.mainloop()