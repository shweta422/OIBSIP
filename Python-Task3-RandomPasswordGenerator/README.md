# 🔐 Secure Password Generator

A Python-based GUI application that generates customizable random passwords using Python's `secrets` module and Tkinter.

## Features

* Custom password length (minimum 8, maximum 100)
* Lowercase letters
* Uppercase letters
* Numbers
* Symbols
* Requires at least 2 character types to be selected
* Guarantees at least one character from each selected type appears in the password
* Option to exclude confusing characters such as `0`, `O`, `l`, and `1`
* Password strength indicator
* Generation history — shows the last 5 passwords generated in the current session
* Copy password to clipboard
* Clear generated password
* Input validation
* Simple graphical user interface

## Technologies Used

* Python
* Tkinter
* Secrets
* String

## How to Run

Make sure Python is installed on your computer.

Run the following command:

```bash
python password_generator.py
```

## How It Works

The application builds a separate character pool for each selected type (lowercase, uppercase, numbers, symbols). It first picks one random character from each selected pool using `secrets.choice()` to guarantee that type appears in the final password, then fills the remaining length from the combined pool. The result is shuffled using a Fisher-Yates shuffle powered by `secrets.randbelow()` (rather than `random.shuffle`) to keep the whole process cryptographically secure.

The application also checks the generated password for length, lowercase letters, uppercase letters, numbers, and symbols to provide a basic strength indication.

Generation history is kept only in memory for the current session (not written to disk), since persisting generated passwords to a file would be a security risk.

## Design Note

The task brief suggested `pyperclip` for clipboard support. This version uses Tkinter's built-in `clipboard_append()` instead, which achieves the same result without an extra dependency.

## Learning Outcomes

This project helped me practice:

* Python functions
* Loops
* Conditional statements
* Exception handling
* String manipulation
* Tkinter GUI development
* Working with Python modules
* Secure random password generation
* Guaranteed-inclusion character sampling
* Basic input validation

## Future Improvements

* More detailed password strength analysis
* Dark mode and additional UI customization
* More customizable character-set options
* Additional password generation settings

## Project Screenshot

![Secure Password Generator](screenshot.png)

## Author

Shweta Soni
