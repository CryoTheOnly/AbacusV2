import requests
import os
import datetime
import threading
import json
import pythoncom
import chromadb
import win32com.client
import queue
import speech_recognition as sr
from sentence_transformers import SentenceTransformer
from chromadb.config import Settings



#Config
#=====================================
LLM_URL = 'http://10.0.0.231:1234/v1/chat/completions'
LLM_MODEL = 'qwen/qwen3-4b'
CHAT_MEMORY = "data/chats/chat.json"
PERSONALITY = "Pioneer"
Date = str(datetime.date.today())
wake_word = "observer"
Search_Site = "https://interface.ghst.best/ddg?q="
embedder = SentenceTransformer("all-MiniLM-L6-v2")  # local embedding model
chroma = chromadb.Client()
collection = chroma.get_or_create_collection("memory")

recognizer = sr.Recognizer()
SpeechRecoModel = "base"
WakeWordDetectModel = "tiny"
audio_queue = queue.Queue()
tts_queue = queue.Queue()

temp = 0.7
timeout = 60

#=====================================
#Defining                            
#=====================================

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

with open("data/Personalities/"+PERSONALITY+"/"+PERSONALITY+".txt", "r") as file:
    personality = file.read()

def convo_save():
    os.makedirs(os.path.dirname(CHAT_MEMORY), exist_ok=True)
    with open(CHAT_MEMORY, "w") as file:
        json.dump(conversation, file, indent=4)

def add_memory(text: str, memory_id: str):
    embedding = embedder.encode(text).tolist()
    collection.add(
        documents=[text],
        embeddings=[embedding],
        ids=[memory_id]
    )

def retrieve_memories(query: str, n_results: int = 3) -> list[str]:
    query_embedding = embedder.encode(query).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    return results["documents"][0] if results["documents"] else []

def chat_with_memory(user_message: str) -> str:
    # 1. Retrieve relevant memories
    memories = retrieve_memories(user_message)
    memory_context = "\n".join(f"- {m}" for m in memories)

if os.path.exists(CHAT_MEMORY):
    with open(CHAT_MEMORY, "r") as file:
        conversation = json.load(file)
    conversation[0] = {"role": "system", "content": personality}  # Keep personality in sync
else:
    conversation = [{"role": "system", "content": personality}]


def convo_save():
    os.makedirs(os.path.dirname(CHAT_MEMORY), exist_ok=True)
    with open(CHAT_MEMORY, "w") as file:
        json.dump(conversation, file, indent=4)


#=====================================
#Actual Code
#=====================================

def transcribe_audio(audio, model):
    """Run Whisper on raw audio data."""
    return recognizer.recognize_whisper(
        audio, model=model.model_name if hasattr(model, "model_name") else "base", language="en").lower()


def listen(source, timeout=5):
    try:
        return recognizer.listen(source, timeout=timeout, phrase_time_limit=None)
    except sr.WaitTimeoutError:
        return None


def tts_worker():
    pythoncom.CoInitialize()  # ← must be called on the thread that uses COM
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    while True:
        text = tts_queue.get()
        if text is None:
            break
        try:
            speaker.Speak(text)
        except Exception as e:
            print(f"TTS error: {e}")
    pythoncom.CoUninitialize()


threading.Thread(target=tts_worker, daemon=True).start()


def process_command(audio):
    try:
        SSTWords = recognizer.recognize_whisper(audio, model="base", language="en").lower()
        print("you said: " + SSTWords)
        conversation.append({"role": "user", "content": SSTWords})

        response = requests.post(LLM_URL, json={
        "model": LLM_MODEL,
        "messages": conversation,
        "temperature": 0.7,
        "chat_template_kwargs": {"thinking": False}  # Disable Qwen3 thinking mode
        }, timeout=60)

        
        
     #THIS IS WHERE EVERYTHING GOES    

        
    except sr.UnknownValueError:
        print("could not understand audio")


with sr.Microphone() as source:
    win32com.client.Dispatch("SAPI.SpVoice").Speak("calibrating")
    print("calibrating...")
    recognizer.adjust_for_ambient_noise(source, duration=10)
    win32com.client.Dispatch("SAPI.SpVoice").Speak("calibration complete")
    print(f"calibrated — say '{wake_word}' | ctrl+c to stop\n")

    while True:
        try:
            print("waiting for wake word...")
            audio = listen(source)
            if audio is None:
                continue

            SSTWords = recognizer.recognize_whisper(audio, model="tiny", language="en").lower()

            if wake_word not in SSTWords:
                continue

            print("wake word detected, listening for command...")
            audio = listen(source)
            if audio is None:
                continue
            threading.Thread(target=process_command, args=(audio,), daemon=True).start()


        except sr.UnknownValueError:
            pass
        except KeyboardInterrupt:
            tts_queue.put(None)
            print("stopping...")
            break