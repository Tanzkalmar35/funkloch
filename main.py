import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from datetime import datetime


class ChatUI:
    def __init__(self, root):
        self.root = root

        root.title("Funkloch")
        root.geometry("650x550")
        root.configure(bg="#111b21")

        # Überschrift
        tk.Label(
            root, text="Funkloch", font=("Arial", 18, "bold"), bg="#202c33", fg="white"
        ).pack(fill="x", pady=10)

        # Chatverlauf
        self.chat = ScrolledText(
            root,
            bg="#111b21",
            fg="white",
            font=("Arial", 12),
            wrap="word",
            state="disabled",
        )
        self.chat.pack(fill="both", expand=True, padx=10, pady=10)

        self.chat.tag_config("own", foreground="#53bdeb", justify="right")
        self.chat.tag_config("other", foreground="white", justify="left")

        # Eingabebereich
        frame = tk.Frame(root, bg="#202c33")
        frame.pack(fill="x", padx=10, pady=10)

        self.entry = tk.Entry(frame, font=("Arial", 12))
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.send_message)

        tk.Button(
            frame, text="Senden", command=self.send_message, bg="#005c4b", fg="white"
        ).pack(side="right", padx=10)

        # Testnachrichten
        self.add_message("Test", "Lorem Testum", own=False)
        self.add_message("AuchTestAberInBlau", "Subber machmer!", own=True)

        self.entry.focus_set()

    def add_message(self, user_name, message, own=False):
        time = datetime.now().strftime("%H:%M")
        tag = "own" if own else "other"

        self.chat.configure(state="normal")
        self.chat.insert(tk.END, f"{user_name} ({time})\n{message}\n\n", tag)
        self.chat.configure(state="disabled")
        self.chat.see(tk.END)

    def send_message(self, event=None):
        message = self.entry.get().strip()

        if message:
            self.add_message("Du", message, own=True)
            self.entry.delete(0, tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    ChatUI(root)
    root.mainloop()
