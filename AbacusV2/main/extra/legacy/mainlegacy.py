import requests
import os
import time
import re
import datetime
import json
import threading
from openai import OpenAI
from dotenv import load_dotenv



#Variables
load_dotenv(".env")
#API's
LLM_URL = 'http://10.0.0.231:1234/v1/chat/completions'
LLM_MODEL = 'Qwen3-4b'
API_KEY = os.getenv("API")
API_MODEL = os.getenv("MODEL")
CHAT_MEMORY = "data/chats/chat.json"
PERSONALITY = "Abacus"
Date = str(datetime.date.today())
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

with open("data/Personalities/"+PERSONALITY+"/"+PERSONALITY+".txt", "r") as file:
    personality = file.read()

if os.path.exists(CHAT_MEMORY):
    with open(CHAT_MEMORY, "r") as file:
        conversation = json.load(file)
else:
    conversation = [{"role": "system", "content": personality}]

tags_to_remove = [
    "<p>", "</p>", "<span>", "</span>", "<div>", "</div>", "<br>",
    "<h1>", "</h1>", "<h2>", "</h2>", "<h3>", "</h3>", "<h4>", "</h4>",
    "<h5>", "</h5>", "<h6>", "</h6>", "<ul>", "</ul>", "<ol>", "</ol>",
    "<li>", "</li>", "<a>", "</a>", "<table>", "</table>",
    "<tr>", "</tr>", "<td>", "</td>", "<th>", "</th>",
    "<strong>", "</strong>", "<b>", "</b>", "<em>", "</em>",
    "<i>", "</i>", "<u>", "</u>", "<mark>", "</mark>",
    "<small>", "</small>", "<article>", "</article>",
    "<section>", "</section>", "<main>", "</main>",
    "<header>", "</header>", "<footer>", "</footer>",
    "<aside>", "</aside>", "<nav>", "</nav>",
    "<label>", "</label>", "<button>", "</button>",
    "<caption>", "</caption>", "<figcaption>", "</figcaption>", "..."
]

def ping_website(search_url):
    try:
        response = requests.head(search_url, timeout=5)
        return response.status_code < 400
    except requests.RequestException:
        return False
    

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
        user_msg_q= "+".join(user_msg.split())
        search_req = user_msg_q
        if ping_website("https://interface.ghst.best/ddg?q="+search_req):
            print("Search intent detected")
            print("Loading")
            awnsers = requests.get("https://interface.ghst.best/ddg?q="+search_req)
            awnsers = awnsers.json()
            awnsers = (awnsers[0]["snippet"])
            for tag in tags_to_remove:
                awnsers = awnsers.replace(tag, "")
            awnsers = re.sub(r"\[.*?\]", "", awnsers)
            awnsers = re.sub(r"\s{2,}", " ", awnsers).strip()
            print(awnsers)
            Time = datetime.datetime.now().strftime("%H:%M:%S")
            log_file = "data/logs/"+Date+".log"
                
            if os.path.exists(log_file):
                def log_message():
                    with open(log_file, "a+") as file:
                        file.write("\n"+Time+"----"+user_msg)
                threading.Thread(target=log_message).start()
            else:
                def log_message_create():
                    with open(log_file, "w") as file:
                        file.write("File created at----"+Time+"----"+user_msg)
                threading.Thread(target=log_message_create).start()
            time.sleep(2),
        else:
            print("error")

            Time = datetime.datetime.now().strftime("%H:%M:%S")
            log_file = "data/logs/"+Date+".log"
            if os.path.exists(log_file):
                def log_message():
                    with open(log_file, "a+") as file:
                        file.write("\n"+Time+"----"+user_msg+"ERROR, COULDNT CONNECT TO SEARCH URL, DIDNT GO THROUGH")
                threading.Thread(target=log_message).start()
            else:
                def log_message_create():
                    with open(log_file, "w") as file:
                        file.write("File created at----"+Time+"----"+user_msg)
                threading.Thread(target=log_message_create).start()
                time.sleep(2)

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
                print(reply+"\n")
                conversation.append({"role": "assistant", "content": reply})
#Save conversation to json
                with open(CHAT_MEMORY, "w") as f:
                    json.dump(conversation, f, indent=2)

            else:
                def log_message_create():
                    with open(log_file, "w") as file:
                        file.write("File created at----"+Time+"----"+user_msg)
                threading.Thread(target=log_message_create).start()

