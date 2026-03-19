from Frontend.GUIold import (
    GraphicalUserInterface, SetAssistantStatus, ShowTextToScreen,
    TempDirectoryPath, SetMicrophoneStatus, AnswerModifier,
    QueryModifier, GetMicrophoneStatus, GetAssistantStatus
)
from Backend.Model import FirstLayerDMM
from Backend.RealtimeSearchEngine import RealtimeSearchEngine
from Backend.Automation import Automation
from Backend.SpeechToText import SpeechRecognition
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech
from dotenv import dotenv_values
from asyncio import run
from time import sleep
import subprocess
import threading
import json
import os
import atexit
import logging
import mtranslate as mt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================
MIC_ON = "True"
MIC_OFF = "False"
STATUS_AVAILABLE = "Available ..."
STATUS_LISTENING = "Listening ..."
STATUS_THINKING = "Thinking ..."
STATUS_SEARCHING = "Searching ..."
STATUS_ANSWERING = "Answering ..."
STATUS_SLEEPING = "Sleeping ... (Say 'Sinha' to wake)"
STATUS_WAKING = "Waking up ..."
WAKE_WORD = "sinha"
SLEEP_COMMAND = "sleep"

FUNCTIONS = ["open", "close", "play", "system", "content", "google search", "youtube search"]
IMAGE_KEYWORDS = ["generate", "create image", "draw", "make image", "picture of"]

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================
def load_environment_variables():
    """Load and validate environment variables from .env file"""
    try:
        env_vars = dotenv_values(".env")
        
        username = env_vars.get("Username")
        assistant_name = env_vars.get("Assistantname")
        input_language = env_vars.get("InputLanguage", "en")
        
        if not username:
            raise ValueError("Username not set in .env file")
        if not assistant_name:
            raise ValueError("Assistantname not set in .env file")
        
        logger.info(f"Environment loaded: User={username}, Assistant={assistant_name}, Language={input_language}")
        return username, assistant_name, input_language
    
    except Exception as e:
        logger.error(f"Failed to load environment variables: {e}")
        raise

Username, Assistantname, InputLanguage = load_environment_variables()
DefaultMessage = f'''{Username} : Hello {Assistantname}, How are you?
{Assistantname} : Welcome {Username}. I am doing well. How may i help you?'''

# ============================================================================
# GLOBAL STATE MANAGEMENT
# ============================================================================
current_dir = os.getcwd()
subprocesses = []
subprocess_lock = threading.Lock()

# Thread-safe sleep state management
sleep_lock = threading.Lock()
is_sleeping = True

def set_sleep_state(sleeping):
    """Thread-safe setter for sleep state"""
    global is_sleeping
    with sleep_lock:
        is_sleeping = sleeping
        logger.info(f"Sleep state changed to: {sleeping}")

def get_sleep_state():
    """Thread-safe getter for sleep state"""
    with sleep_lock:
        return is_sleeping

# ============================================================================
# CLEANUP HANDLERS
# ============================================================================
def cleanup_subprocesses():
    """Cleanup all running subprocesses on exit"""
    with subprocess_lock:
        for proc in subprocesses:
            try:
                if proc.poll() is None:  # Still running
                    logger.info(f"Terminating subprocess PID: {proc.pid}")
                    proc.terminate()
                    proc.wait(timeout=5)
            except Exception as e:
                logger.error(f"Error cleaning up subprocess: {e}")
                try:
                    proc.kill()
                except:
                    pass

atexit.register(cleanup_subprocesses)

# ============================================================================
# TRANSLATION
# ============================================================================
def universal_translator(text):
    """Translate text into the specified input language"""
    if InputLanguage == "en" or not text:
        return text
    
    try:
        translated_text = mt.translate(text, InputLanguage, "auto")
        return translated_text.capitalize()
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text

# ============================================================================
# FILE OPERATIONS
# ============================================================================
def ensure_directory_exists(directory):
    """Create directory if it doesn't exist"""
    try:
        os.makedirs(directory, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {e}")

def read_chatlog_json():
    """Read and parse the chat log JSON file"""
    chatlog_path = os.path.join(current_dir, 'Data', 'ChatLog.json')
    
    try:
        ensure_directory_exists(os.path.dirname(chatlog_path))
        
        if not os.path.exists(chatlog_path):
            logger.warning("ChatLog.json not found, creating empty log")
            with open(chatlog_path, 'w', encoding='utf-8') as file:
                json.dump([], file)
            return []
        
        with open(chatlog_path, 'r', encoding='utf-8') as file:
            chatlog_data = json.load(file)
            return chatlog_data
    
    except json.JSONDecodeError as e:
        logger.error(f"Corrupted ChatLog.json: {e}")
        return []
    except Exception as e:
        logger.error(f"Error reading ChatLog.json: {e}")
        return []

def show_default_chat_if_no_chats():
    """Display default chat message if no chat history exists, without overwriting existing data"""
    try:
        database_path = TempDirectoryPath('Database.data')
        responses_path = TempDirectoryPath('Responses.data')

        # Check if Database.data exists and has content
        if os.path.exists(database_path):
            with open(database_path, 'r', encoding='utf-8') as file:
                data = file.read()
            
            if len(data.strip()) > 0:
                # There is already chat history, no need to show default message
                logger.info("Chat history exists, skipping default message")
                return

        # If Database.data does not exist or is empty, show default message safely
        ensure_directory_exists(os.path.dirname(database_path))
        
        with open(database_path, 'w', encoding='utf-8') as file:
            file.write("")  # Keep Database.data empty initially

        with open(responses_path, 'w', encoding='utf-8') as file:
            file.write(DefaultMessage)  # Write default message to display

        logger.info("No chat history found, displaying default message")

    except Exception as e:
        logger.error(f"Error in show_default_chat_if_no_chats: {e}")


def chatlog_integration():
    """Convert JSON chat log to formatted text for display"""
    try:
        json_data = read_chatlog_json()
        formatted_chatlog = ""
        
        for entry in json_data:
            role = entry.get("role", "")
            content = entry.get("content", "")
            
            if role == "user":
                formatted_chatlog += f"{Username} : {content}\n"
            elif role == "assistant":
                formatted_chatlog += f"{Assistantname} : {content}\n"
        
        with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
            file.write(AnswerModifier(formatted_chatlog))
        
        logger.info("Chat log integration completed")
    
    except Exception as e:
        logger.error(f"Error in chatlog_integration: {e}")

def show_chats_on_gui():
    """Display chat history on the GUI"""
    try:
        database_path = TempDirectoryPath('Database.data')
        
        if not os.path.exists(database_path):
            logger.warning("Database.data not found")
            return
        
        with open(database_path, "r", encoding='utf-8') as file:
            data = file.read()
        
        if len(str(data)) > 0:
            lines = data.split('\n')
            result = '\n'.join(lines)
            
            with open(TempDirectoryPath('Responses.data'), "w", encoding='utf-8') as file:
                file.write(result)
            
            logger.info("Chat history displayed on GUI")
    
    except Exception as e:
        logger.error(f"Error in show_chats_on_gui: {e}")

# ============================================================================
# ANSWER DISPLAY (Centralized)
# ============================================================================
def display_answer(answer):
    """Centralized function to display and speak answers with translation"""
    try:
        if InputLanguage != "en":
            answer = universal_translator(answer)
        
        ShowTextToScreen(f" {Assistantname} : {answer}")
        SetAssistantStatus(STATUS_ANSWERING)
        TextToSpeech(answer)
        
        return True
    
    except Exception as e:
        logger.error(f"Error in display_answer: {e}")
        return False

# ============================================================================
# IMAGE GENERATION
# ============================================================================
def start_image_generation(query):
    """Start image generation subprocess"""
    try:
        image_data_path = os.path.join('Frontend', 'Files', 'ImageGeneration.data')
        ensure_directory_exists(os.path.dirname(image_data_path))
        
        with open(image_data_path, "w", encoding='utf-8') as file:
            file.write(f"{query},True")
        
        logger.info(f"Image generation data written: {query}")
        
        image_script = os.path.join('Backend', 'ImageGeneration.py')
        
        if not os.path.exists(image_script):
            logger.error(f"ImageGeneration.py not found at {image_script}")
            return False
        
        proc = subprocess.Popen(
            ['python', image_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            shell=False
        )
        
        with subprocess_lock:
            subprocesses.append(proc)
        
        logger.info(f"ImageGeneration.py subprocess started (PID: {proc.pid})")
        return True
    
    except Exception as e:
        logger.error(f"Error starting ImageGeneration.py: {e}")
        return False

# ============================================================================
# INITIALIZATION
# ============================================================================
def initial_execution():
    """Initialize the assistant on startup"""
    try:
        logger.info("Starting initial execution")
        
        SetMicrophoneStatus(MIC_OFF)
        ShowTextToScreen("")
        show_default_chat_if_no_chats()
        chatlog_integration()
        show_chats_on_gui()
        SetAssistantStatus(STATUS_SLEEPING)
        
        logger.info("Initial execution completed - System in sleep mode")
    
    except Exception as e:
        logger.error(f"Error in initial_execution: {e}")

# ============================================================================
# WAKE WORD DETECTION (FIXED)
# ============================================================================
def listen_for_wake_word():
    """Listen for wake word when in sleep mode - NO MORE FORCED MIC OFF"""
    try:
        SetAssistantStatus(STATUS_SLEEPING)
        query = SpeechRecognition()
        
        if not query:
            return False
        
        query_lower = query.strip().lower()
        logger.info(f"Wake word listening heard: '{query}'")
        
        if WAKE_WORD in query_lower:
            set_sleep_state(False)
            SetMicrophoneStatus(MIC_ON)
            SetAssistantStatus(STATUS_WAKING)
            
            wake_message = "Yes, I'm awake now!"
            display_answer(wake_message)
            
            logger.info("Wake word detected - Assistant activated")
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error in listen_for_wake_word: {e}")
        return False

# ============================================================================
# MAIN EXECUTION LOGIC
# ============================================================================
def main_execution():
    """Main logic for processing user queries"""
    try:
        task_execution = False
        image_execution = False
        image_generation_query = ""
        
        SetAssistantStatus(STATUS_LISTENING)
        query = SpeechRecognition()
        
        if GetMicrophoneStatus() != MIC_ON:
            return False
        
        if not query:
            return False
        
        if SLEEP_COMMAND in query.lower():
            set_sleep_state(True)
            SetMicrophoneStatus(MIC_OFF)
            
            sleep_message = "Going to sleep. Say 'Sinha' to wake me up."
            ShowTextToScreen(f" {Assistantname} : {sleep_message}")
            SetAssistantStatus(STATUS_ANSWERING)
            TextToSpeech(sleep_message)
            
            logger.info("Sleep command received - Entering sleep mode")
            return True
        
        ShowTextToScreen(f" {Username} : {query}")
        SetAssistantStatus(STATUS_THINKING)
        
        decision = FirstLayerDMM(query)
        logger.info(f"Decision: {decision}")
        
        has_general = any(i for i in decision if i.startswith("general"))
        has_realtime = any(i for i in decision if i.startswith("realtime"))
        
        merged_query = " and ".join(
            [" ".join(i.split()[1:]) for i in decision 
             if i.startswith("general") or i.startswith("realtime")]
        )
        
        for query_item in decision:
            if any(keyword in query_item.lower() for keyword in IMAGE_KEYWORDS):
                image_generation_query = str(query_item)
                image_execution = True
                logger.info(f"Image generation detected: {image_generation_query}")
                break
        
        for query_item in decision:
            if not task_execution:
                if any(query_item.startswith(func) for func in FUNCTIONS):
                    run(Automation(list(decision)))
                    task_execution = True
                    break
        
        if image_execution:
            start_image_generation(image_generation_query)
        
        if (has_general and has_realtime) or has_realtime:
            SetAssistantStatus(STATUS_SEARCHING)
            answer = RealtimeSearchEngine(merged_query)
            display_answer(answer)
            return True
        
        for query_item in decision:
            if "general" in query_item:
                SetAssistantStatus(STATUS_THINKING)
                query_final = query_item.replace("general", "").strip()
                logger.info(f"General query: {query_final}")
                
                answer = ChatBot(query_final)
                display_answer(answer)
                return True
            
            elif "realtime" in query_item:
                SetAssistantStatus(STATUS_SEARCHING)
                query_final = query_item.replace("realtime", "").strip()
                
                answer = RealtimeSearchEngine(QueryModifier(query_final))
                display_answer(answer)
                return True
            
            elif "exit" in query_item:
                exit_message = "Okay, Bye!"
                display_answer(exit_message)
                
                logger.info("Exit command received")
                cleanup_subprocesses()
                os._exit(0)
        
        return False
    
    except Exception as e:
        logger.error(f"Error in main_execution: {e}")
        return False

# ============================================================================
# THREADING
# ============================================================================
def first_thread():
    """Main thread for handling voice commands and wake word detection"""
    logger.info("First thread started")
    
    while True:
        try:
            if get_sleep_state():
                # NEW: Allow manual wake-up via GUI mic button
                if GetMicrophoneStatus() == MIC_ON:
                    set_sleep_state(False)
                    SetAssistantStatus(STATUS_WAKING)
                    display_answer("Yes, I'm awake now!")
                    logger.info("Manual wake-up via GUI microphone button")
                else:
                    listen_for_wake_word()
            else:
                current_status = GetMicrophoneStatus()
                
                if current_status == MIC_ON:
                    main_execution()
                else:
                    ai_status = GetAssistantStatus()
                    if STATUS_AVAILABLE not in ai_status:
                        SetAssistantStatus(STATUS_AVAILABLE)
                    sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            break
        except Exception as e:
            logger.error(f"Error in first_thread: {e}")
            sleep(0.1)

def second_thread():
    """Thread for running the graphical user interface"""
    try:
        logger.info("Starting GUI thread")
        GraphicalUserInterface()
    except Exception as e:
        logger.error(f"Error in GUI thread: {e}")

# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("VOICE ASSISTANT STARTING")
        logger.info(f"User: {Username}, Assistant: {Assistantname}")
        logger.info(f"Language: {InputLanguage}")
        logger.info("=" * 60)
        
        initial_execution()
        
        print("\n" + "=" * 60)
        print("System started in SLEEP MODE")
        print(f"Say '{WAKE_WORD.upper()}' to wake the assistant")
        print("Or click the microphone button in GUI to wake manually")
        print("=" * 60 + "\n")
        
        thread1 = threading.Thread(target=first_thread, daemon=True)
        thread1.start()
        
        second_thread()
    
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        cleanup_subprocesses()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        cleanup_subprocesses()
    finally:
        logger.info("Application shutting down")