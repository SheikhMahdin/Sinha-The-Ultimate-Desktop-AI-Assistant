"""
Combined Browser Automation
============================
Uses YOUR existing Chrome profile (logged-in sessions) via Selenium,
with the broad command support from the utility script.
Function names preserved from the original file for compatibility.
"""

import os
import sys
import time
import asyncio
import logging
import platform
import subprocess
import webbrowser
import socket
import requests
import keyboard
import re

from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from shutil import which

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

from groq import Groq
from dotenv import dotenv_values
from bs4 import BeautifulSoup
from rich import print

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ─── Environment ────────────────────────────────────────────────────────────

env_vars = dotenv_values(".env")
GroqAPIKey = env_vars.get("GroqAPIKey")
client = Groq(api_key=GroqAPIKey)

Username = os.environ.get("Username", "Assistant")

SystemChatBot = [
    {
        "role": "system",
        "content": (
            f"Hello, I am {Username}. You're a content writer. "
            "Write content like letters, code, applications, essays, notes, songs, poems, etc."
        ),
    }
]

messages = []  # Chat history for content writer

professional_responses = [
    "Your satisfaction is my top priority; feel free to reach out if there's anything else I can help you with.",
    "I'm at your service for any additional questions or support you may need — don't hesitate to ask.",
]

# ─── Data Classes ────────────────────────────────────────────────────────────

class TaskStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TaskResult:
    status: TaskStatus
    message: str
    error: Optional[str] = None


# ─── Chrome Profile Detection ────────────────────────────────────────────────

def get_chrome_profile_path() -> Optional[str]:
    """Automatically detect Chrome user data directory for the current OS."""
    system = platform.system()

    if system == "Windows":
        paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data"),
            os.path.join(os.environ.get("APPDATA", ""), "Google", "Chrome", "User Data"),
        ]
    elif system == "Darwin":
        paths = [os.path.expanduser("~/Library/Application Support/Google/Chrome")]
    else:
        paths = [
            os.path.expanduser("~/.config/google-chrome"),
            os.path.expanduser("~/.config/chromium"),
        ]

    for path in paths:
        if os.path.exists(path):
            logger.info(f"Found Chrome profile at: {path}")
            return path

    logger.warning("Chrome profile path not found — using default")
    return None


# ─── Fast Regex Command Parser ───────────────────────────────────────────────

class FastCommandParser:
    """Lightning-fast regex command parser."""

    def __init__(self):
        self.patterns = {
            "open_youtube":    re.compile(r"\bopen\s+youtube\b", re.I),
            "search_youtube":  re.compile(r"\bsearch\s+(?:youtube\s+)?for\s+[\"']?(.+?)[\"']?(?:\s+(?:and|,)|$)", re.I),
            "play_video":      re.compile(r"\bplay\s+(?:the\s+)?(?:first\s+)?video\b", re.I),
            "like_video":      re.compile(r"\blike\s+(?:the\s+)?(?:it|video)\b", re.I),
            "comment":         re.compile(r"\bcomment\s+[\"'](.+?)[\"']", re.I),
            "open_site":       re.compile(r"\b(?:open|go\s+to)\s+([a-zA-Z0-9.-]+\.com)\b", re.I),
            "google_search":   re.compile(r"\b(?:google\s+)?search\s+(?:for\s+)?[\"']?(.+?)[\"']?(?:\s+(?:and|,)|$)", re.I),
        }

    def parse(self, command: str) -> List[Dict[str, Any]]:
        actions = []

        if self.patterns["open_youtube"].search(command):
            actions.append({"action": "open_youtube"})

        m = self.patterns["search_youtube"].search(command)
        if m:
            actions.append({"action": "search_youtube", "query": m.group(1).strip(" ,")})

        if self.patterns["play_video"].search(command):
            actions.append({"action": "play_first_video"})

        if self.patterns["like_video"].search(command):
            actions.append({"action": "like_video"})

        m = self.patterns["comment"].search(command)
        if m:
            actions.append({"action": "post_comment", "text": m.group(1)})

        m = self.patterns["open_site"].search(command)
        if m and not actions:
            actions.append({"action": "open_website", "url": m.group(1)})

        m = self.patterns["google_search"].search(command)
        if m and "search_youtube" not in [a["action"] for a in actions]:
            actions.append({"action": "google_search", "query": m.group(1).strip(" ,")})

        return actions


# ─── Selenium Chrome Engine ──────────────────────────────────────────────────

class YourChromeEngine:
    """Opens Chrome with YOUR existing profile — already logged into everything."""

    def __init__(self, profile_name: str = "Default", user_data_dir: str = None):
        self.driver = None
        self.profile_name = profile_name
        self.user_data_dir = user_data_dir or get_chrome_profile_path()
        self._setup_driver()

    def _setup_driver(self):
        chrome_options = Options()

        if self.user_data_dir:
            chrome_options.add_argument(f"user-data-dir={self.user_data_dir}")
            chrome_options.add_argument(f"profile-directory={self.profile_name}")
            print(f"[green]✓ Using Chrome profile:[/green] {self.profile_name}")
            print(f"[green]✓ Location:[/green] {self.user_data_dir}")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("[green]✓ Browser opened with YOUR profile![/green]")
        except Exception as e:
            print(f"[red]✗ Error:[/red] {e}")
            print("\nTroubleshooting:")
            print("  1. Make sure Chrome is NOT already running")
            print("  2. Close all Chrome windows and try again")
            raise

    def fast_wait(self, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 5) -> Any:
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
        except TimeoutException:
            return None

    def instant_click(self, element) -> bool:
        try:
            element.click()
            return True
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                return False

    def fast_type(self, element, text: str) -> bool:
        try:
            element.clear()
            element.send_keys(text)
            return True
        except Exception:
            return False

    def close(self):
        if self.driver:
            self.driver.quit()


# ─── YouTube Automation ──────────────────────────────────────────────────────

class TurboYouTube:
    """Full YouTube automation via Selenium."""

    def __init__(self, engine: YourChromeEngine):
        self.engine = engine
        self.driver = engine.driver

    def open(self) -> TaskResult:
        try:
            self.driver.get("https://www.youtube.com")
            time.sleep(0.5)
            return TaskResult(TaskStatus.SUCCESS, "YouTube opened")
        except Exception as e:
            return TaskResult(TaskStatus.FAILED, "Failed to open YouTube", str(e))

    def search(self, query: str) -> TaskResult:
        try:
            search_box = (
                self.engine.fast_wait("input#search", timeout=3)
                or self.engine.fast_wait("input[name='search_query']", timeout=2)
            )
            if not search_box:
                return TaskResult(TaskStatus.FAILED, "Search box not found")
            self.engine.fast_type(search_box, query)
            search_box.send_keys(Keys.RETURN)
            time.sleep(1)
            return TaskResult(TaskStatus.SUCCESS, f"Searched YouTube: {query}")
        except Exception as e:
            return TaskResult(TaskStatus.FAILED, "YouTube search failed", str(e))

    def play_first(self) -> TaskResult:
        try:
            time.sleep(1)
            videos = self.driver.find_elements(By.CSS_SELECTOR, "a#video-title")
            if not videos:
                return TaskResult(TaskStatus.FAILED, "No videos found")
            self.engine.instant_click(videos[0])
            time.sleep(1)
            return TaskResult(TaskStatus.SUCCESS, "Playing first video")
        except Exception as e:
            return TaskResult(TaskStatus.FAILED, "Play failed", str(e))

    def like(self) -> TaskResult:
        try:
            time.sleep(1)
            like_btn = (
                self.engine.fast_wait("like-button-view-model button", timeout=3)
                or self.engine.fast_wait("ytd-toggle-button-renderer button", timeout=2)
            )
            if like_btn:
                self.engine.instant_click(like_btn)
                return TaskResult(TaskStatus.SUCCESS, "Video liked")
            return TaskResult(TaskStatus.FAILED, "Like button not found")
        except Exception as e:
            return TaskResult(TaskStatus.FAILED, "Like failed", str(e))

    def comment(self, text: str) -> TaskResult:
        try:
            self.driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)
            comment_box = self.engine.fast_wait("div#placeholder-area", timeout=3)
            if not comment_box:
                return TaskResult(TaskStatus.FAILED, "Comment box not found")
            self.engine.instant_click(comment_box)
            time.sleep(0.5)
            input_field = self.engine.fast_wait("div#contenteditable-root", timeout=2)
            if input_field:
                input_field.send_keys(text)
                time.sleep(0.5)
                post_btn = self.engine.fast_wait("ytd-button-renderer#submit-button button", timeout=2)
                if post_btn:
                    self.engine.instant_click(post_btn)
                    return TaskResult(TaskStatus.SUCCESS, "Comment posted!")
            return TaskResult(TaskStatus.FAILED, "Comment field not found")
        except Exception as e:
            return TaskResult(TaskStatus.FAILED, "Comment failed", str(e))


# ─── Google Search (plain browser) ──────────────────────────────────────────

def GoogleSearch(Topic: str) -> bool:
    """Open a Google search in the default browser."""
    url = f"https://www.google.com/search?q={Topic}"
    webbrowser.open(url)
    return True


# ─── YouTube Search (plain browser) ─────────────────────────────────────────

def YouTubeSearch(Topic: str) -> bool:
    """Open a YouTube search results page in the default browser."""
    url = f"https://www.youtube.com/results?search_query={Topic}"
    webbrowser.open(url)
    return True


# ─── Play YouTube (pywhatkit) ─────────────────────────────────────────────────

def PlayYoutube(query: str) -> bool:
    """Play a YouTube video matching the query (opens best result)."""
    try:
        from pywhatkit import playonyt
        playonyt(query)
    except ImportError:
        YouTubeSearch(query)
    return True


# ─── Content Writer ──────────────────────────────────────────────────────────

def Content(Topic: str) -> bool:
    """Generate AI content and save it to a .txt file, then open it."""

    def _open_editor(file_path: str):
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["notepad.exe", file_path])
        elif system == "Darwin":
            subprocess.Popen(["open", "-t", file_path])
        else:
            editors = ["gedit", "nano", "vi"]
            for ed in editors:
                if which(ed):
                    subprocess.Popen([ed, file_path])
                    break

    def _content_writer_ai(prompt: str) -> str:
        messages.append({"role": "user", "content": prompt})
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=SystemChatBot + messages,
            max_tokens=2048,
            temperature=0.7,
            top_p=1,
            stream=True,
            stop=None,
        )
        answer = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                answer += chunk.choices[0].delta.content
        answer = answer.replace("</s>", "")
        messages.append({"role": "assistant", "content": answer})
        return answer

    topic_clean = Topic.replace("Content ", "").strip()
    content_text = _content_writer_ai(topic_clean)

    os.makedirs("Data", exist_ok=True)
    filename = topic_clean.lower().replace(" ", "") + ".txt"
    file_path = os.path.join("Data", filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content_text)

    _open_editor(file_path)
    return True


# ─── Open App / Website ──────────────────────────────────────────────────────

def _get_official_website(app_name: str) -> str:
    """Use DuckDuckGo to find the official website for an app."""
    if not DDGS_AVAILABLE:
        return ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(app_name + " official site", max_results=5))
            for r in results:
                url = r.get("href") or r.get("url", "")
                if url.startswith("http"):
                    return url
    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")
    return ""


def OpenApp(app: str, sess=None) -> bool:
    """
    Open an application or its website.
    Priority: native app launch → official website (DDG) → domain guessing → Google fallback.
    """
    if sess is None:
        sess = requests.session()

    app = app.strip()
    if app.lower().startswith("open "):
        app = app[5:].strip()

    # 1. Try launching natively
    def _try_launch(name: str) -> bool:
        system = platform.system()
        if system == "Windows":
            try:
                os.startfile(name)
                return True
            except Exception:
                pass
        if system == "Darwin":
            try:
                subprocess.Popen(["open", "-a", name])
                return True
            except Exception:
                pass
        if which(name):
            try:
                subprocess.Popen([name])
                return True
            except Exception:
                pass
        return False

    if _try_launch(app):
        print(f"[green]✓ Launched app:[/green] {app}")
        return True

    # 2. Try official website via DuckDuckGo
    official = _get_official_website(app)
    if official:
        try:
            webbrowser.open(official)
            print(f"[green]✓ Opened official site:[/green] {official}")
            return True
        except Exception as e:
            logger.warning(f"Could not open {official}: {e}")

    # 3. Try guessing the domain
    def _domain_resolves(domain: str, timeout: int = 2) -> bool:
        try:
            socket.setdefaulttimeout(timeout)
            socket.gethostbyname(domain)
            return True
        except Exception:
            return False

    candidates = [app, f"www.{app}"]
    for tld in ["com", "org", "net", "io", "bd", "gov"]:
        candidates += [f"{app}.{tld}", f"www.{app}.{tld}"]

    for dom in candidates:
        if _domain_resolves(dom):
            url = dom if dom.startswith("http") else "https://" + dom
            try:
                webbrowser.open(url)
                print(f"[green]✓ Opened:[/green] {url}")
                return True
            except Exception as e:
                logger.warning(f"Could not open {url}: {e}")

    # 4. Google fallback
    try:
        fallback = f"https://www.google.com/search?q={app}"
        webbrowser.open(fallback)
        print(f"[yellow]⚠ Fallback search:[/yellow] {fallback}")
        return True
    except Exception as e:
        logger.error(f"Fallback failed: {e}")
        return False


# ─── Close App ───────────────────────────────────────────────────────────────

def CloseApp(app: str) -> bool:
    """Close a running application by name."""
    app = app.strip()
    if app.lower() == "chrome":
        return False  # Skip Chrome to avoid closing the automation browser
    try:
        from AppOpener import close
        close(app, match_closest=True, output=True, throw_error=True)
        return True
    except Exception:
        return False


# ─── System Controls ─────────────────────────────────────────────────────────

def System(command: str) -> bool:
    """Handle system-level commands: mute, unmute, volume up/down."""
    cmd = command.strip().lower()
    key_map = {
        "mute":        "volume mute",
        "unmute":      "volume mute",
        "volume up":   "volume up",
        "volume down": "volume down",
    }
    if cmd in key_map:
        keyboard.press_and_release(key_map[cmd])
        return True
    logger.warning(f"Unknown system command: {command}")
    return False


# ─── Main Automation Engine ──────────────────────────────────────────────────

class YourBrowserAutomation:
    """
    Combined automation engine:
    - Full Selenium control of YOUR Chrome profile
    - Broad command support (YouTube, Google, apps, system, content)
    """

    def __init__(self, profile_name: str = "Default", user_data_dir: str = None):
        self.engine = YourChromeEngine(profile_name, user_data_dir)
        self.youtube = TurboYouTube(self.engine)
        self.parser = FastCommandParser()

    async def execute(self, command: str) -> List[TaskResult]:
        """Parse and execute a natural-language browser command."""
        results = []
        actions = self.parser.parse(command)

        if not actions:
            results.append(TaskResult(TaskStatus.FAILED, "Could not parse command"))
            return results

        for action_data in actions:
            action = action_data.get("action")
            try:
                if action == "open_youtube":
                    result = self.youtube.open()

                elif action == "search_youtube":
                    result = self.youtube.search(action_data["query"])

                elif action == "play_first_video":
                    result = self.youtube.play_first()

                elif action == "like_video":
                    result = self.youtube.like()

                elif action == "post_comment":
                    result = self.youtube.comment(action_data["text"])

                elif action == "open_website":
                    url = action_data["url"]
                    if not url.startswith("http"):
                        url = "https://" + url
                    self.engine.driver.get(url)
                    result = TaskResult(TaskStatus.SUCCESS, f"Opened {url}")

                elif action == "google_search":
                    query = action_data["query"]
                    url = f"https://www.google.com/search?q={query}"
                    self.engine.driver.get(url)
                    result = TaskResult(TaskStatus.SUCCESS, f"Searched Google: {query}")

                else:
                    result = TaskResult(TaskStatus.FAILED, f"Unknown action: {action}")

                results.append(result)

            except Exception as e:
                results.append(TaskResult(TaskStatus.FAILED, f"Action failed: {action}", str(e)))

        return results

    def cleanup(self):
        self.engine.close()


# ─── TranslateAndExecute (matches original signature) ────────────────────────

async def TranslateAndExecute(commands: list[str]):
    """
    Translate a list of command strings and execute them.
    Matches the original function signature used across the project.
    """
    funcs = []

    for command in commands:
        command = command.strip()

        if command.startswith("open "):
            if command in ("open it", "open file"):
                continue
            fun = asyncio.to_thread(OpenApp, command.removeprefix("open "))
            funcs.append(fun)

        elif command.startswith("close "):
            fun = asyncio.to_thread(CloseApp, command.removeprefix("close "))
            funcs.append(fun)

        elif command.startswith("play "):
            fun = asyncio.to_thread(PlayYoutube, command.removeprefix("play "))
            funcs.append(fun)

        elif command.startswith("content "):
            fun = asyncio.to_thread(Content, command.removeprefix("content "))
            funcs.append(fun)

        elif command.startswith("google search "):
            fun = asyncio.to_thread(GoogleSearch, command.removeprefix("google search "))
            funcs.append(fun)

        elif command.startswith("youtube search "):
            fun = asyncio.to_thread(YouTubeSearch, command.removeprefix("youtube search "))
            funcs.append(fun)

        elif command.startswith("system "):
            fun = asyncio.to_thread(System, command.removeprefix("system "))
            funcs.append(fun)

        elif command.startswith("general"):
            pass  # Handled elsewhere

        elif command.startswith("realtime "):
            pass  # Handled elsewhere

        else:
            print(f"[yellow]No function found for:[/yellow] {command}")

    results = await asyncio.gather(*funcs)

    for result in results:
        yield result


# ─── Automation (matches original signature) ─────────────────────────────────

async def Automation(commands: list[str]) -> bool:
    """
    Entry point called from other modules.
    Matches the original Automation() signature exactly.
    """
    async for _ in TranslateAndExecute(commands):
        pass
    return True


# ─── Demo ─────────────────────────────────────────────────────────────────────

async def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║         Combined Automation — YOUR Chrome Profile        ║
╚══════════════════════════════════════════════════════════╝

✓ Your YouTube / Google login
✓ Your bookmarks & history
✓ Your extensions
✓ Full Selenium control

NOTE: Close ALL Chrome windows before running!
    """)

    input("Press Enter to start...")

    system = YourBrowserAutomation(profile_name="Default")

    try:
        command = "open youtube, search for python programming, play first video, like it"
        print(f"\n🚀 Executing: {command}\n")

        start = time.time()
        results = await system.execute(command)
        elapsed = time.time() - start

        for i, result in enumerate(results, 1):
            icon = "[green]✓[/green]" if result.status == TaskStatus.SUCCESS else "[red]✗[/red]"
            print(f"{icon} {i}. {result.message}")

        print(f"\n⚡ Done in {elapsed:.2f}s")
        input("\nPress Enter to close...")

    finally:
        system.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
