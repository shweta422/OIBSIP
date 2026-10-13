# 💬 Chat Application (Advanced)

A real-time, multi-room chat application with a Tkinter GUI, built for the
Oasis Infobyte Python Programming track.

## Features

* Server/client architecture using raw TCP sockets (`socket`, `threading`)
* Real-time, bidirectional messaging between any number of connected clients
* Messages are timestamped
* Graceful disconnect handling — other users in the room are notified when
  someone leaves
* GUI built with Tkinter (login screen → room screen → chat screen)
* User registration and login, with hashed passwords stored in SQLite
* Multiple named chat rooms — joining a room that doesn't exist yet creates it
* Message history for a room loads automatically when you join it
* In-app notification (window title change + system beep) when a new message
  arrives while the window isn't focused
* Emoji shortcode support (`:smile:`, `:laugh:`, `:heart:`, `:thumbsup:`,
  `:sad:`, `:fire:`)

## How to run

Both `server.py` and `client.py` use only Python's built-in libraries —
no `pip install` required.

**1. Start the server once** (on one machine, or your own computer for local testing):
```bash
python server.py
```
Leave this running. It listens on port 5555 and creates `chat.db` on first run.

**2. Start one `client.py` per user:**
```bash
python client.py
```
Register a username and password, log in, then enter a room name to join or
create it.

To test with multiple users on the same computer, just run `client.py`
multiple times in separate terminals.

To connect from a different machine on the same network, change the `HOST`
value at the top of `client.py` to the server machine's local IP address.

## How it works

The server and each client exchange small JSON messages over a TCP socket,
one JSON object per line (`\n`-terminated), so each side can read messages
one at a time with Python's file-like socket interface.

* **Authentication**: the client sends a username/password; the server
  checks it against SQLite (`users` table), where only a SHA-256 hash of the
  password is stored — never the plain password.
* **Rooms**: the server keeps an in-memory dictionary mapping each room name
  to the list of currently connected clients in it. Messages are only
  broadcast to members of the same room.
* **History**: every message is also saved to the `messages` table in
  SQLite. When a client joins a room, the server sends back the last 50
  messages for that room so the conversation doesn't start from nothing.
* **Notifications**: Tkinter's `<FocusOut>`/`<FocusIn>` events track whether
  the chat window is the active window. If a message arrives while it isn't,
  the window title changes and the system bell sounds.

## Privacy and security — what's stored, and what's NOT protected

* **Stored locally in `chat.db` (SQLite)**: usernames, a SHA-256 hash of each
  password (not the password itself), and all chat messages with their room
  and timestamp.
* **The network connection itself is NOT encrypted.** This uses a plain TCP
  socket, not TLS/SSL. On a shared or untrusted network, it would be
  possible for someone else to intercept and read the raw traffic, including
  login credentials in transit. This is acceptable for a local learning
  project but would need TLS (or a library like Flask-SocketIO over HTTPS)
  before any real-world or multi-network use.
* Password hashing (SHA-256) is sufficient for this project's scope but is
  not as strong as a purpose-built password hashing algorithm (e.g. bcrypt
  or Argon2), which include built-in slow-hashing and salting.
* No message content is encrypted — anyone with access to `chat.db` could
  read full chat history in plain text.

## Known limitations

* The server must be running and reachable before any client can connect.
* Only the last 50 messages per room are loaded as history.
* No message editing or deletion.
* Designed for trusted local/LAN use — not hardened for the public internet.

## Technologies Used

Python, socket, threading, sqlite3, hashlib, json, Tkinter

## Author

Shweta Soni