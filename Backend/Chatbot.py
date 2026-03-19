"""
Robust Chatbot Module - Fixed All Issues
=========================================
✓ Handles Unicode encoding errors (UTF-8)
✓ Handles corrupted JSON files
✓ Handles missing files
✓ Automatic file repair
✓ Better error messages
"""

from groq import Groq
from json import load, dump, JSONDecodeError
import datetime
from dotenv import dotenv_values
import os
import logging
from pathlib import Path

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================
try:
    env_vars = dotenv_values(".env")
    Username = env_vars.get("Username", "User")
    Assistantname = env_vars.get("Assistantname", "Assistant")
    GroqAPIKey = env_vars.get("GroqAPIKey")

    if not GroqAPIKey:
        raise ValueError("GroqAPIKey not set in .env file")
    
    logger.info(f"✓ Config loaded: User={Username}, Assistant={Assistantname}")
    
except Exception as e:
    logger.error(f"❌ Configuration error: {e}")
    raise

# ============================================================================
# GROQ CLIENT
# ============================================================================
client = Groq(api_key=GroqAPIKey)

# ============================================================================
# CONSTANTS
# ============================================================================
CHATLOG_PATH = Path("Data") / "ChatLog.json"
MAX_HISTORY_MESSAGES = 20  # Keep only last 20 messages to save memory

# ============================================================================
# SYSTEM PROMPT
# ============================================================================
'''System_old = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {Assistantname} which also has real-time up-to-date information from the internet.
***you have a json file where you save memory***
*** Do not provide notes in the output, just answer the question and never mention your training data.***
*** Do not tell time until I ask, do not talk too much, just answer the question.***"""'''


System = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {Assistantname}...
*** Provide detailed, comprehensive answers when asked for explanations, tutorials, or detailed information.
*** Give brief answers only for simple yes/no questions or quick facts.
*** Match your response length to the complexity and detail requested in the question.***
"""
SystemChatBot = [
    {"role": "system", "content": System}
]

# ============================================================================
# SAFE FILE OPERATIONS WITH ENCODING
# ============================================================================

def ensure_data_directory():
    """Ensure Data directory exists"""
    try:
        CHATLOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Data directory verified")
    except Exception as e:
        logger.error(f"Failed to create Data directory: {e}")
        raise

def load_chatlog_safe():
    """
    Safely load chat log with comprehensive error handling
    Handles: Unicode errors, JSON errors, missing files, corrupted files
    """
    ensure_data_directory()
    
    # If file doesn't exist, create it
    if not CHATLOG_PATH.exists():
        logger.info("ChatLog.json not found, creating new file")
        save_chatlog_safe([])
        return []
    
    # Try to read with UTF-8 encoding (fixes Unicode errors)
    try:
        with open(CHATLOG_PATH, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
            # Check if file is empty
            if not content:
                logger.warning("ChatLog.json is empty, initializing")
                save_chatlog_safe([])
                return []
            
            # Try to parse JSON
            try:
                messages = load(open(CHATLOG_PATH, 'r', encoding='utf-8'))
                
                # Validate it's a list
                if not isinstance(messages, list):
                    logger.warning("ChatLog.json contains invalid data (not a list), resetting")
                    save_chatlog_safe([])
                    return []
                
                logger.info(f"✓ Loaded {len(messages)} messages from ChatLog.json")
                return messages
                
            except JSONDecodeError as e:
                logger.error(f"❌ ChatLog.json is corrupted (JSON error): {e}")
                logger.info("Creating backup and resetting chat log")
                
                # Backup corrupted file
                backup_path = CHATLOG_PATH.parent / "ChatLog_corrupted_backup.json"
                try:
                    CHATLOG_PATH.rename(backup_path)
                    logger.info(f"Corrupted file backed up to: {backup_path}")
                except:
                    pass
                
                # Create fresh file
                save_chatlog_safe([])
                return []
    
    except UnicodeDecodeError as e:
        logger.error(f"❌ ChatLog.json has encoding error: {e}")
        logger.info("Attempting to read with different encodings...")
        
        # Try different encodings
        for encoding in ['utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                logger.info(f"Trying encoding: {encoding}")
                with open(CHATLOG_PATH, 'r', encoding=encoding) as f:
                    messages = load(f)
                    
                    if isinstance(messages, list):
                        logger.info(f"✓ Successfully read with {encoding} encoding")
                        # Re-save with UTF-8
                        save_chatlog_safe(messages)
                        return messages
            except:
                continue
        
        # If all encodings fail, backup and reset
        logger.error("All encoding attempts failed, resetting file")
        backup_path = CHATLOG_PATH.parent / "ChatLog_encoding_error_backup.txt"
        try:
            with open(CHATLOG_PATH, 'rb') as src:
                with open(backup_path, 'wb') as dst:
                    dst.write(src.read())
            logger.info(f"Backed up corrupted file to: {backup_path}")
        except:
            pass
        
        save_chatlog_safe([])
        return []
    
    except Exception as e:
        logger.error(f"❌ Unexpected error loading ChatLog.json: {e}")
        save_chatlog_safe([])
        return []

def save_chatlog_safe(messages):
    """
    Safely save chat log with UTF-8 encoding
    """
    try:
        ensure_data_directory()
        
        # Limit message history to save memory
        if len(messages) > MAX_HISTORY_MESSAGES:
            messages = messages[-MAX_HISTORY_MESSAGES:]
            logger.info(f"Trimmed chat history to last {MAX_HISTORY_MESSAGES} messages")
        
        # Write with UTF-8 encoding and proper formatting
        with open(CHATLOG_PATH, 'w', encoding='utf-8') as f:
            dump(messages, f, indent=4, ensure_ascii=False)
        
        logger.debug(f"✓ Saved {len(messages)} messages to ChatLog.json")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving ChatLog.json: {e}")
        return False

# ============================================================================
# REALTIME INFORMATION
# ============================================================================

def RealtimeInformation():
    """Get real-time date and time information"""
    try:
        current_date_time = datetime.datetime.now()
        
        data = (
            f"Please use this real-time information if needed:\n"
            f"Day: {current_date_time.strftime('%A')}\n"
            f"Date: {current_date_time.strftime('%d')}\n"
            f"Month: {current_date_time.strftime('%B')}\n"
            f"Year: {current_date_time.strftime('%Y')}\n"
            f"Time: {current_date_time.strftime('%H')} hours : "
            f"{current_date_time.strftime('%M')} minutes : "
            f"{current_date_time.strftime('%S')} seconds.\n"
        )
        return data
    except Exception as e:
        logger.error(f"Error getting realtime info: {e}")
        return ""

# ============================================================================
# ANSWER FORMATTING
# ============================================================================

def AnswerModifier(Answer):
    """Clean up and format the chatbot's response"""
    try:
        # Remove empty lines
        lines = Answer.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        modified_answer = '\n'.join(non_empty_lines)
        
        # Remove any unwanted tokens
        modified_answer = modified_answer.replace("</s>", "").strip()
        
        return modified_answer
    except Exception as e:
        logger.error(f"Error modifying answer: {e}")
        return Answer

# ============================================================================
# MAIN CHATBOT FUNCTION
# ============================================================================

def ChatBot(Query):
    """
    Main chatbot function with robust error handling
    
    Args:
        Query (str): User's question/query
        
    Returns:
        str: AI's response
    """
    try:
        logger.info(f"Processing query: {Query[:50]}...")
        
        # Load chat history safely
        messages = load_chatlog_safe()
        
        # Add user query
        messages.append({"role": "user", "content": Query})
        
        # Prepare system messages
        system_messages = SystemChatBot + [
            {"role": "system", "content": RealtimeInformation()}
        ]
        
        # Call Groq API
        logger.info("Calling Groq API...")
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=system_messages + messages,
            max_tokens=2048,
            temperature=0.7,
            top_p=1,
            stream=True,
            stop=None
        )
        
        # Collect streamed response
        Answer = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                Answer += chunk.choices[0].delta.content
        
        # Clean up answer
        Answer = AnswerModifier(Answer)
        
        # Add assistant response to messages
        messages.append({"role": "assistant", "content": Answer})
        
        # Save updated chat log
        save_chatlog_safe(messages)
        
        logger.info("✓ Response generated successfully")
        return Answer
    
    except Exception as e:
        logger.error(f"❌ Error in ChatBot: {e}", exc_info=True)
        
        # Try to recover by resetting chat log
        logger.info("Attempting to recover by resetting chat log...")
        try:
            save_chatlog_safe([])
            
            # Retry once with fresh log
            logger.info("Retrying query with fresh chat log...")
            messages = [{"role": "user", "content": Query}]
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=SystemChatBot + [{"role": "system", "content": RealtimeInformation()}] + messages,
                max_tokens=1024,
                temperature=0.7,
                top_p=1,
                stream=True,
                stop=None
            )
            
            Answer = ""
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    Answer += chunk.choices[0].delta.content
            
            Answer = AnswerModifier(Answer)
            
            # Save this successful interaction
            messages.append({"role": "assistant", "content": Answer})
            save_chatlog_safe(messages)
            
            return Answer
            
        except Exception as retry_error:
            logger.error(f"❌ Recovery failed: {retry_error}")
            return f"I apologize, but I encountered an error: {str(e)[:100]}"

# ============================================================================
# INITIALIZATION
# ============================================================================

# Initialize chat log on module import
try:
    messages = load_chatlog_safe()
    logger.info(f"✓ Chatbot module initialized with {len(messages)} messages")
except Exception as e:
    logger.error(f"❌ Error during initialization: {e}")
    messages = []

# ============================================================================
# MAIN (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 CHATBOT - Interactive Mode")
    print("="*60)
    print("Type 'exit', 'quit', or 'q' to exit")
    print("="*60 + "\n")
    
    while True:
        try:
            user_input = input("💬 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            response = ChatBot(user_input)
            print(f"\n🤖 {Assistantname}: {response}\n")
            print("-" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            print(f"\n❌ Error: {e}\n")
