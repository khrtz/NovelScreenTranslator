import tkinter as tk
from tkinter import ttk
from views.clay_button import ClayButton
from views.selection_window import SelectionWindow
from views.rich_text_area import RichTextArea

class ResultFrame(ttk.Frame):
    def __init__(self, master, settings, ocr_controller, translation_controller):
        super().__init__(master, padding=10)
        self.settings = settings
        self.ocr_controller = ocr_controller
        self.translation_controller = translation_controller
        self.result_labels = []
        self.result_texts = []
        self.translated_text_boxes = []
        self.auto_translate_vars = [tk.IntVar(value=int(x)) for x in settings.auto_translate]

        for i in range(3):
            self.create_result_section(i)

    def create_result_section(self, i):
        frame = ttk.Frame(self, padding=15)
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
                           highlightcolor="#007ACC", highlightbackground="#E0E5EC")
        text_box.pack(fill=tk.BOTH, expand=True, pady=5)

        translated_text_box = tk.Text(text_frame, height=4, wrap=tk.WORD, state="disabled", borderwidth=0,
                                      highlightthickness=1, highlightcolor="#007ACC", highlightbackground="#E0E5EC")
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

    def highlight_selected_region(self, index):
        region = self.settings.regions[index]
        if region:
            x1, y1, x2, y2 = region
            highlight_window = SelectionWindow(self.master, region)
            highlight_window.highlight_region()

    def register_region(self, index):
        selection_window = SelectionWindow(self.master)
        selected_region = selection_window.get_selected_region()

        if all(selected_region):
            self.settings.regions[index] = selected_region

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
        print(f"選択範囲 {i + 1}: 自動翻訳完了 (間隔: {self.master.interval_frame.interval_var.get()}秒)")

    def translate_region(self, index):
        region = self.settings.regions[index]
        if region:
            text, success = self.ocr_controller.get_text_from_region(region)
            if success:
                context_before, context_after = self.get_context(index, text)
                translated_text = self.translation_controller.translate_text(text, context_before=context_before,
                                                                             context_after=context_after)
                self.result_texts[index].delete('1.0', tk.END)
                self.result_texts[index].insert('1.0', text)
                self.translated_text_boxes[index].configure(state="normal")
                self.translated_text_boxes[index].delete('1.0', tk.END)
                self.translated_text_boxes[index].insert('1.0', translated_text)
                self.translated_text_boxes[index].configure(state="disabled")

                rich_text_area = RichTextArea(self.master)
                rich_text_area.animate_text(translated_text)