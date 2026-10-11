import datetime
import difflib
import json
import os
import re
import smtplib
import threading
import webbrowser
from email.message import EmailMessage
from urllib.parse import quote_plus

import pyttsx3
import requests
import speech_recognition as sr
from dotenv import load_dotenv


# ---------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------------

load_dotenv()

ASSISTANT_EMAIL = os.getenv("ASSISTANT_EMAIL")
ASSISTANT_EMAIL_APP_PASSWORD = os.getenv("ASSISTANT_EMAIL_APP_PASSWORD")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


# ---------------------------------------------------------
# INITIALIZE VOICE COMPONENTS
# ---------------------------------------------------------

recognizer = sr.Recognizer()


# ---------------------------------------------------------
# LOAD JSON FILES
# ---------------------------------------------------------

def load_json(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

    except FileNotFoundError:
        print(f"{filename} was not found.")
        return default

    except json.JSONDecodeError:
        print(f"{filename} contains invalid JSON.")
        return default


config = load_json(
    "config.json",
    {
        "contacts": {},
        "custom_commands": {}
    }
)

knowledge_base = load_json(
    "knowledge_base.json",
    {}
)

contacts = config.get("contacts", {})
custom_commands = config.get("custom_commands", {})

pending_reminders = []
contacts = config.get("contacts", {})
custom_commands = config.get("custom_commands", {})

pending_reminders = []

# ---------------------------------------------------------
# TEXT TO SPEECH
# ---------------------------------------------------------

def speak(text):
    print(f"Assistant: {text}")

    local_engine = pyttsx3.init()
    local_engine.setProperty("rate", 170)
    local_engine.say(text)
    local_engine.runAndWait()
    local_engine.stop()


# ---------------------------------------------------------
# TEXT NORMALIZATION
# ---------------------------------------------------------

def normalize(text):
    text = text.lower().strip()

    text = re.sub(r"[^\w\s@.\-]", "", text)

    text = re.sub(r"\s+", " ", text)

    return text


# ---------------------------------------------------------
# VOICE INPUT
# ---------------------------------------------------------

def listen():
    with sr.Microphone(device_index=2) as source:

        print("\nListening...")

        recognizer.adjust_for_ambient_noise(
            source,
            duration=1.5
        )

        try:

            audio = recognizer.listen(
                source,
                timeout=8,
                phrase_time_limit=10
            )

            print("Recognizing...")

            text = recognizer.recognize_google(audio)

            print(f"You: {text}")

            return normalize(text)

        except sr.WaitTimeoutError:

            speak("I didn't hear anything. Please try again.")

        except sr.UnknownValueError:

            speak("I couldn't understand that. Please repeat.")

        except sr.RequestError:

            speak(
                "The speech recognition service is currently unavailable."
            )

        except Exception as error:

            print("Microphone error:", error)

            speak(
                "There was a problem with the microphone."
            )

    return ""


# ---------------------------------------------------------
# GREETING
# ---------------------------------------------------------

def greet_user():

    current_hour = datetime.datetime.now().hour

    if current_hour < 12:
        greeting = "Good morning"

    elif current_hour < 18:
        greeting = "Good afternoon"

    else:
        greeting = "Good evening"

    speak(
        f"{greeting}. I am your voice assistant. "
        "How can I help you?"
    )


# ---------------------------------------------------------
# TIME
# ---------------------------------------------------------

def tell_time():

    current_time = datetime.datetime.now().strftime("%I:%M %p")

    speak(f"The current time is {current_time}.")


# ---------------------------------------------------------
# DATE
# ---------------------------------------------------------

def tell_date():

    current_date = datetime.datetime.now().strftime(
        "%A, %d %B %Y"
    )

    speak(f"Today is {current_date}.")


# ---------------------------------------------------------
# WEB SEARCH
# ---------------------------------------------------------

def search_web(command):

    query = re.sub(
        r"^(search for|search|google)\s+",
        "",
        command,
        flags=re.IGNORECASE
    ).strip()

    if not query:

        speak("What would you like me to search for?")

        query = listen()

        if not query:
            return

    speak(f"Searching for {query}.")

    url = (
        "https://www.google.com/search?q="
        + quote_plus(query)
    )

    webbrowser.open(url)


# ---------------------------------------------------------
# WEATHER
# ---------------------------------------------------------

def extract_weather_city(command):

    match = re.search(
        r"(?:weather|temperature|forecast)"
        r"(?:\s+(?:in|at|for))\s+(.+)$",
        command
    )

    if match:
        return match.group(1).strip()

    return ""


def get_weather(city):

    if not OPENWEATHER_API_KEY:

        speak(
            "The weather API key has not been configured."
        )

        return

    url = "https://api.openweathermap.org/data/2.5/weather"

    parameters = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }

    try:

        response = requests.get(
            url,
            params=parameters,
            timeout=10
        )

        data = response.json()

        if response.status_code != 200:


            speak(
                "I couldn't find weather information "
                f"for {city}."
            )

            return

        temperature = data["main"]["temp"]

        feels_like = data["main"]["feels_like"]

        humidity = data["main"]["humidity"]

        description = data["weather"][0]["description"]

        speak(
            f"The weather in {city} is {description}. "
            f"The temperature is {temperature:.1f} degrees Celsius. "
            f"It feels like {feels_like:.1f} degrees. "
            f"Humidity is {humidity} percent."
        )

    except requests.RequestException:

        speak(
            "I couldn't connect to the weather service."
        )

    except Exception as error:

        print("Weather error:", error)

        speak(
            "Something went wrong while getting the weather."
        )


def handle_weather(command):

    city = extract_weather_city(command)

    if not city:

        speak("Which city would you like the weather for?")

        city = listen()

    if city:

        get_weather(city)


# ---------------------------------------------------------
# EMAIL
# ---------------------------------------------------------

def find_contact(command):

    normalized_command = normalize(command)

    for name in contacts:

        if normalize(name) in normalized_command:

            return name

    return None


def find_contact_from_name(name):

    normalized_name = normalize(name)

    for contact_name in contacts:

        if normalize(contact_name) == normalized_name:

            return contact_name

    return None


def send_email():

    if not ASSISTANT_EMAIL or not ASSISTANT_EMAIL_APP_PASSWORD:

        speak(
            "Email credentials are not configured. "
            "Please check your environment variables."
        )

        return

    speak(
        "Who should I email? "
        "Please say the contact name."
    )

    recipient_name = listen()

    if not recipient_name:

        return

    contact = find_contact_from_name(recipient_name)

    if not contact:

        speak(
            "I couldn't find that contact in your configuration."
        )

        return

    recipient_email = contacts[contact]

    speak("What should be the subject?")

    subject = listen()

    if not subject:

        return

    speak("What should I write in the email?")

    body = listen()

    if not body:

        return

    try:

        message = EmailMessage()

        message["From"] = ASSISTANT_EMAIL

        message["To"] = recipient_email

        message["Subject"] = subject

        message.set_content(body)

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as smtp:

            smtp.login(
                ASSISTANT_EMAIL,
                ASSISTANT_EMAIL_APP_PASSWORD
            )

            smtp.send_message(message)

        speak(
            f"Your email has been sent to {contact}."
        )

    except smtplib.SMTPException as error:

        print("Email error:", error)

        speak(
            "I couldn't send the email. "
            "Please check your Gmail settings."
        )

    except Exception as error:

        print("Unexpected email error:", error)

        speak(
            "Something went wrong while sending the email."
        )


# ---------------------------------------------------------
# REMINDERS
# ---------------------------------------------------------

def reminder_alert(message):

    print("\nREMINDER:", message)

    # Don't speak here — this runs on a background thread, and
    # speaking at the same time the main thread is listening causes
    # a conflict. Instead, queue it up for the main loop to speak.
    pending_reminders.append(message)


def set_reminder(command):

    pattern = re.compile(
        r"(?:in|for|after)\s+(\d+)\s*"
        r"(seconds?|minutes?|hours?)",
        re.IGNORECASE
    )

    match = pattern.search(command)

    if not match:

        speak(
            "Please say a duration such as "
            "remind me in 5 minutes."
        )

        return

    amount = int(match.group(1))

    unit = match.group(2).lower()

    if unit.startswith("second"):

        duration = amount

    elif unit.startswith("minute"):

        duration = amount * 60

    else:

        duration = amount * 3600

    message = pattern.sub(
        "",
        command,
        count=1
    ).strip()

    message = re.sub(
        r"^(remind me|set a reminder|set reminder|reminder)\s*",
        "",
        message,
        flags=re.IGNORECASE
    ).strip()

    message = re.sub(
        r"^(to|that|for me to)\s+",
        "",
        message,
        flags=re.IGNORECASE
    ).strip()

    message = re.sub(
        r"\s+",
        " ",
        message
    ).strip()

    if not message:

        speak("What should I remind you about?")

        message = listen()

    if not message:

        message = "You have a reminder."

    timer = threading.Timer(
        duration,
        reminder_alert,
        args=(message,)
    )

    timer.daemon = True

    timer.start()

    if duration < 60:

        duration_text = f"{amount} seconds"

    elif duration < 3600:

        duration_text = f"{amount} minutes"

    else:

        duration_text = f"{amount} hours"

    speak(
        f"Reminder set for {duration_text}."
    )


# ---------------------------------------------------------
# KNOWLEDGE BASE
# ---------------------------------------------------------

def clean_question(question):

    question = normalize(question)

    prefixes = [
        "what is ",
        "whats ",
        "tell me about ",
        "who is ",
        "who was "
    ]

    for prefix in prefixes:

        if question.startswith(prefix):

            return question[len(prefix):].strip()

    return question


def answer_from_knowledge_base(command):

    query = clean_question(command)

    if not query:

        speak(
            "What would you like to know?"
        )

        return

    normalized_questions = {
        normalize(question): question
        for question in knowledge_base
    }

    # Exact match
    if query in normalized_questions:

        original_question = normalized_questions[query]

        speak(
            knowledge_base[original_question]
        )

        return

    # Partial match
    for normalized_question, original_question in normalized_questions.items():

        if (
            normalized_question in query
            or query in normalized_question
        ):

            speak(
                knowledge_base[original_question]
            )

            return

    # Fuzzy matching
    matches = difflib.get_close_matches(
        query,
        list(normalized_questions.keys()),
        n=1,
        cutoff=0.55
    )

    if matches:

        original_question = normalized_questions[matches[0]]

        speak(
            knowledge_base[original_question]
        )

    else:

        speak(
            "I don't have an answer for that "
            "in my local knowledge base yet."
        )


# ---------------------------------------------------------
# CUSTOM COMMANDS
# ---------------------------------------------------------

def find_custom_command(command):

    normalized_command = normalize(command)

    normalized_commands = {
        normalize(name): name
        for name in custom_commands
    }

    # Exact match
    if normalized_command in normalized_commands:

        return normalized_commands[normalized_command]

    # Phrase contained in command
    for normalized_name, original_name in normalized_commands.items():

        if normalized_name in normalized_command:

            return original_name

    # Fuzzy match
    matches = difflib.get_close_matches(
        normalized_command,
        list(normalized_commands.keys()),
        n=1,
        cutoff=0.72
    )

    if matches:

        return normalized_commands[matches[0]]

    return None


def run_custom_command(command):

    command_name = find_custom_command(command)

    if not command_name:

        return False

    action = custom_commands[command_name]

    action_type = action.get("type")

    value = action.get("value")

    if action_type == "response":

        speak(value)

        return True

    if action_type == "url":

        speak(
            f"Opening {command_name}."
        )

        webbrowser.open(value)

        return True

    return False


# ---------------------------------------------------------
# INTENT DETECTION
# ---------------------------------------------------------

def detect_intent(command):

    command = normalize(command)

    if not command:

        return "unknown"

    # Exit
    exit_phrases = [
        "stop",
        "exit",
        "quit",
        "goodbye",
        "close assistant",
        "shutdown"
    ]

    if any(
        phrase in command
        for phrase in exit_phrases
    ):

        return "exit"

    # Greeting
    greeting_phrases = [
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "good evening"
    ]

    if any(
        phrase in command
        for phrase in greeting_phrases
    ):

        return "greeting"

    # Time
    time_phrases = [
        "what time is it",
        "tell me the time",
        "current time",
        "what is the time",
        "can you tell me what time it is",
        "time right now"
    ]

    if any(
        phrase in command
        for phrase in time_phrases
    ):

        return "time"

    # Date
    date_phrases = [
        "what is todays date",
        "whats todays date",
        "tell me the date",
        "what day is it",
        "current date",
        "todays date"
    ]
    if any(
        phrase in command
        for phrase in date_phrases
    ):

        return "date"

    # Search
    search_phrases = [
        "search for",
        "search",
        "google"
    ]

    if any(
        command.startswith(phrase)
        for phrase in search_phrases
    ):

        return "search"

    # Weather
    weather_phrases = [
        "weather",
        "temperature",
        "forecast"
    ]

    if any(
        phrase in command
        for phrase in weather_phrases
    ):

        return "weather"

    # Email
    email_phrases = [
        "send an email",
        "send email",
        "send mail",
        "send a mail"
    ]

    if any(
        phrase in command
        for phrase in email_phrases
    ):

        return "email"

    # Reminder
    reminder_phrases = [
        "set a reminder",
        "remind me",
        "set reminder",
        "reminder"
    ]

    if any(
        phrase in command
        for phrase in reminder_phrases
    ):

        return "reminder"

    # Knowledge
    knowledge_phrases = [
        "what is ",
        "whats ",
        "tell me about ",
        "who is ",
        "who was "
    ]

    if any(
        command.startswith(phrase)
        for phrase in knowledge_phrases
    ):

        return "knowledge"

    return "unknown"


# ---------------------------------------------------------
# COMMAND HANDLER
# ---------------------------------------------------------

def handle_command(command):

    intent = detect_intent(command)

    print(f"Detected intent: {intent}")

    if intent == "exit":

        speak("Goodbye. Have a nice day.")

        return False

    if intent == "greeting":

        greet_user()

    elif intent == "time":

        tell_time()

    elif intent == "date":

        tell_date()

    elif intent == "search":

        search_web(command)

    elif intent == "weather":

        handle_weather(command)

    elif intent == "email":

        send_email()

    elif intent == "reminder":

        set_reminder(command)

    elif intent == "knowledge":

        answer_from_knowledge_base(command)

    else:

        if not run_custom_command(command):

            speak(
                "I didn't recognize that command. "
                "Please try saying it another way."
            )

    return True


# ---------------------------------------------------------
# MAIN PROGRAM
# ---------------------------------------------------------

def main():

    print("=" * 55)
    print("ADVANCED PYTHON VOICE ASSISTANT")
    print("=" * 55)

    greet_user()

    while True:

        while pending_reminders:
            message = pending_reminders.pop(0)
            speak(f"Reminder. {message}")

        command = listen()

        if not command:

            continue

        if not handle_command(command):

            break


# ---------------------------------------------------------
# START PROGRAM
# ---------------------------------------------------------

if __name__ == "__main__":
    main()
