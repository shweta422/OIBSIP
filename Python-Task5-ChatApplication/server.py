
import socket
import threading
import json
import sqlite3
import hashlib
import datetime
import traceback
 
HOST = "0.0.0.0"
PORT = 5555
DB_FILE = "chat.db"
 
 
# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------
 
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room TEXT NOT NULL,
        username TEXT NOT NULL,
        text TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )""")
    conn.commit()
    conn.close()
 
 
def hash_password(password):
    # SHA-256 is enough here (same level the task brief suggests for
    # client-side hashing). Document in README that this is not
    # bcrypt-grade and the connection itself isn't encrypted.
    return hashlib.sha256(password.encode()).hexdigest()
 
 
# ---------------------------------------------------------
# IN-MEMORY ROOM STATE
# ---------------------------------------------------------
# rooms: { room_name: [ (connection, username), ... ] }
 
rooms = {}
rooms_lock = threading.Lock()
 
 
def send_json(conn, data):
    try:
        conn.sendall((json.dumps(data) + "\n").encode())
    except OSError:
        pass
 
 
def broadcast(room, data, exclude_conn=None):
    with rooms_lock:
        members = list(rooms.get(room, []))
    for member_conn, _ in members:
        if member_conn is not exclude_conn:
            send_json(member_conn, data)
 
 
# ---------------------------------------------------------
# AUTH
# ---------------------------------------------------------
 
def handle_register(conn, payload):
    username = payload.get("username", "").strip()
    password = payload.get("password", "")
 
    if not username or not password:
        send_json(conn, {"type": "auth_result", "success": False,
                          "message": "Username and password required."})
        return
 
    db = sqlite3.connect(DB_FILE)
    c = db.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password))
        )
        db.commit()
        send_json(conn, {"type": "auth_result", "success": True,
                          "message": "Registered. Please log in."})
    except sqlite3.IntegrityError:
        send_json(conn, {"type": "auth_result", "success": False,
                          "message": "That username is already taken."})
    finally:
        db.close()
 
 
def handle_login(conn, payload):
    username = payload.get("username", "").strip()
    password = payload.get("password", "")
 
    db = sqlite3.connect(DB_FILE)
    c = db.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    db.close()
 
    if row and row[0] == hash_password(password):
        send_json(conn, {"type": "auth_result", "success": True,
                          "message": "Login successful.", "username": username})
        return username
 
    send_json(conn, {"type": "auth_result", "success": False,
                      "message": "Invalid username or password."})
    return None
 
 
# ---------------------------------------------------------
# MESSAGES / HISTORY
# ---------------------------------------------------------
 
def load_history(room, limit=50):
    db = sqlite3.connect(DB_FILE)
    c = db.cursor()
    c.execute(
        "SELECT username, text, timestamp FROM messages "
        "WHERE room = ? ORDER BY id DESC LIMIT ?",
        (room, limit)
    )
    rows = c.fetchall()
    db.close()
    rows.reverse()
    return [{"username": r[0], "text": r[1], "timestamp": r[2]} for r in rows]
 
 
def save_message(room, username, text):
    timestamp = datetime.datetime.now().strftime("%H:%M")
    db = sqlite3.connect(DB_FILE)
    c = db.cursor()
    c.execute(
        "INSERT INTO messages (room, username, text, timestamp) VALUES (?, ?, ?, ?)",
        (room, username, text, timestamp)
    )
    db.commit()
    db.close()
    return timestamp
 
 
# ---------------------------------------------------------
# PER-CLIENT HANDLER
# ---------------------------------------------------------
 
def handle_client(conn, addr):
    username = None
    current_room = None
    client_file = conn.makefile("r")
 
    try:
        for line in client_file:
            line = line.strip()
            if not line:
                continue
 
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
 
            msg_type = payload.get("type")
 
            try:
                if msg_type == "register":
                    handle_register(conn, payload)
 
                elif msg_type == "login":
                    result = handle_login(conn, payload)
                    if result:
                        username = result
 
                elif msg_type == "join_room":
                    if not username:
                        send_json(conn, {"type": "error", "message": "Log in first."})
                        continue
 
                    room = payload.get("room", "general").strip() or "general"
 
                    if current_room:
                        with rooms_lock:
                            rooms[current_room] = [
                                m for m in rooms.get(current_room, []) if m[0] is not conn
                            ]
                        broadcast(current_room, {"type": "system",
                                                  "text": f"{username} left the room."})
 
                    current_room = room
                    with rooms_lock:
                        rooms.setdefault(room, []).append((conn, username))
 
                    send_json(conn, {"type": "room_joined", "room": room,
                                      "history": load_history(room)})
                    broadcast(room, {"type": "system", "text": f"{username} joined the room."},
                              exclude_conn=conn)
 
                elif msg_type == "message":
                    if not username or not current_room:
                        send_json(conn, {"type": "error", "message": "Join a room first."})
                        continue
 
                    text = payload.get("text", "").strip()
                    if not text:
                        continue
 
                    timestamp = save_message(current_room, username, text)
                    broadcast(current_room, {
                        "type": "message",
                        "username": username,
                        "text": text,
                        "timestamp": timestamp
                    })
 
            except Exception:
                # Print the full error to the server console instead of
                # silently crashing this client's connection. This is what
                # lets us actually see what went wrong, instead of the
                # client just showing "lost connection" with no reason.
                print(f"\n--- ERROR handling '{msg_type}' from {addr} ---")
                traceback.print_exc()
                print("--- end error ---\n")
 
    except (ConnectionResetError, OSError):
        pass
    finally:
        if current_room:
            with rooms_lock:
                rooms[current_room] = [
                    m for m in rooms.get(current_room, []) if m[0] is not conn
                ]
            broadcast(current_room, {"type": "system",
                                      "text": f"{username or 'A user'} disconnected."})
        conn.close()
 
 
# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
 
def main():
    init_db()
 
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
 
    print(f"Chat server listening on port {PORT}...")
 
    while True:
        conn, addr = server_socket.accept()
        print("New connection:", addr)
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
 
 
if __name__ == "__main__":
    main()
 

