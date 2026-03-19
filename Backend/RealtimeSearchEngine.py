"""
Advanced Realtime Search Engine - Improved Version
===================================================
✓ Multiple IP location APIs with fallbacks
✓ Multiple weather APIs with fallbacks  
✓ Robust error handling and caching
✓ Better search result parsing
✓ Parallel data gathering for speed
"""

from groq import Groq
from json import load, dump
import datetime
from dotenv import dotenv_values
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import logging
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass
from time import time

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================
env_vars = dotenv_values(".env")
Username = env_vars.get("Username", "User")
Assistantname = env_vars.get("Assistantname", "Assistant")
GroqAPIKey = env_vars.get("GroqAPIKey")

if not GroqAPIKey:
    raise ValueError("GroqAPIKey not set in .env file")

# ============================================================================
# CONSTANTS
# ============================================================================
CHATLOG_PATH = os.path.join(os.getcwd(), "Data", "ChatLog.json")
REQUEST_TIMEOUT = 8
MAX_RETRIES = 2
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Cache expiry times (seconds)
LOCATION_CACHE_EXPIRY = 3600  # 1 hour
WEATHER_CACHE_EXPIRY = 1800   # 30 minutes

# ============================================================================
# GROQ CLIENT
# ============================================================================
client = Groq(api_key=GroqAPIKey)

# ============================================================================
# SYSTEM PROMPT
# ============================================================================
System = f"""You are {Assistantname}, AI assistant for {Username}. Use the search results and real-time data provided to give accurate, current information. Answer directly and professionally."""

# ============================================================================
# DATA CLASSES
# ============================================================================
@dataclass
class LocationData:
    """Location information"""
    city: str
    region: str
    country: str
    country_code: str
    latitude: float
    longitude: float
    ip_address: str
    timezone: str
    
    def __str__(self):
        return f"{self.city}, {self.region}, {self.country}"

@dataclass
class WeatherData:
    """Weather information"""
    temperature_c: float
    temperature_f: float
    condition: str
    humidity: Optional[int] = None
    wind_speed: Optional[float] = None
    feels_like_c: Optional[float] = None
    
    def __str__(self):
        temp_str = f"{self.temperature_c}°C ({self.temperature_f}°F)"
        if self.condition:
            temp_str += f" - {self.condition}"
        return temp_str

# ============================================================================
# CHAT LOG MANAGEMENT
# ============================================================================
def load_chatlog(max_messages: int = 5) -> List[Dict]:
    """Load recent chat history"""
    try:
        os.makedirs(os.path.dirname(CHATLOG_PATH), exist_ok=True)
        if os.path.exists(CHATLOG_PATH):
            with open(CHATLOG_PATH, "r", encoding='utf-8') as f:
                msgs = load(f)
                if isinstance(msgs, list):
                    return msgs[-max_messages:] if len(msgs) > max_messages else msgs
    except Exception as e:
        logger.error(f"Error loading chatlog: {e}")
    return []

def save_chatlog(messages: List[Dict], max_keep: int = 20):
    """Save chat history"""
    try:
        os.makedirs(os.path.dirname(CHATLOG_PATH), exist_ok=True)
        # Keep only recent messages
        messages_to_save = messages[-max_keep:] if len(messages) > max_keep else messages
        with open(CHATLOG_PATH, "w", encoding='utf-8') as f:
            dump(messages_to_save, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving chatlog: {e}")

# ============================================================================
# ADVANCED LOCATION DETECTION (MULTIPLE APIS)
# ============================================================================

class LocationDetector:
    """Detect user location using multiple IP geolocation APIs"""
    
    def __init__(self):
        self.cache: Optional[Dict] = None
        self.cache_time: Optional[float] = None
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self.cache is None or self.cache_time is None:
            return False
        return (time() - self.cache_time) < LOCATION_CACHE_EXPIRY
    
    def _try_ipapi(self) -> Optional[LocationData]:
        """Try ip-api.com (free, no key needed)"""
        try:
            logger.info("🌍 Trying ip-api.com...")
            response = requests.get(
                "http://ip-api.com/json/",
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': USER_AGENT}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    location = LocationData(
                        city=data.get('city', 'Unknown'),
                        region=data.get('regionName', 'Unknown'),
                        country=data.get('country', 'Unknown'),
                        country_code=data.get('countryCode', 'XX'),
                        latitude=data.get('lat', 0.0),
                        longitude=data.get('lon', 0.0),
                        ip_address=data.get('query', 'Unknown'),
                        timezone=data.get('timezone', 'UTC')
                    )
                    logger.info(f"✓ ip-api.com: {location}")
                    return location
        except Exception as e:
            logger.warning(f"ip-api.com failed: {e}")
        return None
    
    def _try_ipinfo(self) -> Optional[LocationData]:
        """Try ipinfo.io (free tier)"""
        try:
            logger.info("🌍 Trying ipinfo.io...")
            response = requests.get(
                "https://ipinfo.io/json",
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': USER_AGENT}
            )
            
            if response.status_code == 200:
                data = response.json()
                loc = data.get('loc', '0,0').split(',')
                
                location = LocationData(
                    city=data.get('city', 'Unknown'),
                    region=data.get('region', 'Unknown'),
                    country=data.get('country', 'Unknown'),
                    country_code=data.get('country', 'XX'),
                    latitude=float(loc[0]) if len(loc) > 0 else 0.0,
                    longitude=float(loc[1]) if len(loc) > 1 else 0.0,
                    ip_address=data.get('ip', 'Unknown'),
                    timezone=data.get('timezone', 'UTC')
                )
                logger.info(f"✓ ipinfo.io: {location}")
                return location
        except Exception as e:
            logger.warning(f"ipinfo.io failed: {e}")
        return None
    
    def _try_ipwhois(self) -> Optional[LocationData]:
        """Try ipwhois.app (free, no key)"""
        try:
            logger.info("🌍 Trying ipwhois.app...")
            response = requests.get(
                "http://ipwho.is/",
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': USER_AGENT}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success', False):
                    location = LocationData(
                        city=data.get('city', 'Unknown'),
                        region=data.get('region', 'Unknown'),
                        country=data.get('country', 'Unknown'),
                        country_code=data.get('country_code', 'XX'),
                        latitude=data.get('latitude', 0.0),
                        longitude=data.get('longitude', 0.0),
                        ip_address=data.get('ip', 'Unknown'),
                        timezone=data.get('timezone', {}).get('id', 'UTC')
                    )
                    logger.info(f"✓ ipwhois.app: {location}")
                    return location
        except Exception as e:
            logger.warning(f"ipwhois.app failed: {e}")
        return None
    
    def _try_freegeoip(self) -> Optional[LocationData]:
        """Try freegeoip.app"""
        try:
            logger.info("🌍 Trying freegeoip.app...")
            response = requests.get(
                "https://freegeoip.app/json/",
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': USER_AGENT}
            )
            
            if response.status_code == 200:
                data = response.json()
                location = LocationData(
                    city=data.get('city', 'Unknown'),
                    region=data.get('region_name', 'Unknown'),
                    country=data.get('country_name', 'Unknown'),
                    country_code=data.get('country_code', 'XX'),
                    latitude=data.get('latitude', 0.0),
                    longitude=data.get('longitude', 0.0),
                    ip_address=data.get('ip', 'Unknown'),
                    timezone=data.get('time_zone', 'UTC')
                )
                logger.info(f"✓ freegeoip.app: {location}")
                return location
        except Exception as e:
            logger.warning(f"freegeoip.app failed: {e}")
        return None
    
    def get_location(self) -> LocationData:
        """Get location with multiple fallbacks"""
        # Check cache first
        if self._is_cache_valid():
            logger.info("✓ Using cached location")
            return self.cache
        
        # Try each API in order
        apis = [
            self._try_ipapi,
            self._try_ipinfo,
            self._try_ipwhois,
            self._try_freegeoip
        ]
        
        for api_func in apis:
            location = api_func()
            if location:
                # Cache the result
                self.cache = location
                self.cache_time = time()
                return location
        
        # Fallback to default
        logger.warning("⚠️  All location APIs failed, using default")
        default = LocationData(
            city="Unknown",
            region="Unknown", 
            country="Unknown",
            country_code="XX",
            latitude=0.0,
            longitude=0.0,
            ip_address="Unknown",
            timezone="UTC"
        )
        return default

# ============================================================================
# ADVANCED WEATHER DETECTION (MULTIPLE APIS)
# ============================================================================

class WeatherDetector:
    """Detect weather using multiple APIs"""
    
    def __init__(self, location_detector: LocationDetector):
        self.location_detector = location_detector
        self.cache: Optional[Dict] = None
        self.cache_time: Optional[float] = None
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self.cache is None or self.cache_time is None:
            return False
        return (time() - self.cache_time) < WEATHER_CACHE_EXPIRY
    
    def _try_wttr(self, location: LocationData) -> Optional[WeatherData]:
        """Try wttr.in (text-based weather)"""
        try:
            logger.info(f"🌡️  Trying wttr.in for {location.city}...")
            
            # Try city name first
            query = location.city if location.city != "Unknown" else f"{location.latitude},{location.longitude}"
            
            response = requests.get(
                f"https://wttr.in/{query}?format=j1",
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': USER_AGENT}
            )
            
            if response.status_code == 200:
                data = response.json()
                current = data.get('current_condition', [{}])[0]
                
                weather = WeatherData(
                    temperature_c=float(current.get('temp_C', 0)),
                    temperature_f=float(current.get('temp_F', 0)),
                    condition=current.get('weatherDesc', [{}])[0].get('value', 'Unknown'),
                    humidity=int(current.get('humidity', 0)),
                    wind_speed=float(current.get('windspeedKmph', 0)),
                    feels_like_c=float(current.get('FeelsLikeC', 0))
                )
                logger.info(f"✓ wttr.in: {weather}")
                return weather
        except Exception as e:
            logger.warning(f"wttr.in failed: {e}")
        return None
    
    def _try_openmeteo(self, location: LocationData) -> Optional[WeatherData]:
        """Try open-meteo.com (free, no API key)"""
        try:
            logger.info(f"🌡️  Trying open-meteo.com...")
            
            if location.latitude == 0.0 and location.longitude == 0.0:
                return None
            
            response = requests.get(
                f"https://api.open-meteo.com/v1/forecast",
                params={
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'current_weather': 'true',
                    'temperature_unit': 'celsius'
                },
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                current = data.get('current_weather', {})
                
                temp_c = current.get('temperature', 0)
                temp_f = (temp_c * 9/5) + 32
                
                # Map WMO weather codes to conditions
                wmo_code = current.get('weathercode', 0)
                condition_map = {
                    0: 'Clear sky',
                    1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
                    45: 'Foggy', 48: 'Foggy',
                    51: 'Light drizzle', 53: 'Moderate drizzle', 55: 'Dense drizzle',
                    61: 'Slight rain', 63: 'Moderate rain', 65: 'Heavy rain',
                    71: 'Slight snow', 73: 'Moderate snow', 75: 'Heavy snow',
                    80: 'Rain showers', 81: 'Rain showers', 82: 'Heavy rain showers',
                    95: 'Thunderstorm', 96: 'Thunderstorm with hail'
                }
                condition = condition_map.get(wmo_code, 'Unknown')
                
                weather = WeatherData(
                    temperature_c=temp_c,
                    temperature_f=round(temp_f, 1),
                    condition=condition,
                    wind_speed=current.get('windspeed', 0)
                )
                logger.info(f"✓ open-meteo.com: {weather}")
                return weather
        except Exception as e:
            logger.warning(f"open-meteo.com failed: {e}")
        return None
    
    def _try_weatherapi(self, location: LocationData) -> Optional[WeatherData]:
        """Try weatherapi.com (has free tier)"""
        try:
            logger.info(f"🌡️  Trying weatherapi.com...")
            
            # WeatherAPI free tier allows queries without key for basic info
            query = location.city if location.city != "Unknown" else f"{location.latitude},{location.longitude}"
            
            response = requests.get(
                f"http://api.weatherapi.com/v1/current.json",
                params={
                    'key': 'demo',  # They have a demo key that works sometimes
                    'q': query,
                    'aqi': 'no'
                },
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                current = data.get('current', {})
                
                weather = WeatherData(
                    temperature_c=current.get('temp_c', 0),
                    temperature_f=current.get('temp_f', 0),
                    condition=current.get('condition', {}).get('text', 'Unknown'),
                    humidity=current.get('humidity', 0),
                    wind_speed=current.get('wind_kph', 0),
                    feels_like_c=current.get('feelslike_c', 0)
                )
                logger.info(f"✓ weatherapi.com: {weather}")
                return weather
        except Exception as e:
            logger.warning(f"weatherapi.com failed: {e}")
        return None
    
    def get_weather(self) -> WeatherData:
        """Get weather with multiple fallbacks"""
        # Check cache first
        if self._is_cache_valid():
            logger.info("✓ Using cached weather")
            return self.cache
        
        # Get location
        location = self.location_detector.get_location()
        
        # Try each weather API in order
        apis = [
            lambda: self._try_wttr(location),
            lambda: self._try_openmeteo(location),
            lambda: self._try_weatherapi(location)
        ]
        
        for api_func in apis:
            weather = api_func()
            if weather and weather.temperature_c != 0:
                # Cache the result
                self.cache = weather
                self.cache_time = time()
                return weather
        
        # Fallback to default
        logger.warning("⚠️  All weather APIs failed, using default")
        return WeatherData(
            temperature_c=0.0,
            temperature_f=32.0,
            condition="Unknown"
        )

# ============================================================================
# GLOBAL INSTANCES
# ============================================================================
location_detector = LocationDetector()
weather_detector = WeatherDetector(location_detector)

# ============================================================================
# REALTIME INFO GATHERING
# ============================================================================

def get_realtime_info() -> str:
    """Gather all real-time information"""
    try:
        # Get current time
        now = datetime.datetime.now()
        
        # Get location (cached if recent)
        location = location_detector.get_location()
        
        # Get weather (cached if recent)
        weather = weather_detector.get_weather()
        
        # Format info
        info_parts = [
            f"📅 Date & Time: {now.strftime('%A, %B %d, %Y at %H:%M:%S')}",
            f"🌍 Location: {location.city}, {location.region}, {location.country}",
            f"📍 IP Address: {location.ip_address}",
            f"🌡️  Temperature: {weather}",
        ]
        
        if weather.humidity:
            info_parts.append(f"💧 Humidity: {weather.humidity}%")
        
        if weather.wind_speed:
            info_parts.append(f"💨 Wind Speed: {weather.wind_speed} km/h")
        
        result = "\n".join(info_parts)
        logger.info(f"\n📊 Realtime Info:\n{result}")
        return result
        
    except Exception as e:
        logger.error(f"Error gathering realtime info: {e}")
        now = datetime.datetime.now()
        return f"📅 Date & Time: {now.strftime('%A, %B %d, %Y at %H:%M:%S')}"

# ============================================================================
# WEB SEARCH - DUCKDUCKGO
# ============================================================================

def search_duckduckgo_html(query: str) -> Optional[str]:
    """DuckDuckGo HTML search with improved parsing"""
    try:
        logger.info(f"🔍 DuckDuckGo: {query}")
        
        headers = {'User-Agent': USER_AGENT}
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            content = response.text
            results = []
            
            # Improved parsing
            parts = content.split('result__a')[1:6]
            
            for part in parts:
                try:
                    # Extract title
                    title_match = re.search(r'>([^<]{10,200})</a>', part)
                    if not title_match:
                        continue
                    
                    title = title_match.group(1)
                    # Clean HTML entities
                    title = (title.replace('&amp;', '&')
                                 .replace('&#x27;', "'")
                                 .replace('&quot;', '"')
                                 .replace('&lt;', '<')
                                 .replace('&gt;', '>'))
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    
                    # Extract snippet
                    snippet = ""
                    snippet_match = re.search(r'result__snippet[^>]*>([^<]+)', part)
                    if snippet_match:
                        snippet = snippet_match.group(1)
                        snippet = (snippet.replace('&amp;', '&')
                                        .replace('&#x27;', "'")
                                        .replace('&quot;', '"'))
                        snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                    
                    if title:
                        if snippet:
                            results.append(f"• {title}\n  {snippet}")
                        else:
                            results.append(f"• {title}")
                        
                        logger.info(f"  ✓ {title[:60]}...")
                
                except Exception as e:
                    logger.debug(f"Error parsing result: {e}")
                    continue
            
            if results:
                logger.info(f"✅ Found {len(results)} DuckDuckGo results")
                return "🔍 WEB SEARCH RESULTS:\n\n" + "\n\n".join(results)
        
        return None
        
    except Exception as e:
        logger.error(f"❌ DuckDuckGo error: {e}")
        return None

# ============================================================================
# WIKIPEDIA SEARCH
# ============================================================================

def extract_main_subject(query: str) -> str:
    """Extract main subject from query"""
    query_lower = query.lower()
    
    # Remove common question words
    remove_patterns = [
        r'\b(what|who|when|where|why|how|is|are|was|were|the|a|an)\b',
        r'\b(current|latest|recent|tell me|about|information)\b',
        r'\b(net worth|networth|wealth|fortune|money|details)\b',
    ]
    
    for pattern in remove_patterns:
        query_lower = re.sub(pattern, ' ', query_lower)
    
    # Clean up
    subject = ' '.join(query_lower.split())
    return subject.strip()

def search_wikipedia(query: str) -> Optional[str]:
    """Enhanced Wikipedia search"""
    try:
        logger.info(f"📚 Wikipedia: {query}")
        
        subject = extract_main_subject(query)
        logger.info(f"  → Subject: '{subject}'")
        
        results = []
        
        # Search API
        search_url = (
            f"https://en.wikipedia.org/w/api.php"
            f"?action=opensearch"
            f"&search={requests.utils.quote(subject)}"
            f"&limit=3&namespace=0&format=json"
        )
        
        response = requests.get(
            search_url,
            timeout=REQUEST_TIMEOUT,
            headers={'User-Agent': USER_AGENT}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if len(data) >= 3 and data[1]:
                titles = data[1]
                descriptions = data[2] if len(data) > 2 else []
                
                logger.info(f"  ✓ Found {len(titles)} Wikipedia articles")
                
                # Get detailed summary for first result
                if titles:
                    first_title = titles[0]
                    summary_url = (
                        f"https://en.wikipedia.org/api/rest_v1/page/summary/"
                        f"{requests.utils.quote(first_title.replace(' ', '_'))}"
                    )
                    
                    try:
                        sum_response = requests.get(
                            summary_url,
                            timeout=REQUEST_TIMEOUT,
                            headers={'User-Agent': USER_AGENT}
                        )
                        
                        if sum_response.status_code == 200:
                            sum_data = sum_response.json()
                            extract = sum_data.get('extract', '')
                            
                            if extract:
                                results.append(f"📖 {first_title}\n\n{extract}")
                                logger.info(f"  ✓ Got summary for: {first_title}")
                    except Exception as e:
                        logger.debug(f"Error getting summary: {e}")
                
                # Add other results
                for title, desc in zip(titles[1:], descriptions[1:]):
                    if desc:
                        results.append(f"📄 {title}: {desc}")
        
        if results:
            logger.info(f"✅ Wikipedia returned {len(results)} results")
            return "📚 WIKIPEDIA INFORMATION:\n\n" + "\n\n".join(results)
        
        logger.info("⚠️  No Wikipedia results")
        return None
        
    except Exception as e:
        logger.error(f"❌ Wikipedia error: {e}")
        return None

# ============================================================================
# GOOGLE SEARCH (OPTIONAL)
# ============================================================================

def search_google(query: str) -> Optional[str]:
    """Google search if library available"""
    try:
        from googlesearch import search
        
        logger.info(f"🔍 Google: {query}")
        results = []
        
        search_results = search(query, num_results=5, advanced=True)
        
        for result in search_results:
            title = getattr(result, 'title', 'No Title')
            description = getattr(result, 'description', '')
            
            if title and title != 'No Title':
                result_text = f"• {title}"
                if description:
                    result_text += f"\n  {description}"
                results.append(result_text)
                logger.info(f"  ✓ {title[:60]}...")
        
        if results:
            logger.info(f"✅ Found {len(results)} Google results")
            return "🔍 GOOGLE SEARCH RESULTS:\n\n" + "\n\n".join(results)
        
        return None
        
    except ImportError:
        logger.debug("Google search library not available")
        return None
    except Exception as e:
        logger.error(f"❌ Google search error: {e}")
        return None

# ============================================================================
# COMBINED WEB SEARCH
# ============================================================================

def search_web(query: str) -> str:
    """Combined web search with all methods"""
    results = []
    
    # Use ThreadPoolExecutor for parallel searching
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(search_google, query): "Google",
            executor.submit(search_duckduckgo_html, query): "DuckDuckGo",
            executor.submit(search_wikipedia, query): "Wikipedia"
        }
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                source = futures[future]
                logger.error(f"Error in {source} search: {e}")
    
    if results:
        return "\n\n" + "="*60 + "\n\n".join(results)
    
    logger.warning("❌ No search results found from any source")
    return "⚠️  No search results available. Answering based on AI training data (through January 2025)."

# ============================================================================
# PARALLEL DATA GATHERING
# ============================================================================

def gather_all_data(query: str) -> Tuple[str, str]:
    """Gather search results and real-time info in parallel"""
    with ThreadPoolExecutor(max_workers=2) as executor:
        search_future = executor.submit(search_web, query)
        info_future = executor.submit(get_realtime_info)
        
        search_results = search_future.result()
        realtime_info = info_future.result()
        
        return search_results, realtime_info

# ============================================================================
# MAIN REALTIME SEARCH ENGINE
# ============================================================================

def RealtimeSearchEngine(prompt: str) -> str:
    """Main search engine with real-time data"""
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"QUERY: {prompt}")
        logger.info('='*60)
        
        # Gather all data in parallel
        search_results, realtime_info = gather_all_data(prompt)
        
        # Load chat history
        messages = load_chatlog(max_messages=5)
        messages.append({"role": "user", "content": prompt})
        
        # Build system context
        system_messages = [
            {"role": "system", "content": System},
            {"role": "system", "content": f"REAL-TIME DATA:\n{realtime_info}"},
            {"role": "system", "content": f"SEARCH RESULTS:\n{search_results}"}
        ]
        
        logger.info(f"\n🤖 Generating AI response...")
        
        # Generate response with Groq
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=system_messages + messages,
            temperature=0.7,
            max_tokens=1000,
            top_p=1,
            stream=False
        )
        
        answer = completion.choices[0].message.content.strip()
        
        # Save to chat history
        full_messages = load_chatlog(max_messages=20)
        full_messages.extend([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer}
        ])
        save_chatlog(full_messages, max_keep=30)
        
        logger.info("✅ Response generated successfully")
        return answer
    
    except Exception as e:
        logger.error(f"❌ Error in RealtimeSearchEngine: {e}", exc_info=True)
        return f"I apologize, but I encountered an error: {str(e)}"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def AnswerModifier(answer: str) -> str:
    """Clean and format answer"""
    # Remove empty lines
    lines = [line for line in answer.split('\n') if line.strip()]
    return '\n'.join(lines)

def QueryModifier(query: str) -> str:
    """Clean and modify query"""
    return query.strip()

# ============================================================================
# TESTING/DEBUGGING FUNCTIONS
# ============================================================================

def test_location():
    """Test location detection"""
    print("\n" + "="*60)
    print("TESTING LOCATION DETECTION")
    print("="*60)
    
    location = location_detector.get_location()
    print(f"\n✓ Location: {location}")
    print(f"  City: {location.city}")
    print(f"  Region: {location.region}")
    print(f"  Country: {location.country} ({location.country_code})")
    print(f"  Coordinates: {location.latitude}, {location.longitude}")
    print(f"  IP Address: {location.ip_address}")
    print(f"  Timezone: {location.timezone}")

def test_weather():
    """Test weather detection"""
    print("\n" + "="*60)
    print("TESTING WEATHER DETECTION")
    print("="*60)
    
    weather = weather_detector.get_weather()
    print(f"\n✓ Weather: {weather}")
    print(f"  Temperature: {weather.temperature_c}°C / {weather.temperature_f}°F")
    print(f"  Condition: {weather.condition}")
    if weather.humidity:
        print(f"  Humidity: {weather.humidity}%")
    if weather.wind_speed:
        print(f"  Wind Speed: {weather.wind_speed} km/h")

def test_realtime_info():
    """Test complete real-time info gathering"""
    print("\n" + "="*60)
    print("TESTING REALTIME INFO")
    print("="*60)
    
    info = get_realtime_info()
    print(f"\n{info}")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 ADVANCED REALTIME SEARCH ENGINE")
    print("="*60)
    print("Features:")
    print("  ✓ Multiple IP location APIs with fallbacks")
    print("  ✓ Multiple weather APIs with fallbacks")
    print("  ✓ DuckDuckGo + Wikipedia + Google search")
    print("  ✓ Parallel data gathering for speed")
    print("  ✓ Intelligent caching")
    print("="*60 + "\n")
    
    # Test mode
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_location()
        test_weather()
        test_realtime_info()
        sys.exit(0)
    
    # Interactive mode
    try:
        while True:
            query = input("\n💬 Query (or 'exit' to quit): ").strip()
            
            if not query or query.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            response = RealtimeSearchEngine(query)
            
            print("\n" + "="*60)
            print("📝 ANSWER:")
            print("="*60)
            print(AnswerModifier(response))
            print("="*60)
    
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
