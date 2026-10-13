import socket
import threading
import json
import queue
import tkinter as tk
from tkinter import messagebox
 
HOST = "127.0.0.1"  # change this if the server is on another machine
PORT = 5555
 
EMOJI_MAP = {
    ":smile:": "😄",
    ":laugh:": "😂",
    ":heart:": "❤️",
    ":thumbsup:": "👍",
    ":sad:": "😢",
    ":fire:": "🔥",
}
 
 
def convert_emojis(text):
    for code, emoji in EMOJI_MAP.items():
        text = text.replace(code, emoji)
    return text
 
 
class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Application")
 
        self.sock = None
        self.server_file = None
        self.username = None
        self.current_room = None
        self.window_focused = True
 
        self.incoming = queue.Queue()
 
        self.root.bind("<FocusIn>", self.on_focus_in)
        self.root.bind("<FocusOut>", self.on_focus_out)
 
        if not self.connect_to_server():
            return
 
        self.build_login_screen()
        self.root.after(100, self.process_incoming)
 
    # -----------------------------------------------------
    # NETWORKING
    # -----------------------------------------------------
 
    def connect_to_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            self.server_file = self.sock.makefile("r")
            threading.Thread(target=self.receive_loop, daemon=True).start()
            return True
        except OSError as error:
            messagebox.showerror("Connection Error",
                                  f"Could not connect to the server.\n{error}")
            self.root.destroy()
            return False
 
    def send_json(self, data):
        try:
            self.sock.sendall((json.dumps(data) + "\n").encode())
        except OSError:
            messagebox.showerror("Connection Error", "Lost connection to the server.")
 
    def receive_loop(self):
        # Runs on a background thread. Tkinter widgets can't be safely
        # touched from here, so incoming messages are just queued —
        # process_incoming() (running in the main thread) handles them.
        try:
            for line in self.server_file:
                line = line.strip()
                if not line:
                    continue
                try:
                    self.incoming.put(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError:
            pass
 
    def process_incoming(self):
        while not self.incoming.empty():
            self.handle_payload(self.incoming.get())
        self.root.after(100, self.process_incoming)
 
    def handle_payload(self, payload):
        msg_type = payload.get("type")
 
        if msg_type == "auth_result":
            self.handle_auth_result(payload)
        elif msg_type == "room_joined":
            self.handle_room_joined(payload)
        elif msg_type == "message":
            self.display_message(payload)
            self.notify_if_unfocused()
        elif msg_type == "system":
            self.display_system(payload.get("text", ""))
        elif msg_type == "error":
            messagebox.showerror("Error", payload.get("message", "Unknown error."))
 
    # -----------------------------------------------------
    # SCREENS
    # -----------------------------------------------------
 
    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
 
    def build_login_screen(self):
        self.clear_screen()
        self.root.geometry("350x260")
 
        tk.Label(self.root, text="Chat Login", font=("Arial", 16, "bold")).pack(pady=15)
 
        tk.Label(self.root, text="Username").pack()
        self.username_entry = tk.Entry(self.root)
        self.username_entry.pack()
 
        tk.Label(self.root, text="Password").pack()
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.pack()
 
        tk.Button(self.root, text="Login", command=self.do_login,
                  font=("Arial", 10, "bold")).pack(pady=10)
        tk.Button(self.root, text="Register", command=self.do_register).pack()
 
    def do_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showwarning("Missing Info", "Enter both username and password.")
            return
        self.send_json({"type": "login", "username": username, "password": password})
 
    def do_register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            messagebox.showwarning("Missing Info", "Enter both username and password.")
            return
        self.send_json({"type": "register", "username": username, "password": password})
 
    def handle_auth_result(self, payload):
        if payload.get("success"):
            if "username" in payload:
                self.username = payload["username"]
                self.build_room_screen()
            else:
                messagebox.showinfo("Registered", payload.get("message", "Registered."))
        else:
            messagebox.showerror("Failed", payload.get("message", "Something went wrong."))
 
    def build_room_screen(self):
        self.clear_screen()
        self.root.geometry("350x220")
 
        tk.Label(self.root, text=f"Welcome, {self.username}",
                 font=("Arial", 14, "bold")).pack(pady=15)
        tk.Label(self.root, text="Room name (joins it, or creates it if new):").pack()
 
        self.room_entry = tk.Entry(self.root)
        self.room_entry.insert(0, "general")
        self.room_entry.pack()
 
        tk.Button(self.root, text="Join Room", command=self.join_room,
                  font=("Arial", 10, "bold")).pack(pady=15)
 
    def join_room(self):
        room = self.room_entry.get().strip() or "general"
        self.send_json({"type": "join_room", "room": room})
 
    def handle_room_joined(self, payload):
        self.current_room = payload.get("room")
        self.build_chat_screen()
        for msg in payload.get("history", []):
            self.display_message(msg)
 
    def build_chat_screen(self):
        self.clear_screen()
        self.root.geometry("500x550")
        self.root.title(f"Room: {self.current_room}")
 
        tk.Label(self.root, text=f"Room: {self.current_room}",
                 font=("Arial", 13, "bold")).pack(pady=5)
 
        self.chat_box = tk.Text(self.root, state="disabled", wrap="word")
        self.chat_box.pack(fill="both", expand=True, padx=10, pady=5)
 
        entry_frame = tk.Frame(self.root)
        entry_frame.pack(fill="x", padx=10, pady=5)
 
        self.message_entry = tk.Entry(entry_frame)
        self.message_entry.pack(side="left", fill="x", expand=True)
        self.message_entry.bind("<Return>", lambda event: self.send_message())
 
        tk.Button(entry_frame, text="Send", command=self.send_message).pack(side="left", padx=5)
 
        tk.Label(self.root, font=("Arial", 8),
                 text="Emoji shortcodes: :smile: :laugh: :heart: :thumbsup: :sad: :fire:"
                 ).pack(pady=(0, 5))
 
    def send_message(self):
        text = self.message_entry.get().strip()
        if not text:
            return
        text = convert_emojis(text)
        self.send_json({"type": "message", "text": text})
        self.message_entry.delete(0, tk.END)
 
    def display_message(self, payload):
        self.chat_box.config(state="normal")
        line = f"[{payload.get('timestamp', '')}] {payload.get('username', '')}: {payload.get('text', '')}\n"
        self.chat_box.insert(tk.END, line)
        self.chat_box.see(tk.END)
        self.chat_box.config(state="disabled")
 
    def display_system(self, text):
        self.chat_box.config(state="normal")
        self.chat_box.insert(tk.END, f"* {text}\n")
        self.chat_box.see(tk.END)
        self.chat_box.config(state="disabled")
 
    # -----------------------------------------------------
    # FOCUS-BASED NOTIFICATION
    # -----------------------------------------------------
 
    def on_focus_in(self, event):
        self.window_focused = True
        if self.current_room:
            self.root.title(f"Room: {self.current_room}")
 
    def on_focus_out(self, event):
        self.window_focused = False
 
    def notify_if_unfocused(self):
        if not self.window_focused:
            self.root.bell()
            self.root.title("New message! — Chat Application")
 
 
def main():
    root = tk.Tk()
    ChatClient(root)
    root.mainloop()
 
 
if __name__ == "__main__":
    main()
 