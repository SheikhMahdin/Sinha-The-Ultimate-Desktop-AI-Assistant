"""
Advanced Voice Assistant System
================================
Enhanced version with improved architecture, performance, and maintainability.
Maintains backward compatibility with original functionality.
"""

from __future__ import annotations

import os
import sys
import json
import logging
import atexit
import threading
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from time import sleep, time
from asyncio import run
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty

# Third-party imports
import mtranslate as mt
from dotenv import dotenv_values

# Local imports
from Frontend.GUI import (
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

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for terminal output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging() -> logging.Logger:
    """Configure advanced logging with file rotation and colored output"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler without colors
    file_handler = logging.FileHandler(log_dir / "assistant.log", encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class MicrophoneState(Enum):
    """Microphone state enumeration"""
    ON = "True"
    OFF = "False"


class AssistantStatus(Enum):
    """Assistant status enumeration"""
    AVAILABLE = "Available ..."
    LISTENING = "Listening ..."
    THINKING = "Thinking ..."
    SEARCHING = "Searching ..."
    ANSWERING = "Answering ..."
    SLEEPING = "Sleeping ... (Say 'Sinha' to wake)"
    WAKING = "Waking up ..."


class QueryType(Enum):
    """Query classification types"""
    GENERAL = auto()
    REALTIME = auto()
    AUTOMATION = auto()
    IMAGE_GENERATION = auto()
    EXIT = auto()


@dataclass
class Constants:
    """Application constants"""
    WAKE_WORD: str = "sinha"
    SLEEP_COMMAND: str = "sleep"
    
    FUNCTIONS: List[str] = field(default_factory=lambda: [
        "open", "close", "play", "system", "content", 
        "google search", "youtube search"
    ])
    
    IMAGE_KEYWORDS: List[str] = field(default_factory=lambda: [
        "generate", "create image", "draw", "make image", "picture of"
    ])
    
    QUERY_TIMEOUT: float = 5.0
    RESPONSE_DELAY: float = 0.1
    MAX_RETRIES: int = 3

CONST = Constants()

# ============================================================================
# CONFIGURATION MANAGEMENT
# ============================================================================

@dataclass
class AppConfig:
    """Application configuration"""
    username: str
    assistant_name: str
    input_language: str = "en"
    
    @classmethod
    def from_env(cls, env_path: str = ".env") -> AppConfig:
        """Load configuration from environment file"""
        try:
            env_vars = dotenv_values(env_path)
            
            username = env_vars.get("Username")
            assistant_name = env_vars.get("Assistantname")
            input_language = env_vars.get("InputLanguage", "en")
            
            if not username:
                raise ValueError("Username not set in .env file")
            if not assistant_name:
                raise ValueError("Assistantname not set in .env file")
            
            logger.info(f"✓ Config loaded: User={username}, Assistant={assistant_name}, Lang={input_language}")
            return cls(username, assistant_name, input_language)
        
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    @property
    def default_message(self) -> str:
        """Generate default welcome message"""
        return (
            f'{self.username} : Hello {self.assistant_name}, How are you?\n'
            f'{self.assistant_name} : Welcome {self.username}. I am doing well. How may I help you?'
        )


# ============================================================================
# STATE MANAGEMENT
# ============================================================================

class ThreadSafeState:
    """Thread-safe state manager"""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._sleep_state = True
        self._processing = False
        self._subprocesses: List[subprocess.Popen] = []
    
    @contextmanager
    def lock(self):
        """Context manager for state locking"""
        self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()
    
    @property
    def is_sleeping(self) -> bool:
        with self._lock:
            return self._sleep_state
    
    @is_sleeping.setter
    def is_sleeping(self, value: bool):
        with self._lock:
            self._sleep_state = value
            logger.info(f"Sleep state → {value}")
    
    @property
    def is_processing(self) -> bool:
        with self._lock:
            return self._processing
    
    @is_processing.setter
    def is_processing(self, value: bool):
        with self._lock:
            self._processing = value
    
    def add_subprocess(self, proc: subprocess.Popen):
        with self._lock:
            self._subprocesses.append(proc)
    
    def cleanup_subprocesses(self):
        """Clean up all running subprocesses"""
        with self._lock:
            for proc in self._subprocesses:
                try:
                    if proc.poll() is None:
                        logger.info(f"Terminating subprocess PID: {proc.pid}")
                        proc.terminate()
                        proc.wait(timeout=5)
                except Exception as e:
                    logger.error(f"Error cleaning up subprocess: {e}")
                    try:
                        proc.kill()
                    except:
                        pass
            self._subprocesses.clear()

state = ThreadSafeState()

# ============================================================================
# FILE OPERATIONS
# ============================================================================

class FileManager:
    """Advanced file operations manager"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.base_dir = Path.cwd()
        self.data_dir = self.base_dir / "Data"
        self.temp_dir = Path(TempDirectoryPath(''))
        
    def ensure_directory(self, directory: Path) -> bool:
        """Create directory if it doesn't exist"""
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            return False
    
    def read_json(self, filepath: Path, default: Any = None) -> Any:
        """Safely read JSON file with fallback"""
        try:
            self.ensure_directory(filepath.parent)
            
            if not filepath.exists():
                logger.warning(f"{filepath.name} not found, creating empty")
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(default or [], f)
                return default or []
            
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted JSON in {filepath}: {e}")
            return default or []
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
            return default or []
    
    def write_text(self, filepath: Path, content: str) -> bool:
        """Write text to file safely"""
        try:
            self.ensure_directory(filepath.parent)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Error writing to {filepath}: {e}")
            return False
    
    def read_text(self, filepath: Path, default: str = "") -> str:
        """Read text from file with fallback"""
        try:
            if not filepath.exists():
                return default
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
            return default
    
    def get_chatlog_data(self) -> List[Dict[str, str]]:
        """Read chat log JSON"""
        return self.read_json(self.data_dir / 'ChatLog.json', [])
    
    def format_chatlog(self) -> str:
        """Convert JSON chat log to formatted text"""
        json_data = self.get_chatlog_data()
        formatted = []
        
        for entry in json_data:
            role = entry.get("role", "")
            content = entry.get("content", "")
            
            if role == "user":
                formatted.append(f"{self.config.username} : {content}")
            elif role == "assistant":
                formatted.append(f"{self.config.assistant_name} : {content}")
        
        return '\n'.join(formatted)


# ============================================================================
# TRANSLATION SERVICE
# ============================================================================

class TranslationService:
    """Translation service with caching"""
    
    def __init__(self, target_language: str):
        self.target_language = target_language
        self._cache: Dict[str, str] = {}
    
    def translate(self, text: str) -> str:
        """Translate text with caching"""
        if self.target_language == "en" or not text:
            return text
        
        # Check cache
        if text in self._cache:
            return self._cache[text]
        
        try:
            translated = mt.translate(text, self.target_language, "auto")
            result = translated.capitalize()
            self._cache[text] = result
            return result
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text


# ============================================================================
# QUERY PROCESSOR
# ============================================================================

class QueryProcessor:
    """Advanced query processing and classification"""
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def classify_query(self, decision: List[str]) -> Dict[str, Any]:
        """Classify query into structured data"""
        classification = {
            'has_general': False,
            'has_realtime': False,
            'has_automation': False,
            'has_image_gen': False,
            'has_exit': False,
            'merged_query': '',
            'image_query': '',
            'automation_items': []
        }
        
        # Check for different query types
        general_queries = [i for i in decision if i.startswith("general")]
        realtime_queries = [i for i in decision if i.startswith("realtime")]
        
        classification['has_general'] = bool(general_queries)
        classification['has_realtime'] = bool(realtime_queries)
        
        # Merge general and realtime queries
        if general_queries or realtime_queries:
            merged = " and ".join(
                [" ".join(i.split()[1:]) for i in (general_queries + realtime_queries)]
            )
            classification['merged_query'] = merged
        
        # Check for image generation
        for item in decision:
            if any(keyword in item.lower() for keyword in CONST.IMAGE_KEYWORDS):
                classification['has_image_gen'] = True
                classification['image_query'] = item
                break
        
        # Check for automation
        automation_items = [
            item for item in decision 
            if any(item.startswith(func) for func in CONST.FUNCTIONS)
        ]
        if automation_items:
            classification['has_automation'] = True
            classification['automation_items'] = automation_items
        
        # Check for exit
        classification['has_exit'] = any("exit" in item for item in decision)
        
        return classification


# ============================================================================
# ASSISTANT ENGINE
# ============================================================================

class AssistantEngine:
    """Main assistant processing engine"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.file_manager = FileManager(config)
        self.translator = TranslationService(config.input_language)
        self.query_processor = QueryProcessor(config)
        self.response_queue = Queue()
    
    def initialize(self):
        """Initialize the assistant"""
        logger.info("Initializing assistant...")
        
        SetMicrophoneStatus(MicrophoneState.OFF.value)
        ShowTextToScreen("")
        
        # Setup default chat if needed
        database_path = Path(TempDirectoryPath('Database.data'))
        responses_path = Path(TempDirectoryPath('Responses.data'))
        
        if not database_path.exists() or database_path.stat().st_size == 0:
            self.file_manager.write_text(database_path, "")
            self.file_manager.write_text(responses_path, self.config.default_message)
            logger.info("No chat history - displaying default message")
        else:
            # Load existing chat log
            formatted_log = self.file_manager.format_chatlog()
            if formatted_log:
                self.file_manager.write_text(database_path, AnswerModifier(formatted_log))
                self.display_chat_history()
        
        SetAssistantStatus(AssistantStatus.SLEEPING.value)
        logger.info("✓ Initialization complete - System in sleep mode")
    
    def display_chat_history(self):
        """Display chat history on GUI"""
        try:
            database_path = Path(TempDirectoryPath('Database.data'))
            data = self.file_manager.read_text(database_path)
            
            if data:
                self.file_manager.write_text(
                    Path(TempDirectoryPath('Responses.data')), 
                    data
                )
                logger.debug("Chat history displayed")
        except Exception as e:
            logger.error(f"Error displaying chat history: {e}")
    
    def display_answer(self, answer: str) -> bool:
        """Display and speak answer with translation"""
        try:
            # Translate if needed
            if self.config.input_language != "en":
                answer = self.translator.translate(answer)
            
            # Display on screen
            ShowTextToScreen(f" {self.config.assistant_name} : {answer}")
            SetAssistantStatus(AssistantStatus.ANSWERING.value)
            
            # Speak
            TextToSpeech(answer)
            
            return True
        
        except Exception as e:
            logger.error(f"Error in display_answer: {e}")
            return False
    
    def start_image_generation(self, query: str) -> bool:
        """Start image generation subprocess"""
        try:
            image_data_path = Path('Frontend') / 'Files' / 'ImageGeneration.data'
            self.file_manager.ensure_directory(image_data_path.parent)
            
            with open(image_data_path, "w", encoding='utf-8') as f:
                f.write(f"{query},True")
            
            logger.info(f"Image generation initiated: {query}")
            
            image_script = Path('Backend') / 'ImageGeneration.py'
            
            if not image_script.exists():
                logger.error(f"ImageGeneration.py not found")
                return False
            
            proc = subprocess.Popen(
                [sys.executable, str(image_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            
            state.add_subprocess(proc)
            logger.info(f"✓ Image generation started (PID: {proc.pid})")
            return True
        
        except Exception as e:
            logger.error(f"Error starting image generation: {e}")
            return False
    
    def listen_for_wake_word(self) -> bool:
        """Listen for wake word in sleep mode"""
        try:
            SetAssistantStatus(AssistantStatus.SLEEPING.value)
            query = SpeechRecognition()
            
            if not query:
                return False
            
            query_lower = query.strip().lower()
            logger.debug(f"Wake listener heard: '{query}'")
            
            if CONST.WAKE_WORD in query_lower:
                state.is_sleeping = False
                SetMicrophoneStatus(MicrophoneState.ON.value)
                SetAssistantStatus(AssistantStatus.WAKING.value)
                
                self.display_answer("Yes, I'm awake now!")
                logger.info("✓ Wake word detected - Assistant activated")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error in wake word detection: {e}")
            return False
    
    def process_query(self) -> bool:
        """Main query processing logic"""
        try:
            # Listen for query
            SetAssistantStatus(AssistantStatus.LISTENING.value)
            query = SpeechRecognition()
            
            if GetMicrophoneStatus() != MicrophoneState.ON.value:
                return False
            
            if not query:
                return False
            
            # Check for sleep command
            if CONST.SLEEP_COMMAND in query.lower():
                state.is_sleeping = True
                SetMicrophoneStatus(MicrophoneState.OFF.value)
                
                self.display_answer("Going to sleep. Say 'Sinha' to wake me up.")
                logger.info("Sleep command - Entering sleep mode")
                return True
            
            # Display user query
            ShowTextToScreen(f" {self.config.username} : {query}")
            SetAssistantStatus(AssistantStatus.THINKING.value)
            
            # Get decision from DMM
            decision = FirstLayerDMM(query)
            logger.info(f"DMM Decision: {decision}")
            
            # Classify the query
            classification = self.query_processor.classify_query(decision)
            
            # Handle image generation
            if classification['has_image_gen']:
                self.start_image_generation(classification['image_query'])
            
            # Handle automation
            if classification['has_automation']:
                run(Automation(list(decision)))
            
            # Handle realtime search
            if classification['has_realtime'] or (
                classification['has_general'] and classification['has_realtime']
            ):
                SetAssistantStatus(AssistantStatus.SEARCHING.value)
                answer = RealtimeSearchEngine(classification['merged_query'])
                self.display_answer(answer)
                return True
            
            # Handle general queries
            if classification['has_general']:
                SetAssistantStatus(AssistantStatus.THINKING.value)
                query_final = classification['merged_query']
                logger.info(f"Processing general query: {query_final}")
                
                answer = ChatBot(query_final)
                self.display_answer(answer)
                return True
            
            # Handle exit
            if classification['has_exit']:
                self.display_answer("Okay, Bye!")
                logger.info("Exit command received")
                state.cleanup_subprocesses()
                os._exit(0)
            
            return False
        
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return False


# ============================================================================
# THREADING MANAGER
# ============================================================================

class ThreadManager:
    """Manage assistant threads with executor"""
    
    def __init__(self, engine: AssistantEngine):
        self.engine = engine
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="Assistant")
        self.running = True
    
    def voice_processing_loop(self):
        """Main voice processing thread"""
        logger.info("Voice processing thread started")
        
        while self.running:
            try:
                if state.is_sleeping:
                    # Check for manual wake-up via GUI
                    if GetMicrophoneStatus() == MicrophoneState.ON.value:
                        state.is_sleeping = False
                        SetAssistantStatus(AssistantStatus.WAKING.value)
                        self.engine.display_answer("Yes, I'm awake now!")
                        logger.info("Manual wake-up via GUI")
                    else:
                        self.engine.listen_for_wake_word()
                else:
                    # Process queries when awake
                    if GetMicrophoneStatus() == MicrophoneState.ON.value:
                        self.engine.process_query()
                    else:
                        # Set to available if not already
                        current_status = GetAssistantStatus()
                        if AssistantStatus.AVAILABLE.value not in current_status:
                            SetAssistantStatus(AssistantStatus.AVAILABLE.value)
                        sleep(CONST.RESPONSE_DELAY)
            
            except KeyboardInterrupt:
                logger.info("Voice thread interrupted")
                break
            except Exception as e:
                logger.error(f"Error in voice processing: {e}")
                sleep(CONST.RESPONSE_DELAY)
    
    def gui_loop(self):
        """GUI thread"""
        try:
            logger.info("Starting GUI thread")
            GraphicalUserInterface()
        except Exception as e:
            logger.error(f"Error in GUI thread: {e}")
    
    def start(self):
        """Start all threads"""
        # Start voice processing in executor
        voice_future = self.executor.submit(self.voice_processing_loop)
        
        # Run GUI in main thread (required for tkinter)
        self.gui_loop()
        
        # Cleanup
        self.running = False
        self.executor.shutdown(wait=True)
    
    def shutdown(self):
        """Shutdown all threads"""
        self.running = False
        self.executor.shutdown(wait=False)


# ============================================================================
# APPLICATION
# ============================================================================

class VoiceAssistantApp:
    """Main application class"""
    
    def __init__(self):
        self.config = AppConfig.from_env()
        self.engine = AssistantEngine(self.config)
        self.thread_manager = ThreadManager(self.engine)
        
        # Register cleanup
        atexit.register(self.cleanup)
    
    def cleanup(self):
        """Cleanup resources on exit"""
        logger.info("Cleaning up resources...")
        state.cleanup_subprocesses()
        self.thread_manager.shutdown()
    
    def run(self):
        """Run the application"""
        try:
            self._print_banner()
            
            # Initialize
            self.engine.initialize()
            
            # Print startup info
            print("\n" + "=" * 60)
            print("System started in SLEEP MODE")
            print(f"Say '{CONST.WAKE_WORD.upper()}' to wake the assistant")
            print("Or click the microphone button in GUI to wake manually")
            print("=" * 60 + "\n")
            
            # Start threads
            self.thread_manager.start()
        
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            self.cleanup()
    
    def _print_banner(self):
        """Print startup banner"""
        banner = f"""
{'=' * 60}
🎙️  ADVANCED VOICE ASSISTANT v2.0
{'=' * 60}
User: {self.config.username}
Assistant: {self.config.assistant_name}
Language: {self.config.input_language}
{'=' * 60}
        """
        print(banner)
        logger.info("Application starting...")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Application entry point"""
    app = VoiceAssistantApp()
    app.run()


if __name__ == "__main__":
    main()
