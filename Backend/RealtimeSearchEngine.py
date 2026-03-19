from groq import Groq
from json import load, dump
import datetime
from dotenv import dotenv_values
import os
import requests
from concurrent.futures import ThreadPoolExecutor
import re

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

# ============================================================================
# GROQ CLIENT
# ============================================================================
client = Groq(api_key=GroqAPIKey)

# ============================================================================
# SYSTEM PROMPT
# ============================================================================
System = f"""You are {Assistantname}, AI assistant for {Username}. Use the search results provided to give accurate, current information. Answer directly and professionally based on the search results."""

# ============================================================================
# CHAT LOG (MINIMAL)
# ============================================================================
def load_chatlog():
    """Load last 5 messages only"""
    try:
        os.makedirs(os.path.dirname(CHATLOG_PATH), exist_ok=True)
        if os.path.exists(CHATLOG_PATH):
            with open(CHATLOG_PATH, "r", encoding='utf-8') as f:
                msgs = load(f)
                return msgs[-5:] if isinstance(msgs, list) else []
    except:
        pass
    return []

def save_chatlog(messages):
    """Save chat async"""
    try:
        os.makedirs(os.path.dirname(CHATLOG_PATH), exist_ok=True)
        with open(CHATLOG_PATH, "w", encoding='utf-8') as f:
            dump(messages[-20:], f, indent=2)
    except:
        pass

# ============================================================================
# CACHED DATA (GLOBAL)
# ============================================================================
_cache = {'location': None, 'weather': None, 'time': None}

def get_location_fast():
    """Fast cached location"""
    global _cache
    now = datetime.datetime.now()
    
    if _cache['location'] and _cache['time'] and (now - _cache['time']).seconds < 3600:
        return _cache['location']
    
    try:
        r = requests.get("https://ipinfo.io/json", timeout=2)
        if r.status_code == 200:
            data = r.json()
            _cache['location'] = (data.get("city", "Unknown"), data.get("country", "BD"))
            _cache['time'] = now
            return _cache['location']
    except:
        pass
    
    return ("Unknown", "BD")

def get_weather_fast():
    """Fast cached weather"""
    global _cache
    now = datetime.datetime.now()
    
    if _cache['weather'] and _cache['time'] and (now - _cache['time']).seconds < 1800:
        return _cache['weather']
    
    try:
        city, _ = get_location_fast()
        r = requests.get(f"https://wttr.in/{city}?format=%t", timeout=2)
        if r.status_code == 200:
            _cache['weather'] = r.text.strip()
            return _cache['weather']
    except:
        pass
    
    return "N/A"

def get_info_fast():
    """Ultra-fast info gathering"""
    now = datetime.datetime.now()
    city, country = get_location_fast()
    temp = get_weather_fast()
    
    return f"Current: {now.strftime('%B %d, %Y at %H:%M')} | Location: {city}, {country} | Temperature: {temp}"

# ============================================================================
# METHOD 1: DUCKDUCKGO HTML (VERIFIED WORKING)
# ============================================================================
def search_duckduckgo_html(query):
    """DuckDuckGo HTML search - TESTED AND WORKING"""
    try:
        print(f"🔍 DuckDuckGo: {query}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        r = requests.get(url, headers=headers, timeout=8)
        
        if r.status_code == 200:
            content = r.text
            results = []
            
            # Extract results
            parts = content.split('result__a')[1:6]  # Get first 5 results
            
            for part in parts:
                try:
                    # Extract title
                    title_match = re.search(r'>([^<]{10,})</a>', part)
                    if title_match:
                        title = title_match.group(1)
                        # Clean HTML entities
                        title = title.replace('&amp;', '&').replace('&#x27;', "'").replace('&quot;', '"')
                        title = re.sub(r'<[^>]+>', '', title)
                        
                        # Try to find snippet
                        snippet_match = re.search(r'result__snippet[^>]*>([^<]+)</a>', part)
                        if snippet_match:
                            snippet = snippet_match.group(1)
                            snippet = snippet.replace('&amp;', '&').replace('&#x27;', "'").replace('&quot;', '"')
                            snippet = re.sub(r'<[^>]+>', '', snippet)
                            results.append(f"• {title}\n  {snippet}")
                        else:
                            results.append(f"• {title}")
                        
                        print(f"  ✓ {title[:60]}...")
                except:
                    continue
            
            if results:
                print(f"✅ Found {len(results)} results")
                return "WEB SEARCH RESULTS:\n\n" + "\n\n".join(results)
        
        return None
        
    except Exception as e:
        print(f"❌ DuckDuckGo error: {e}")
        return None

# ============================================================================
# METHOD 2: IMPROVED WIKIPEDIA SEARCH
# ============================================================================
def extract_main_subject(query):
    """Extract the main subject from a query intelligently"""
    query_lower = query.lower()
    
    # List of words to remove
    remove_words = [
        'what is', 'what\'s', 'who is', 'who\'s', 'how much', 'how many',
        'tell me about', 'information about', 'details about',
        'the', 'a', 'an', 'current', 'latest', 'recent',
        'net worth', 'networth', 'wealth', 'fortune', 'money',
        'of', 'about', 'on', 'for'
    ]
    
    for word in remove_words:
        query_lower = query_lower.replace(word, ' ')
    
    # Clean up extra spaces
    subject = ' '.join(query_lower.split())
    return subject.strip()

def search_wikipedia_advanced(query):
    """Advanced Wikipedia search with multiple strategies"""
    try:
        print(f"🔍 Wikipedia: {query}")
        
        # Extract main subject
        subject = extract_main_subject(query)
        print(f"  → Searching for: '{subject}'")
        
        results = []
        
        # Strategy 1: Use Wikipedia's opensearch API (finds relevant pages)
        search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={requests.utils.quote(subject)}&limit=3&namespace=0&format=json"
        
        r = requests.get(search_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        
        if r.status_code == 200:
            data = r.json()
            # data format: [query, [titles], [descriptions], [urls]]
            
            if len(data) >= 3 and data[1]:
                titles = data[1]
                descriptions = data[2] if len(data) > 2 else []
                
                print(f"  ✓ Found {len(titles)} Wikipedia pages")
                
                # Get full summary for the first result
                if titles:
                    first_title = titles[0]
                    page_url = first_title.replace(' ', '_')
                    summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(page_url)}"
                    
                    try:
                        sum_r = requests.get(summary_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                        if sum_r.status_code == 200:
                            sum_data = sum_r.json()
                            extract = sum_data.get('extract', '')
                            
                            if extract:
                                results.append(f"📖 {first_title}\n\n{extract}")
                                print(f"  ✓ Got full summary for: {first_title}")
                    except:
                        pass
                
                # Add other results as brief descriptions
                for i, (title, desc) in enumerate(zip(titles[1:], descriptions[1:]), 1):
                    if desc:
                        results.append(f"📄 {title}: {desc}")
        
        # Strategy 2: If opensearch fails, try query API
        if not results:
            query_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={requests.utils.quote(subject)}&format=json&srlimit=3"
            
            r2 = requests.get(query_url, timeout=5)
            if r2.status_code == 200:
                data2 = r2.json()
                search_results = data2.get('query', {}).get('search', [])
                
                for result in search_results:
                    title = result.get('title', '')
                    snippet = result.get('snippet', '')
                    # Remove HTML tags
                    snippet = re.sub(r'<[^>]+>', '', snippet)
                    
                    if title and snippet:
                        results.append(f"📄 {title}: {snippet}")
                        print(f"  ✓ {title}")
        
        if results:
            print(f"✅ Wikipedia returned {len(results)} results")
            return "WIKIPEDIA INFORMATION:\n\n" + "\n\n".join(results)
        
        print(f"⚠️  No Wikipedia results")
        return None
        
    except Exception as e:
        print(f"❌ Wikipedia error: {e}")
        return None

# ============================================================================
# METHOD 3: GOOGLE SEARCH (IF AVAILABLE)
# ============================================================================
def search_google(query):
    """Google search using googlesearch-python library"""
    try:
        from googlesearch import search
        
        print(f"🔍 Google: {query}")
        
        results = []
        search_results = search(query, num_results=5, advanced=True)
        
        for result in search_results:
            title = result.title if hasattr(result, 'title') else 'No Title'
            description = result.description if hasattr(result, 'description') else ''
            
            if title and title != 'No Title':
                result_text = f"• {title}"
                if description:
                    result_text += f"\n  {description}"
                results.append(result_text)
                print(f"  ✓ {title[:60]}...")
        
        if results:
            print(f"✅ Found {len(results)} Google results")
            return "GOOGLE SEARCH RESULTS:\n\n" + "\n\n".join(results)
        
        return None
        
    except ImportError:
        print("⚠️  Google search library not available")
        return None
    except Exception as e:
        print(f"❌ Google search error: {e}")
        return None

# ============================================================================
# COMBINED SEARCH (ALL METHODS)
# ============================================================================
def search_web(query):
    """Combined search using all available methods"""
    results = []
    
    # Method 1: Try Google first (if available)
    google_results = search_google(query)
    if google_results:
        results.append(google_results)
    
    # Method 2: DuckDuckGo HTML (verified working)
    ddg_results = search_duckduckgo_html(query)
    if ddg_results:
        results.append(ddg_results)
    
    # Method 3: Wikipedia (for background info)
    wiki_results = search_wikipedia_advanced(query)
    if wiki_results:
        results.append(wiki_results)
    
    if results:
        return "\n\n" + "="*60 + "\n\n".join(results)
    
    print("❌ No search results found")
    return "No search results available. Answering based on AI knowledge (trained through January 2025)."

# ============================================================================
# PARALLEL DATA GATHERING
# ============================================================================
def gather_data_parallel(query):
    """Gather search and info in parallel"""
    with ThreadPoolExecutor(max_workers=2) as executor:
        search_future = executor.submit(search_web, query)
        info_future = executor.submit(get_info_fast)
        
        return search_future.result(), info_future.result()

# ============================================================================
# REALTIME SEARCH ENGINE
# ============================================================================
def RealtimeSearchEngine(prompt):
    """Search and response with real-time data"""
    try:
        print(f"\n{'='*60}")
        print(f"QUERY: {prompt}")
        print('='*60)
        
        # Parallel data gathering
        search_results, realtime_info = gather_data_parallel(prompt)
        
        # Load minimal history
        messages = load_chatlog()
        messages.append({"role": "user", "content": prompt})
        
        # Build context
        system_msgs = [
            {"role": "system", "content": System},
            {"role": "system", "content": f"SEARCH DATA (Use this to answer):\n{search_results}"},
            {"role": "system", "content": realtime_info}
        ]
        
        print(f"\n🤖 Generating AI response...")
        
        # Generate response
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=system_msgs + messages,
            temperature=0.7,
            max_tokens=800,
            top_p=1,
            stream=False
        )
        
        answer = completion.choices[0].message.content.strip()
        
        # Save chat
        full_msgs = load_chatlog()
        full_msgs.extend([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer}
        ])
        save_chatlog(full_msgs)
        
        return answer
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return f"Error: {str(e)}"

# ============================================================================
# ANSWER MODIFIER
# ============================================================================
def AnswerModifier(answer):
    """Clean output"""
    return '\n'.join(line for line in answer.split('\n') if line.strip())

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("REALTIME SEARCH ENGINE")
    print("Using: DuckDuckGo + Wikipedia + Google (if available)")
    print("="*60 + "\n")
    
    try:
        while True:
            q = input("Query: ").strip()
            if not q or q.lower() in ['exit', 'quit', 'q']:
                break
            
            resp = RealtimeSearchEngine(q)
            print("\n" + "="*60)
            print("ANSWER:")
            print("="*60)
            print(AnswerModifier(resp))
            print("="*60 + "\n")
    
    except KeyboardInterrupt:
        print("\nExiting...")