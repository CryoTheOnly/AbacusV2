import requests
import os
import time
import platform
import datetime
import json
import threading
from openai import OpenAI
from ddgs import DDGS
from dotenv import load_dotenv



#Variables
load_dotenv("keys/.env")
#API's
LLM_URL = 'http://10.0.0.231:1234/v1/chat/completions'
LLM_MODEL = 'Qwen3-4b'
API_KEY = os.getenv("API")
API_MODEL = "MODEL"
SPOT_API ='placeholder'

CHAT_MEMORY = "data/chats/chat.json"
os_name = platform.system()
Date = datetime.date.today()
Date = str(Date)
if os_name == "Windows" or "windows":
    def clear():
        os.system('cls')
elif os_name == "Linux" or "linux" or "Darwin" or "darwin":
    def clear():
        os.system('clear')
with open("data/personalities/Abacus.txt", "r") as file:
    personality = file.read()
if os.path.exists(CHAT_MEMORY):
    with open(CHAT_MEMORY, "r") as file:
        conversation = json.load(file)
else:
    conversation = [{"role": "system", "content": personality}]

client = OpenAI(api_key=API_KEY)

while True:
     user_msg = input("You: ")

     response = client.responses.create(
         model = API_MODEL,
         input = user_msg,

     )
     print(response.output_text);


    # ---- Main logic for search ----

     if "search" in response.output_text.lower():
            print("Search intent detected")
            print("Loading")
            search_req = user_msg
    #        time.sleep(2)
            with DDGS() as ddgs:
                result = ddgs.text(
                    search_req,
                    max_results=3
                )
                for r in result:
                    print("Title:", r["title"])
                    print("URL:", r["href"])
                    print("Snippet:", r["body"])
                    print("-" * 40)
                    time.sleep(20)
            Time = datetime.datetime.now().strftime("%H:%M:%S")
            log_file = "data/logs/"+Date+".log"
            if os.path.exists(log_file):
                with open(log_file, "a+") as file:
                    file.write("\n"+Time+"----SEARCH----"+user_msg)
            time.sleep(20)

    #error detection and log creation

     elif "text" in response.output_text.lower():
            print("No search intent detected")
            Time = datetime.datetime.now().strftime("%H:%M:%S")
            log_file = "data/logs/"+Date+".log"
            if os.path.exists(log_file):
                def log_message():
                    with open(log_file, "a+") as file:
                        file.write("\n"+Time+"----"+user_msg)
                threading.Thread(target=log_message).start()
#LLM Time
                if os.path.exists(CHAT_MEMORY):
                    with open(CHAT_MEMORY, "r") as f:
                        conversation = json.load(f)
                else:
                    conversation = [{"role": "system", "content": personality}]
                conversation.append({"role": "user", "content": user_msg})
                response = requests.post(LLM_URL, json={
                    "model": LLM_MODEL,
                    "messages": conversation,
                    "disable_chain_of_thought": True
                })
                reply = response.json()["choices"][0]["message"]["content"]
                print("Abacus: " + reply)
                conversation.append({"role": "assistant", "content": reply})
#Save conversation to json
                with open(CHAT_MEMORY, "w") as f:
                    json.dump(conversation, f, indent=2)

            else:
             def log_message_create():
                with open(log_file, "w") as file:
                    file.write("File created at----"+Time+"----"+user_msg)
            threading.Thread(target=log_message_create).start()

