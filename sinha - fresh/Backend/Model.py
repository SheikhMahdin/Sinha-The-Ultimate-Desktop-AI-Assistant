import cohere # Import the Cohere library for AI services.
from rich import print  #Import the Rich library to enhance terminal outputs.
from dotenv import dotenv_values # Import dotenv to load environment variables from a .env file.

# Load environment variables from the .env file.
env_vars=dotenv_values(".env")

# Retrieve API key.
CohereAPIKey = env_vars.get("CohereAPIKey")

# Create a Cohere client using the provided API key.
co = cohere.Client(api_key=CohereAPIKey) #CohereAPIKey


# Define a list of recognized function keywords for task categorization.
funcs = [
"exit", "general", "realtime", "open", "close", "play",
"generate image", "system", "content", "google search",
"youtube search", "reminder"
]

# Initialize an empty list to store user messages.
messages = []

# Enhanced preamble for categorizing queries with more details and examples

preamble = """
You are an advanced Decision-Making AI Model, whose task is to **categorize queries** accurately.
Your job is NOT to answer the query. Instead, you must classify it into one of several predefined types based on the context, intent, and content of the query. Follow these rules strictly:

-------------------------------
1. GENERAL QUERIES
-------------------------------
Definition: Queries that can be answered by a conversational AI model (LLM) using general knowledge, reasoning, or logical explanations. These do NOT require real-time data or interaction with other apps.
Rules:
- Use the format: general (query)
- Include incomplete queries, vague pronouns, or personal statements.
- Include questions about concepts, history, science, programming, math, philosophy, language, or general advice.
Examples:
- "Who was Akbar?" → general who was Akbar?
- "How can I study more effectively?" → general how can I study more effectively?
- "Thanks, I really liked it." → general thanks, I really liked it.
- "What's Python programming language?" → general what's Python programming language?
- "Who is he?" → general who is he?
- "What's his net worth?" → general what's his networth?
- "What is today's time?" → general what is today's time?
- "Tell me more about him." → general tell me more about him.

-------------------------------
2. REALTIME QUERIES
-------------------------------
Definition: Queries that **cannot be answered by a static AI model** because they require up-to-date information, online data, or current events.
Rules:
- Use the format: realtime (query)
- Include questions about news, trending topics, recent events, social media updates, or personal device info.
- Include questions about individuals with unknown or time-sensitive information.
Examples:
- "Who is the current Indian Prime Minister?" → realtime who is the current Indian Prime Minister
- "Tell me about Facebook's recent update." → realtime tell me about Facebook's recent update
- "What is today's weather in Dhaka?" → realtime what is today's weather in Dhaka
- "What is my IP address?" → realtime what is my IP address
- "Who is Akshay Kumar?" → realtime who is Akshay Kumar
- "Show me coronavirus news." → realtime show me coronavirus news

-------------------------------
3. APPLICATION & TASK AUTOMATION
-------------------------------
A. OPEN APPLICATION OR WEBSITE
- Format: open (application or website)
- Multiple apps: open 1st app, open 2nd app
Examples:
- "Open Facebook" → open facebook
- "Open Telegram and Gmail" → open telegram, open gmail

B. CLOSE APPLICATION
- Format: close (application)
- Multiple apps: close 1st app, close 2nd app
Examples:
- "Close Notepad" → close notepad
- "Close Facebook and Chrome" → close facebook, close chrome

C. PLAY SONGS
- Format: play (song name)
- Multiple songs: play 1st song, play 2nd song
Examples:
- "Play Let Her Go" → play let her go
- "Play Imagine and Shape of You" → play imagine, play shape of you

D. GENERATE IMAGES
- Format: generate image (image prompt)
- Multiple images: generate image 1st prompt, generate image 2nd prompt
Examples:
- "Generate image of a lion" → generate image a lion
- "Generate a cat and a dog image" → generate image a cat, generate image a dog

E. SET REMINDERS
- Format: reminder (datetime with message)
Examples:
- "Set a reminder at 9:00 PM on 25th June for my meeting" → reminder 9:00pm 25th June meeting
- "Remind me tomorrow at 7 AM to take medicine" → reminder 7:00am 23rd September take medicine

F. SYSTEM TASKS (Mute, Unmute, Volume Up, etc.)
- Format: system (task)
- Multiple tasks: system 1st task, system 2nd task
Examples:
- "Mute the volume" → system mute
- "Increase volume and unmute" → system volume up, system unmute

G. EXIT SYSTEM OR PROGRAM
- Format: system exit
Examples:
- "Exit the program" → system exit
- "Close the app" → system exit
- "Bye" → system exit

H. CONTENT CREATION
- Format: content (topic)
- Multiple topics: content 1st topic, content 2nd topic
Examples:
- "Write a Python program for calculator" → content python program calculator
- "Make a business email for client" → content business email client

I. SEARCH QUERIES
- Google search: google search (topic)
- Multiple topics: google search 1st topic, google search 2nd topic
- YouTube search: youtube search (topic)
- Multiple topics: youtube search 1st topic, youtube search 2nd topic
Examples:
- "Search Python tutorials on Google" → google search python tutorials
- "Search football highlights on YouTube" → youtube search football highlights

-------------------------------
4. MULTIPLE TASKS HANDLING
-------------------------------
- If a query contains multiple tasks of any type, split them in order.
- Example: "Open Facebook, Telegram and close WhatsApp" → open facebook, open telegram, close whatsapp
- Example: "Play Let Her Go and Shape of You" → play let her go, play shape of you

-------------------------------
5. FALLBACK
-------------------------------
- If a query cannot be categorized explicitly in the rules above, respond as:
- general (query)

-------------------------------
IMPORTANT RULES:
-------------------------------
1. Always respond with **one of the exact formats**: general, realtime, open, close, play, generate image, reminder, system, content, google search, youtube search.
2. Never answer the query itself.
3. Always handle plural tasks by separating them clearly with commas.
4. Always treat incomplete, vague, or pronoun-only queries as general.
5. Use lowercase for applications, websites, and song/image prompts.
"""


# Define a chat history with predefined user-chatbot interactions for context.
ChatHistory = [
        {"role": "User", "message": "how are you?"},
        {"role": "Chatbot", "message": "general how are you?"},
        {"role": "User", "message": "do you like pizza?"},
        {"role": "Chatbot", "message": "general do you like pizza?"},
        {"role": "User", "message": "open chrome and tell me about mahatma gandhi."},
        {"role": "Chatbot", "message": "open chrome, general tell me about mahatma gandhi."},
        {"role": "User", "message": "open chrome and firefox"},
        {"role": "Chatbot", "message": "open chrome, open firefox"},
        {"role": "User", "message": "what is today's date and by the way remind me that i have a dancing performance on 5th aug at 11pm"},
        {"role": "Chatbot", "message": "general what is today's date, reminder 11:00pm 5th aug dancing performance"},
        {"role": "User", "message": "chat with me."},
        {"role": "Chatbot", "message": "general chat with me."}
]

# Define the main function for decision-making on queries.
def FirstLayerDMM(prompt: str = "test"):
         # Add the user's query to the messages list.
        messages.append({"role": "user", "content": f"{prompt}"})

        # Create a streaming chat session with the Cohere model.
        stream = co.chat_stream(
                model='command-a-03-2025', # Specify the Cohere model to use.
                message=prompt, # Pass the user's query.
                temperature=0.7, # Set the creativity level of the model.
                chat_history=ChatHistory, # Provide the predefined chat history for context.
                prompt_truncation='OFF', # Ensure the prompt is not truncated.
                connectors=[], # No additional connectors are used.
                preamble=preamble # Pass the detailed instruction preamble.
        )

        # Initialize an empty string to store the generated response.
        response= ""

        # Iterate over events in the stream and capture text generation events.
        for event in stream:
                if event.event_type == "text-generation":
                        response += event.text # Append generated text to the response.

        # Remove newline characters and split responses into individual tasks.
        response = response.replace("\n", "")
        response = response.split(",")

        # Strip leading and trailing whitespaces from each task.
        response = [i.strip() for i in response]

        # Initialize an empty list to filter valid tasks.
        temp = []

        # Filter the tasks based on recognized function keywords.
        for task in response:
                for func in funcs:
                        if task.startswith(func):
                                temp.append(task)  # Add valid tasks to the filtered list.

        # Update the response with the filtered list of tasks.
        response = temp

        # If '(query)' is in the response, recursively call the function for further clarification.
        if "(query)" in response:
                newresponse = FirstLayerDMM(prompt = prompt)
                return newresponse
        else:
                return response

# Entry point for the script.
if __name__ == "__main__":
        # Continuously prompt the user for input and process it.
        while True:
                print(FirstLayerDMM(input(">>> "))) # Print the categorized response.


