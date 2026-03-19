# Import required libraries
from AppOpener import close, open as appopen  # Import functions to open and close apps.
from webbrowser import open as webopen # Import web browser functionality.
from pywhatkit import search, playonyt # Import functions for Google search and YouTube playback.
from dotenv import dotenv_values # Import dotenv to manage environment variables.
from bs4 import BeautifulSoup # Import BeautifulSoup for parsing HTML content.
from rich import print # Import rich for styled console output.
from groq import Groq # Import Groq for AI chat functionalities.
import webbrowser # Import webbrowser for open opening URLS.
import subprocess # Import subprocess for interacting with the system.
import requests # Import requests for making HTTP reque requests.
import keyboard # Import keyboard for keyboard-related actions.
import asyncio # Import asyncio for asynchronous programming.
import os # Import os for operating system functionalities.

# Load environment variables from the .env file.

env_vars=dotenv_values(".env")
GroqAPIKey=env_vars.get("GroqAPIKey") # Retrieve the Groq API key.

# Define CSS classes for parsing specific elements in HTML content.
classes = ["zCubwf", "hgKElc", "LTK00 SY7ric", "ZOLCW", "gsrt vk_bk FzvWSb YwPhnf", "pclqee", "tw-Data-text tw-text-small tw-ta",
            "IZ6rdc", "05uR6d LTK00", "vlzY6d", "webanswers-webanswers_table_webanswers-table", "dDoNo ikb4Bb gsrt", "sXLa0e",
            "LWkfKe", "VQF4g", "qv3Wpe", "kno-rdesc", "SPZz6b"]

# Define a user-agent for making web requests.
useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'

# Initialize the Groq client with the API key.
client = Groq(api_key=GroqAPIKey)

# Predefined professional responses for user interactions.
professional_responses = [
    "Your satisfaction is my top priority; feel free to reach out if there's anything else I can help you with.",
    "I'm at your service for any additional questions or support you may need-don't hesitate to ask.",
]

# List to store chatbot messages.
messages = []

# System message to provide context to the chatbot.
SystemChatBot = [{"role": "system", "content": f"Hello, I am {os.environ['Username']}, You're a content writer. You have to write content like letters, codes, applications, essays, notes, songs, poems etc."}]

# Function to perform a Google search.
def GoogleSearch(Topic):
    search(Topic) # Use pywhatkit's search function to perform a Google search.
    return True # Indicate success.

# Function to generate content using AI and save it to a file.
def Content(Topic):

    # Nested function to open a file in Notepad.
    def OpenNotepad (File):
        default_text_editor = 'notepad.exe' # Default text editor.
        subprocess.Popen([default_text_editor, File]) # Open the file in Notepad.

    # Nested function to generate content using the AI chatbot.
    def ContentWriterAI(prompt):
        messages.append({"role": "user", "content": f"{prompt}"})  # Add the user's prompt to messages.

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",# Specify the AI model,.....old model: "mixtral-8x7b-32768"
            messages = SystemChatBot + messages,  # Include system instructions and chat history.
            max_tokens=2048,  # Limit the maximum tokens in the response.
            temperature=0.7,  # Adjust response randomness.
            top_p=1,  # Use nucleus sampling for response diversity.
            stream=True,  # Enable streaming response.
            stop=None  # Allow the model to determine stopping conditions.
        )

        Answer = ""  # Initialize an empty string for the response.

        # Process streamed response chunks.
        for chunk in completion:
            if chunk.choices[0].delta.content:  # Check for content in the current chunk.
                Answer += chunk.choices[0].delta.content  # Append the content to the answer.

        Answer = Answer.replace("</s>", "")  # Remove unwanted tokens from the response.
        messages.append({"role": "assistant", "content": Answer})  # Add the AI's response to messages.
        return Answer

    Topic: str = Topic.replace("Content ", "")  # Remove "Content" from the topic.
    ContentByAI = ContentWriterAI(Topic)  # Generate content using AI.

    # Save the generated content to a text file.
    with open(rf"Data\{Topic.lower().replace(' ', '')}.txt", "w", encoding="utf-8") as file:
        file.write(ContentByAI)  # Write the content to the file.
        file.close()

    OpenNotepad(rf"Data\{Topic.lower().replace(' ', '')}.txt")  # Open the file in Notepad.
    return True  # Indicate success.

# Function to search for a topic on YouTube.
def YouTubeSearch(Topic):
        Url4Search = f"https://www.youtube.com/results?search_query={Topic}"  # Construct the YouTube search URL.
        webbrowser.open(Url4Search)  # Open the search URL in a web browser.
        return True  # Indicate success.

# Function to play a video on YouTube.
def PlayYoutube(query):
    playonyt(query)  # Use pywhatkit's playonyt function to play the video.
    return True  # Indicate success.



# --- Add this helper inside your OpenApp.py or above OpenApp function ---


import os
import sys
import webbrowser
import socket
import subprocess
import requests
from shutil import which

# --- Step 0: Helper function to get official site from LLM ---
from duckduckgo_search import DDGS

def GetOfficialWebsite(app_name: str) -> str:
    """
    Gets the official website for an app/service using DuckDuckGo search.
    Free, no API key required.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(app_name + " official site", max_results=5))
            for r in results:
                url = r.get("href") or r.get("url")
                if url and url.startswith("http"):
                    return url
    except Exception as e:
        print(f"[Search Error] {e}")
    return ""



def OpenApp(app, sess=requests.session()):
    """
    Attempts to open a specified application. 
    If unsuccessful, resolves and opens a corresponding website.
    """

    app = app.strip()
    if app.lower().startswith("open "):
        app = app[5:].strip()

    # --- Step 1: Try to launch as application ---
    def try_launch_app(app_name: str) -> bool:
        if sys.platform.startswith("win"):  # Windows
            try:
                os.startfile(app_name)
                return True
            except Exception:
                pass
        if sys.platform.startswith("darwin"):  # macOS
            try:
                subprocess.Popen(["open", "-a", app_name])
                return True
            except Exception:
                pass
        if which(app_name):  # Linux / Unix
            try:
                subprocess.Popen([app_name])
                return True
            except Exception:
                pass
        return False

    # --- Step 2: Try official site via LLM ---
    official_site = GetOfficialWebsite(app)
    if official_site:
        try:
            webbrowser.open(official_site)
            print(f"[Official Website Opened] {official_site}")
            return True
        except Exception as e:
            print(f"[Error Opening Official Website] {official_site} -> {e}")

    # --- Step 3: Try to resolve domain manually ---
    def domain_resolves(domain: str, timeout=2) -> bool:
        try:
            socket.setdefaulttimeout(timeout)
            socket.gethostbyname(domain)
            return True
        except Exception:
            return False

    candidates = [app, f"www.{app}"]
    tlds = ["com", "org", "net", "io", "bd", "gov"]
    for tld in tlds:
        candidates.append(f"{app}.{tld}")
        candidates.append(f"www.{app}.{tld}")

    for dom in candidates:
        if domain_resolves(dom):
            url = dom if dom.startswith(("http://", "https://")) else "https://" + dom
            try:
                webbrowser.open(url)
                print(f"[Website Opened] {url}")
                return True
            except Exception as e:
                print(f"[Error Opening Website] {url} -> {e}")

    # --- Step 4: Fallback search ---
    try:
        search_url = f"https://www.google.com/search?q={app}"
        webbrowser.open(search_url)
        print(f"[Fallback Search] {search_url}")
        return True
    except Exception as e:
        print(f"[Error Search Fallback] {e}")
        return False


# Example usage:
# OpenApp("youtube")


#penApp("youtube")
    



# Function to close an application.
def CloseApp(app):


    if app.strip() == "chrome":
        pass # Skip if the app is Chrome.
    else:
        try:
            close(app, match_closest =True, output=True, throw_error=True) # Attempt to close the app.
            return True # Indicate success.
        except:
            return False # Indicate failure.

# Function to execute system-level commands.
def System(command):

    # Nested function to mute the system volume.
    def mute():
        keyboard.press_and_release("volume mute") # Simulate the mute key press.

    # Nested function to unmute the system volume.
    def unmute():
        keyboard.press_and_release("volume mute") # Simulate the unmute key press.

    # Nested function to increase the system volume.
    def volume_up():
        keyboard.press_and_release("volume up") # Simulate the volume up key press.

    # Nested function to decrease the system volume.
    def volume_down():
        keyboard.press_and_release("volume down") # Simulate the volume down key press.

    # Execute the appropriate command.
    if command == "mute":
        mute()
    elif command == "unmute":
        unmute()
    elif command == "volume up":
        volume_up()
    elif command == "volume down":
        volume_down()

    return True # Indicate success.

# Asynchronous function to translate and execute user commands.
async def TranslateAndExecute(commands: list [str]):

    funcs = [] # List to store asynchronous tasks.

    for command in commands:

        if command.startswith("open "): # Handle "open" commands.

            if "open it" in command: # Ignore "open it" commands.
                pass

            if "open file" == command: # Ignore "open file" commands.
                pass

            else:
                fun = asyncio.to_thread(OpenApp, command.removeprefix("open ")) # Schedule app opening.
                funcs.append(fun)

        elif command.startswith("general"): # Placeholder for general commands.
            pass

        elif command.startswith("realtime "): # Placeholder for real-time commands.
            pass

        elif command.startswith("close"): # Handle "close" commands.
            fun = asyncio.to_thread (CloseApp, command.removeprefix("close")) # Schedule app closing.
            funcs.append(fun)

        elif command.startswith("play "): # Handle "play" commands.
            fun = asyncio.to_thread (PlayYoutube, command.removeprefix("play")) # Schedule YouTube playback.
            funcs.append(fun)

        elif command.startswith("content"): # Handle "content" commands.
            fun = asyncio.to_thread(Content, command.removeprefix("content")) # Schedule content creation.
            funcs.append(fun)

        elif command.startswith("google search "): # Handle Google search commands.
            fun = asyncio.to_thread(GoogleSearch, command.removeprefix("google search ")) # Schedule Google search.
            funcs.append(fun)

        elif command.startswith("youtube search "): # Handle YouTube search commands.
            fun = asyncio.to_thread(YouTubeSearch, command.removeprefix("youtube search ")) # Schedule YouTube search.
            funcs.append(fun)

        elif command.startswith("system"): # Handle system commands.
            fun = asyncio.to_thread(System, command.removeprefix("system ")) # Schedule system command.
            funcs.append(fun)

        else:
            print (f"No Function Found. For {command}") # Print an error for unrecognized commands.

    results = await asyncio.gather(*funcs) # Execete all tasks concurrently.

    for result in results:
        if isinstance(result, str):
            yield result
        else:
            yield result

# Asynchronous function to automate command execution.
async def Automation (commands: list[str]):
    async for result in TranslateAndExecute(commands): # Translate and execute commands.
        pass

    return True # Indicate success.


if __name__ == "__main__":
    asyncio.run(Content("Content how to create a youtube cahnnel"))



"""def OpenApp(app, sess=requests.session()):
    
    '''Attempts to open a specified application. If unsuccessful, performs a Bing search
    and opens the most relevant webpage.
    
    Args:
        app (str): Name of the application to open.
        sess (requests.Session, optional): A session object for making HTTP requests. Defaults to a new session.
    
    Returns:
        bool: True if an application or webpage was opened successfully, False otherwise.'''
    
    try:
        # Attempt to open the application
        appopen(app, match_closest=True, output=True, throw_error=True)
        return True
    except Exception:
        # Extract links from HTML content
        def extract_links(html):
            if not html:
                return []
            soup = BeautifulSoup(html, 'html.parser')
            return [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith("http")]
        
        # Perform a Bing search
        def search_bing(query):
            url = f"https://www.bing.com/search?q={query}"
            headers = {"User-Agent": "Mozilla/5.0"}  
            time.sleep(2)  
            response = sess.get(url, headers=headers)
            return response.text if response.status_code == 200 else None
        
        html = search_bing(app)
        
        if html:
            links = extract_links(html)
            if links:
                webbrowser.open(links[0])  # Open the first valid search result
                return True
    
    return False  # Indicate failure




#penApp("youtube")"""