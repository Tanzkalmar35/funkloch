from tkinter import *

# from tkinter import ttk
import tkinter as tk


def _on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def add_message(parent, user_name: str, message: str, left_align: bool):
    bgcolor = "lightblue"  # label does not support transparency

    speech_bubble = tk.Frame(
        parent,
        width=60,
        height=2,
        bg=bgcolor,
    )
    name = tk.Label(
        speech_bubble,
        font=("Arial", 16, "bold"),
        text=user_name,
        bg=bgcolor,
    )
    text_box = tk.Label(
        speech_bubble,
        font=("Arial", 13, "normal"),
        text=message,
        bg=bgcolor,
    )
    name.pack(anchor="w")
    text_box.pack(anchor="w")
    speech_bubble.pack(anchor="w" if left_align else "e")


root = tk.Tk()
root.geometry("300x300")

canvas = tk.Canvas(root, width=250, height=300)
canvas.pack(side="left", fill="both", expand=True)

scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollbar.pack(side="right", fill="y")
canvas.configure(yscrollcommand=scrollbar.set)

frame = tk.Frame(canvas)
frame.pack(fill="x")

window_id = canvas.create_window((0, 0), window=frame, anchor="nw")
# canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))

for i in range(30):
    add_message(frame, "A", f"Hi {i}", i % 2 == 0)

canvas.bind_all("<MouseWheel>", _on_mousewheel)
canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))


root.mainloop()
