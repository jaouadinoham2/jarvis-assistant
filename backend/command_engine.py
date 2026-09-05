"""
JARVIS Command Engine — System Actions
Handles opening apps, calculations, time/date, and other useful tasks.
"""

import subprocess
import datetime
import os
import re
import math
import webbrowser


# ─── App Registry (common Windows apps) ─────────────────────
APP_REGISTRY = {
    # Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "brave": "brave",
    "brave browser": "brave",
    "browser": "brave",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "firefox": "firefox",

    # Communication
    "whatsapp": "explorer.exe shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
    "telegram": "telegram",
    "discord": "discord",

    # Microsoft Office
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "notepad": "notepad",

    # Media
    "spotify": "spotify",
    "vlc": "vlc",

    # System
    "calculator": "calc",
    "calc": "calc",
    "settings": "ms-settings:",
    "file explorer": "explorer",
    "explorer": "explorer",
    "task manager": "taskmgr",
    "command prompt": "cmd",
    "cmd": "cmd",
    "powershell": "powershell",
    "paint": "mspaint",
    "snipping tool": "snippingtool",
    "camera": "microsoft.windows.camera:",
    "clock": "ms-clock:",
    "maps": "bingmaps:",
    "store": "ms-windows-store:",
    "photos": "ms-photos:",
}


def detect_command(user_message):
    """
    Detect if the user's message is a command that JARVIS can execute.
    
    Returns:
        (command_type, result_text) if a command is detected
        None if it's just a regular chat message
    """
    msg = user_message.lower().strip()

    # ─── Math / Calculation ──────────────────────────────────
    if is_math_request(msg):
        expression = extract_math_expression(user_message)
        if expression:
            result = safe_calculate(expression)
            if result is not None:
                return ("math", f"The answer is: {result}")

    # ─── Open Website / URL ───────────────────────────────────
    website_result = detect_website_command(msg)
    if website_result:
        return website_result

    # ─── Open App ────────────────────────────────────────────
    if any(phrase in msg for phrase in ["open ", "launch ", "start ", "run "]):
        app_name = extract_app_name(msg)
        if app_name and app_name in APP_REGISTRY:
            success = open_app(APP_REGISTRY[app_name])
            if success:
                return ("app", f"I've opened {app_name.title()} for you, sir.")
            else:
                return ("app", f"I tried to open {app_name.title()} but it doesn't seem to be installed on your system.")

    # ─── Time & Date ─────────────────────────────────────────
    if any(phrase in msg for phrase in ["what time", "current time", "what's the time", "tell me the time"]):
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        return ("time", f"It's currently {time_str}, sir.")

    if any(phrase in msg for phrase in ["what date", "today's date", "what's the date", "what day"]):
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        return ("date", f"Today is {date_str}, sir.")

    # ─── Volume Control ──────────────────────────────────────
    if "mute" in msg or "unmute" in msg:
        return ("info", "I can't control your system volume directly yet, but you can press the mute button on your keyboard.")

    # ─── Shutdown / Restart ──────────────────────────────────
    if any(phrase in msg for phrase in ["shutdown computer", "shut down computer", "restart computer"]):
        return ("info", "For safety reasons, I won't shut down or restart your computer automatically. You can do this from the Start menu.")

    return None


def is_math_request(msg):
    """Check if the message looks like a math question."""
    math_keywords = ["calculate", "what is", "what's", "how much is", "solve", "compute", "evaluate"]
    has_keyword = any(kw in msg for kw in math_keywords)
    has_math_chars = bool(re.search(r'[\d]+\s*[\+\-\*\/\^\%]', msg))
    ends_with_question = msg.rstrip().endswith("?") or msg.rstrip().endswith("=")
    has_equals = "=" in msg and any(c.isdigit() for c in msg)

    return has_keyword or has_math_chars or (ends_with_question and any(c.isdigit() for c in msg))


def extract_math_expression(msg):
    """Extract a mathematical expression from the message."""
    # Remove common words
    cleaned = msg.lower()
    for word in ["calculate", "what is", "what's", "how much is", "solve", "compute", "evaluate", "?", "="]:
        cleaned = cleaned.replace(word, "")

    # Replace common math words
    cleaned = cleaned.replace("plus", "+").replace("minus", "-")
    cleaned = cleaned.replace("times", "*").replace("multiplied by", "*")
    cleaned = cleaned.replace("divided by", "/").replace("over", "/")
    cleaned = cleaned.replace("power", "**").replace("to the power of", "**")
    cleaned = cleaned.replace("squared", "**2").replace("cubed", "**3")
    cleaned = cleaned.replace("x", "*").replace("X", "*")
    cleaned = cleaned.replace("^", "**")

    # Extract just the math part (digits and operators)
    # Allow digits, operators, parentheses, dots, spaces
    math_chars = re.findall(r'[\d\.\+\-\*\/\(\)\s\%]+', cleaned)
    if math_chars:
        expression = "".join(math_chars).strip()
        # Remove trailing operators
        expression = expression.rstrip("+-*/")
        if expression and any(c.isdigit() for c in expression):
            return expression

    return None


def safe_calculate(expression):
    """Safely evaluate a math expression using Python."""
    try:
        # Clean the expression
        expression = expression.strip()
        if not expression:
            return None

        # Only allow safe characters
        allowed = set("0123456789.+-*/%() ")
        if not all(c in allowed for c in expression):
            return None

        # Use eval with restricted builtins for safety
        result = eval(expression, {"__builtins__": {}}, {
            "abs": abs, "round": round, "min": min, "max": max,
            "pow": pow, "sum": sum,
            "sqrt": math.sqrt, "pi": math.pi, "e": math.e,
        })

        # Format result nicely
        if isinstance(result, float):
            if result == int(result) and abs(result) < 1e15:
                return str(int(result))
            return f"{result:,.6f}".rstrip('0').rstrip('.')
        return f"{result:,}"

    except Exception as e:
        print(f"[CALC] Error evaluating '{expression}': {e}")
        return None


def extract_app_name(msg):
    """Extract the app name from an 'open X' command."""
    for prefix in ["open ", "launch ", "start ", "run "]:
        if prefix in msg:
            app_name = msg.split(prefix, 1)[1].strip().rstrip(".")
            # Remove trailing words like "app", "application", "please", "for me"
            for suffix in [" app", " application", " please", " for me", " now"]:
                app_name = app_name.replace(suffix, "")
            app_name = app_name.strip()
            if app_name in APP_REGISTRY:
                return app_name
            # Try partial match
            for key in APP_REGISTRY:
                if key in app_name or app_name in key:
                    return key
    return None


# ─── Website/URL Registry ────────────────────────────────────
WEBSITE_REGISTRY = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "whatsapp web": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "reddit": "https://www.reddit.com",
    "github": "https://github.com",
    "amazon": "https://www.amazon.in",
    "flipkart": "https://www.flipkart.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "chatgpt": "https://chat.openai.com",
    "linkedin": "https://www.linkedin.com",
    "wikipedia": "https://www.wikipedia.org",
    "stack overflow": "https://stackoverflow.com",
}


def detect_website_command(msg):
    """Detect if user wants to open a website or search the web."""
    # Check for "open youtube", "open google", etc.
    for trigger in ["open ", "go to ", "visit ", "launch ", "navigate to "]:
        if trigger in msg:
            rest = msg.split(trigger, 1)[1].strip().rstrip(".")
            # Remove extra words
            for suffix in [" please", " for me", " now", " in brave", " in chrome",
                          " in browser", " in a new tab", " in new tab", " on browser"]:
                rest = rest.replace(suffix, "")
            rest = rest.strip()

            # Check website registry
            for site_name, url in WEBSITE_REGISTRY.items():
                if site_name in rest or rest in site_name:
                    open_in_browser(url)
                    return ("website", f"Opening {site_name.title()} for you, sir.")

            # If it looks like a URL
            if "." in rest and " " not in rest:
                url = rest if rest.startswith("http") else f"https://{rest}"
                open_in_browser(url)
                return ("website", f"Opening {rest} for you, sir.")

    # Check for "search for X" or "google X"
    for trigger in ["search for ", "search ", "google ", "look up "]:
        if trigger in msg:
            query = msg.split(trigger, 1)[1].strip().rstrip(".")
            for suffix in [" please", " for me", " on google", " on the internet"]:
                query = query.replace(suffix, "")
            query = query.strip()
            if query:
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                open_in_browser(search_url)
                return ("search", f"Searching for {query}, sir.")

    # Direct website mentions without "open"
    for site_name, url in WEBSITE_REGISTRY.items():
        if msg.strip() == site_name or msg.strip() == f"open {site_name}":
            open_in_browser(url)
            return ("website", f"Opening {site_name.title()} for you, sir.")

    return None


def open_in_browser(url):
    """Open a URL in the default browser (Brave/Chrome/Edge)."""
    try:
        # Try Brave first (common install paths)
        brave_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for brave_path in brave_paths:
            if os.path.exists(brave_path):
                subprocess.Popen([brave_path, url])
                return True

        # Fallback to system default browser
        webbrowser.open(url)
        return True
    except Exception as e:
        print(f"[CMD] Failed to open URL '{url}': {e}")
        return False


def open_app(command):
    """Open an application on Windows."""
    try:
        if command == "brave":
            # Special handling for Brave browser
            brave_paths = [
                os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            ]
            for brave_path in brave_paths:
                if os.path.exists(brave_path):
                    subprocess.Popen([brave_path])
                    return True
            # If Brave not found, try default browser
            webbrowser.open("about:blank")
            return True

        if command.startswith("ms-") or command.startswith("microsoft.") or command.startswith("bing") or command.endswith(":"):
            os.startfile(command)
        elif command.startswith("explorer.exe"):
            subprocess.Popen(command, shell=True)
        else:
            subprocess.Popen(command, shell=True)
        return True
    except Exception as e:
        print(f"[CMD] Failed to open '{command}': {e}")
        return False

