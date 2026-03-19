"""
Ultra-Fast Automation - YOUR CHROME PROFILE Edition
====================================================
Uses YOUR existing Chrome browser with all your logins and sessions!
"""

import os
import sys
import time
import asyncio
import logging
import platform
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

from groq import Groq
from dotenv import dotenv_values

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TaskResult:
    status: TaskStatus
    message: str
    error: Optional[str] = None


def get_chrome_profile_path():
    """
    Automatically detect Chrome user data directory for your OS.
    """
    system = platform.system()
    
    if system == "Windows":
        # Windows paths
        paths = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data'),
            os.path.join(os.environ.get('APPDATA', ''), 'Google', 'Chrome', 'User Data'),
        ]
    elif system == "Darwin":  # macOS
        paths = [
            os.path.expanduser('~/Library/Application Support/Google/Chrome'),
        ]
    else:  # Linux
        paths = [
            os.path.expanduser('~/.config/google-chrome'),
            os.path.expanduser('~/.config/chromium'),
        ]
    
    # Find first existing path
    for path in paths:
        if os.path.exists(path):
            logger.info(f"Found Chrome profile at: {path}")
            return path
    
    logger.warning("Chrome profile path not found - using default")
    return None


class FastCommandParser:
    """Lightning-fast regex command parser."""
    
    def __init__(self):
        self.patterns = {
            'open_youtube': re.compile(r'\bopen\s+youtube\b', re.I),
            'search_youtube': re.compile(r'\bsearch\s+(?:youtube\s+)?for\s+["\']?(.+?)["\']?(?:\s+(?:and|,)|$)', re.I),
            'play_video': re.compile(r'\bplay\s+(?:the\s+)?(?:first\s+)?video\b', re.I),
            'like_video': re.compile(r'\blike\s+(?:the\s+)?(?:it|video)\b', re.I),
            'comment': re.compile(r'\bcomment\s+["\'](.+?)["\']', re.I),
            'open_site': re.compile(r'\b(?:open|go\s+to)\s+([a-zA-Z0-9.-]+\.com)\b', re.I),
            'google_search': re.compile(r'\b(?:google\s+)?search\s+(?:for\s+)?["\']?(.+?)["\']?(?:\s+(?:and|,)|$)', re.I),
        }
    
    def parse(self, command: str) -> List[Dict[str, Any]]:
        """Parse command using regex - INSTANT!"""
        actions = []
        
        if self.patterns['open_youtube'].search(command):
            actions.append({'action': 'open_youtube'})
        
        search_match = self.patterns['search_youtube'].search(command)
        if search_match:
            query = search_match.group(1).strip(' ,')
            actions.append({'action': 'search_youtube', 'query': query})
        
        if self.patterns['play_video'].search(command):
            actions.append({'action': 'play_first_video'})
        
        if self.patterns['like_video'].search(command):
            actions.append({'action': 'like_video'})
        
        comment_match = self.patterns['comment'].search(command)
        if comment_match:
            text = comment_match.group(1)
            actions.append({'action': 'post_comment', 'text': text})
        
        site_match = self.patterns['open_site'].search(command)
        if site_match and not actions:
            url = site_match.group(1)
            actions.append({'action': 'open_website', 'url': url})
        
        google_match = self.patterns['google_search'].search(command)
        if google_match and 'search_youtube' not in [a['action'] for a in actions]:
            query = google_match.group(1).strip(' ,')
            actions.append({'action': 'google_search', 'query': query})
        
        return actions


class YourChromeEngine:
    """
    Uses YOUR existing Chrome browser with YOUR profile!
    - Already logged into YouTube ✓
    - Your bookmarks ✓
    - Your history ✓
    - Your extensions ✓
    """
    
    def __init__(self, profile_name: str = "Default", user_data_dir: str = None):
        """
        Initialize with YOUR Chrome profile.
        
        Args:
            profile_name: Chrome profile name (Default, Profile 1, Profile 2, etc.)
            user_data_dir: Optional custom Chrome user data directory
        """
        self.driver = None
        self.profile_name = profile_name
        self.user_data_dir = user_data_dir or get_chrome_profile_path()
        self._setup_driver()
    
    def _setup_driver(self):
        """Setup Chrome using YOUR profile."""
        chrome_options = Options()
        
        # USE YOUR CHROME PROFILE!
        if self.user_data_dir:
            chrome_options.add_argument(f"user-data-dir={self.user_data_dir}")
            chrome_options.add_argument(f"profile-directory={self.profile_name}")
            print(f"✓ Using your Chrome profile: {self.profile_name}")
            print(f"✓ Location: {self.user_data_dir}")
        
        # Performance optimizations (but keep your extensions!)
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Don't load images for speed (optional - comment out if you want images)
        # chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        
        # Disable automation flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✓ Browser opened with YOUR profile!")
        except Exception as e:
            print(f"✗ Error: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure Chrome is NOT already running")
            print("2. Close all Chrome windows and try again")
            print("3. Or use a different profile name")
            raise
    
    def fast_wait(self, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 5) -> Any:
        """Fast wait for element."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
        except TimeoutException:
            return None
    
    def instant_click(self, element) -> bool:
        """Instant click."""
        try:
            element.click()
            return True
        except:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                return False
    
    def fast_type(self, element, text: str) -> bool:
        """Fast typing."""
        try:
            element.clear()
            element.send_keys(text)
            return True
        except:
            return False
    
    def close(self):
        """Close browser."""
        if self.driver:
            self.driver.quit()


class TurboYouTube:
    """Ultra-fast YouTube automation."""
    
    def __init__(self, engine: YourChromeEngine):
        self.engine = engine
        self.driver = engine.driver
    
    def open(self) -> TaskResult:
        """Open YouTube."""
        try:
            self.driver.get("https://www.youtube.com")
            time.sleep(0.5)
            return TaskResult(TaskStatus.SUCCESS, "YouTube opened")
        except Exception as e:
            return TaskResult(TaskStatus.FAILED, "Failed", str(e))
    
    def search(self, query: str) -> TaskResult:
        """Search YouTube."""
        try:
            search_box = (
                self.engine.fast_wait("input#search", timeout=3) or
                self.engine.fast_wait("input[name='search_query']", timeout=2)
            )
            
            if not search_box:
                return TaskResult(TaskStatus.FAILED, "Search box not found")
            
            self.engine.fast_type(search_box, query)
            search_box.send_keys(Keys.RETURN)
            time.sleep(1)
            
            return TaskResult(TaskStatus.SUCCESS, f"Searched: {query}")
        except Exception as e:
            return TaskResult(TaskStatus.FAILED, "Search failed", str(e))
    
    def play_first(self) -> TaskResult:
        """Play first video."""
        try:
            time.sleep(1)
            videos = self.driver.find_elements(By.CSS_SELECTOR, "a#video-title")
            
            if not videos:
                return TaskResult(TaskStatus.FAILED, "No videos found")
            
            self.engine.instant_click(videos[0])
            time.sleep(1)
            
            return TaskResult(TaskStatus.SUCCESS, "Video playing")
        except Exception as e:
            return TaskResult(TaskStatus.FAILED, "Play failed", str(e))
    
    def like(self) -> TaskResult:
        """Like video."""
        try:
            time.sleep(1)
            
            like_btn = (
                self.engine.fast_wait("like-button-view-model button", timeout=3) or
                self.engine.fast_wait("ytd-toggle-button-renderer button", timeout=2)
            )
            
            if like_btn:
                self.engine.instant_click(like_btn)
                return TaskResult(TaskStatus.SUCCESS, "Video liked")
            else:
                return TaskResult(TaskStatus.FAILED, "Like button not found")
        except Exception as e:
            return TaskResult(TaskStatus.FAILED, "Like failed", str(e))
    
    def comment(self, text: str) -> TaskResult:
        """Post comment - NOW WORKS because you're logged in!"""
        try:
            # Scroll to comments
            self.driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)
            
            # Click comment box
            comment_box = self.engine.fast_wait("div#placeholder-area", timeout=3)
            if not comment_box:
                return TaskResult(TaskStatus.FAILED, "Comment box not found")
            
            self.engine.instant_click(comment_box)
            time.sleep(0.5)
            
            # Type comment
            input_field = self.engine.fast_wait("div#contenteditable-root", timeout=2)
            if input_field:
                input_field.send_keys(text)
                time.sleep(0.5)
                
                # Post button
                post_btn = self.engine.fast_wait("ytd-button-renderer#submit-button button", timeout=2)
                if post_btn:
                    self.engine.instant_click(post_btn)
                    return TaskResult(TaskStatus.SUCCESS, "Comment posted!")
            
            return TaskResult(TaskStatus.FAILED, "Comment field not found")
        except Exception as e:
            return TaskResult(TaskStatus.FAILED, "Comment failed", str(e))


class YourBrowserAutomation:
    """
    FAST automation using YOUR browser profile!
    """
    
    def __init__(self, profile_name: str = "Default", user_data_dir: str = None):
        """
        Initialize with YOUR Chrome profile.
        
        Args:
            profile_name: Your Chrome profile (Default, Profile 1, Profile 2, etc.)
            user_data_dir: Optional custom Chrome directory
        """
        self.engine = YourChromeEngine(profile_name, user_data_dir)
        self.youtube = TurboYouTube(self.engine)
        self.parser = FastCommandParser()
    
    async def execute(self, command: str) -> List[TaskResult]:
        """Execute command FAST using YOUR browser!"""
        results = []
        
        # Instant regex parsing
        actions = self.parser.parse(command)
        
        if not actions:
            results.append(TaskResult(TaskStatus.FAILED, "Could not parse command"))
            return results
        
        # Execute actions
        for action_data in actions:
            action = action_data.get('action')
            
            try:
                if action == 'open_youtube':
                    result = self.youtube.open()
                    
                elif action == 'search_youtube':
                    result = self.youtube.search(action_data['query'])
                    
                elif action == 'play_first_video':
                    result = self.youtube.play_first()
                    
                elif action == 'like_video':
                    result = self.youtube.like()
                    
                elif action == 'post_comment':
                    result = self.youtube.comment(action_data['text'])
                    
                elif action == 'open_website':
                    url = action_data['url']
                    if not url.startswith('http'):
                        url = 'https://' + url
                    self.engine.driver.get(url)
                    result = TaskResult(TaskStatus.SUCCESS, f"Opened {url}")
                    
                elif action == 'google_search':
                    query = action_data['query']
                    url = f"https://www.google.com/search?q={query}"
                    self.engine.driver.get(url)
                    result = TaskResult(TaskStatus.SUCCESS, f"Searched: {query}")
                    
                else:
                    result = TaskResult(TaskStatus.FAILED, f"Unknown: {action}")
                
                results.append(result)
                
            except Exception as e:
                results.append(TaskResult(TaskStatus.FAILED, f"Failed: {action}", str(e)))
        
        return results
    
    def cleanup(self):
        """Close browser."""
        self.engine.close()


# ============================================================================
# SIMPLE USAGE - YOUR BROWSER!
# ============================================================================

async def main():
    """Demo using YOUR Chrome profile."""
    
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║         Ultra-Fast Automation - YOUR BROWSER              ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    
    This will use YOUR Chrome profile with:
    ✓ Your YouTube login
    ✓ Your bookmarks
    ✓ Your history
    ✓ Your extensions
    
    NOTE: Close ALL Chrome windows before running!
    """)
    
    input("Press Enter to start...")
    
    # Initialize with YOUR profile
    # Common profile names: "Default", "Profile 1", "Profile 2", etc.
    system = YourBrowserAutomation(profile_name="Default")
    
    try:
        # Example command
        command = "open youtube, search for python programming, play first video, like it"
        
        print(f"\n🚀 Executing: {command}\n")
        
        start_time = time.time()
        results = await system.execute(command)
        elapsed = time.time() - start_time
        
        # Print results
        for i, result in enumerate(results, 1):
            status_emoji = "✓" if result.status == TaskStatus.SUCCESS else "✗"
            print(f"{status_emoji} {i}. {result.message}")
        
        print(f"\n⚡ Completed in {elapsed:.2f} seconds!")
        print("\n💡 Notice: You're already logged into YouTube!")
        print("   Try commenting - it will work!")
        
        input("\nPress Enter to close...")
        
    finally:
        system.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
