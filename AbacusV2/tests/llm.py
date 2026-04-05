import requests
import os
import json
import datetime
import pyttsx3
import threading

# Variables
LLM_URL = 'http://10.0.0.231:1234/v1/chat/completions'
LLM_MODEL = 'qwen/qwen3-4b'
PERSONALITY = "Abacus"
CHAT_MEMORY = "data/chats/chat.json"
Date = str(datetime.date.today())
engine = pyttsx3.init()

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def convo_save():
    os.makedirs(os.path.dirname(CHAT_MEMORY), exist_ok=True)
    with open(CHAT_MEMORY, "w") as file:
        json.dump(conversation, file, indent=4)

# Load personality
with open("data/Personalities/" + PERSONALITY + "/" + PERSONALITY + ".txt", "r") as file:
    personality = file.read()

# Load or create conversation, always keep system prompt current
if os.path.exists(CHAT_MEMORY):
    with open(CHAT_MEMORY, "r") as file:
        conversation = json.load(file)
    conversation[0] = {"role": "system", "content": personality}  # Keep personality in sync
else:
    conversation = [{"role": "system", "content": personality}]

# Get user input
text = input("You: ")
conversation.append({"role": "user", "content": text})

# Send to LLM

response = requests.post(LLM_URL, json={
    "model": LLM_MODEL,
    "messages": conversation,
    "temperature": 0.7,
    "chat_template_kwargs": {"thinking": False}  # Disable Qwen3 thinking mode
}, timeout=60)
response.raise_for_status()

LLMReply = response.json()["choices"][0]["message"]["content"]
print("Pioneer: " + LLMReply)

# Append assistant reply before saving
conversation.append({"role": "assistant", "content": LLMReply})

threading.Thread(target=convo_save, daemon=True).start() 

engine.say(LLMReply)
engine.runAndWait()

# Save conversation
