import tkinter as tk
from tkinter import Toplevel, Canvas
import ctypes
from ctypes import wintypes

ACCENT_COLOR = "#007ACC"

class SelectionWindow:
    def __init__(self, parent):
        self.parent = parent
        self.set_dpi_awareness()
        self.root = self.create_selection_window()
        self.canvas = self.create_canvas()
        self.rect_id = self.canvas.create_rectangle(0, 0, 0, 0, outline=ACCENT_COLOR, width=2, dash=(4, 4))
        self.region = [None, None, None, None]
        self.dragging = False
        self.bind_events()

    def set_dpi_awareness(self):
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except AttributeError:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)

    def get_cursor_position(self):
        point = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        return point.x, point.y

    def create_selection_window(self):
        root = Toplevel(self.parent)
        root.attributes('-alpha', 0.3)
        root.attributes('-fullscreen', True)
        root.wait_visibility(root)
        root.wm_attributes('-topmost', 1)
        return root

    def create_canvas(self):
        canvas = Canvas(self.root, cursor="cross", bg="black", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        return canvas

    def bind_events(self):
        def on_mouse_down(event):
            self.region[:2] = self.get_cursor_position()
            self.region[2:] = self.region[:2]
            self.dragging = True

        def on_mouse_move(event):
            if self.dragging:
                self.region[2:] = self.get_cursor_position()
                self.canvas.coords(self.rect_id, *self.region)

        def on_mouse_up(event):
            if self.dragging:
                self.dragging = False
                self.region[2:] = self.get_cursor_position()
                self.root.quit()

        self.canvas.bind("<ButtonPress-1>", on_mouse_down)
        self.canvas.bind("<B1-Motion>", on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", on_mouse_up)

    def get_selected_region(self):
        self.root.mainloop()
        return self.region