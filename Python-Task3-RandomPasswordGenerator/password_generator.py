import string
import secrets
import tkinter as tk
from tkinter import messagebox


# -----------------------------
# PASSWORD GENERATOR
# -----------------------------

def generate_password():
    try:
        length = int(length_var.get())

        # Check password length
        if length < 8:
            messagebox.showerror(
                "Invalid Length",
                "Password length must be at least 8."
            )
            return

        if length > 100:
            messagebox.showerror(
                "Invalid Length",
                "Password length cannot be more than 100."
            )
            return

        # Build a pool per selected character type, so we can
        # guarantee at least one character from each type later.
        type_pools = []

        if lowercase_var.get() == "Yes":
            type_pools.append(string.ascii_lowercase)

        if uppercase_var.get() == "Yes":
            type_pools.append(string.ascii_uppercase)

        if numbers_var.get() == "Yes":
            type_pools.append(string.digits)

        if symbols_var.get() == "Yes":
            type_pools.append(string.punctuation)

        # Require at least 2 character types selected
        if len(type_pools) < 2:
            messagebox.showerror(
                "Not Enough Options",
                "Please select at least 2 character types."
            )
            return

        # Remove confusing characters from each pool
        if ambiguous_var.get() == "Yes":
            cleaned_pools = []
            for pool in type_pools:
                for char in "0Ol1":
                    pool = pool.replace(char, "")
                cleaned_pools.append(pool)
            type_pools = cleaned_pools

            # A pool could become empty after cleaning (e.g. digits
            # with 0 and 1 both removed would still have 2-9, so this
            # is mainly a safety net for edge cases).
            type_pools = [p for p in type_pools if p]
            if len(type_pools) < 2:
                messagebox.showerror(
                    "Not Enough Options",
                    "After excluding ambiguous characters, fewer than "
                    "2 usable character types remain. Deselect "
                    "'Exclude 0, O, l, 1' or pick different types."
                )
                return

        # Guarantee at least one character from each selected type
        password_chars = [secrets.choice(pool) for pool in type_pools]

        # Fill the remaining length from the combined pool
        combined_pool = "".join(type_pools)
        remaining = length - len(password_chars)

        for _ in range(remaining):
            password_chars.append(secrets.choice(combined_pool))

        # Shuffle so the guaranteed characters aren't always at the front
        for i in range(len(password_chars) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            password_chars[i], password_chars[j] = password_chars[j], password_chars[i]

        password = "".join(password_chars)

        # Display password
        password_var.set(password)

        # Calculate password strength
        update_strength(password)

        # Add to history
        add_to_history(password)

    except ValueError:
        messagebox.showerror(
            "Invalid Input",
            "Please enter a valid number for password length."
        )


# -----------------------------
# PASSWORD STRENGTH
# -----------------------------

def update_strength(password):
    score = 0

    if len(password) >= 8:
        score += 1

    if len(password) >= 12:
        score += 1

    if any(char.islower() for char in password):
        score += 1

    if any(char.isupper() for char in password):
        score += 1

    if any(char.isdigit() for char in password):
        score += 1

    if any(char in string.punctuation for char in password):
        score += 1

    if score <= 2:
        strength_var.set("Strength: Weak")

    elif score <= 4:
        strength_var.set("Strength: Medium")

    else:
        strength_var.set("Strength: Strong")


# -----------------------------
# GENERATION HISTORY (last 5, session only)
# -----------------------------

password_history = []


def add_to_history(password):
    password_history.insert(0, password)

    # Keep only the last 5
    del password_history[5:]

    history_listbox.delete(0, tk.END)
    for pwd in password_history:
        history_listbox.insert(tk.END, pwd)


# -----------------------------
# COPY PASSWORD
# -----------------------------

def copy_password():
    password = password_var.get()

    if password == "":
        messagebox.showwarning(
            "No Password",
            "Generate a password first."
        )
        return

    root.clipboard_clear()
    root.clipboard_append(password)
    root.update()

    messagebox.showinfo(
        "Copied",
        "Password copied to clipboard!"
    )


# -----------------------------
# CLEAR PASSWORD
# -----------------------------

def clear_password():
    password_var.set("")
    strength_var.set("Strength: -")


# -----------------------------
# MAIN WINDOW
# -----------------------------

root = tk.Tk()

root.title("Secure Password Generator")

root.geometry("500x700")

root.resizable(False, False)


# -----------------------------
# TITLE
# -----------------------------

tk.Label(
    root,
    text="🔐 Secure Password Generator",
    font=("Arial", 20, "bold")
).pack(pady=15)


tk.Label(
    root,
    text="Create strong random passwords securely",
    font=("Arial", 10)
).pack(pady=(0, 15))


# -----------------------------
# LENGTH
# -----------------------------

length_frame = tk.Frame(root)

length_frame.pack(pady=5)


tk.Label(
    length_frame,
    text="Password Length (min 8):",
    font=("Arial", 11)
).pack(side="left", padx=5)


length_var = tk.StringVar(value="12")


tk.Entry(
    length_frame,
    textvariable=length_var,
    width=8,
    font=("Arial", 11),
    justify="center"
).pack(side="left")


# -----------------------------
# OPTIONS
# -----------------------------

options_frame = tk.Frame(root)

options_frame.pack(pady=10)


lowercase_var = tk.StringVar(value="Yes")
uppercase_var = tk.StringVar(value="Yes")
numbers_var = tk.StringVar(value="Yes")
symbols_var = tk.StringVar(value="Yes")
ambiguous_var = tk.StringVar(value="No")


def create_option(parent, text, variable):
    frame = tk.Frame(parent)

    frame.pack(pady=2)

    tk.Label(
        frame,
        text=text,
        width=27,
        anchor="w",
        font=("Arial", 10)
    ).pack(side="left")

    tk.OptionMenu(
        frame,
        variable,
        "Yes",
        "No"
    ).pack(side="left")


create_option(
    options_frame,
    "Lowercase letters:",
    lowercase_var
)


create_option(
    options_frame,
    "Uppercase letters:",
    uppercase_var
)


create_option(
    options_frame,
    "Numbers:",
    numbers_var
)


create_option(
    options_frame,
    "Symbols:",
    symbols_var
)


create_option(
    options_frame,
    "Exclude 0, O, l, 1:",
    ambiguous_var
)


# -----------------------------
# BUTTONS
# -----------------------------

button_frame = tk.Frame(root)

button_frame.pack(pady=15)


tk.Button(
    button_frame,
    text="Generate Password",
    command=generate_password,
    font=("Arial", 11, "bold"),
    padx=15,
    pady=6
).pack(side="left", padx=5)


tk.Button(
    button_frame,
    text="Clear",
    command=clear_password,
    font=("Arial", 11),
    padx=15,
    pady=6
).pack(side="left", padx=5)


# -----------------------------
# PASSWORD DISPLAY
# -----------------------------

tk.Label(
    root,
    text="Generated Password",
    font=("Arial", 10, "bold")
).pack(pady=(5, 3))


password_var = tk.StringVar()


tk.Entry(
    root,
    textvariable=password_var,
    width=38,
    font=("Arial", 13),
    justify="center"
).pack(pady=5)


# -----------------------------
# STRENGTH
# -----------------------------

strength_var = tk.StringVar(value="Strength: -")


tk.Label(
    root,
    textvariable=strength_var,
    font=("Arial", 11, "bold")
).pack(pady=5)


# -----------------------------
# COPY BUTTON
# -----------------------------

tk.Button(
    root,
    text="Copy Password",
    command=copy_password,
    font=("Arial", 10),
    padx=20,
    pady=5
).pack(pady=10)


# -----------------------------
# HISTORY (last 5, session only — not saved to file)
# -----------------------------

tk.Label(
    root,
    text="History (last 5, this session only)",
    font=("Arial", 10, "bold")
).pack(pady=(10, 3))

history_listbox = tk.Listbox(
    root,
    width=38,
    height=5,
    font=("Arial", 10),
    justify="center"
)
history_listbox.pack(pady=5)


# -----------------------------
# START APPLICATION
# -----------------------------

root.mainloop()