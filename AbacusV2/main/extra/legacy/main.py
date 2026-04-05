import requests
import os
import sys
import time
import platform
import json
import threading
import socket
import re
import datetime
from datetime import date
from openai import OpenAI
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from ddgs import DDGS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity



#Variables
load_dotenv("keys/.env")
#API's
LLM_URL = 'http://10.0.0.231:1234/v1/chat/completions'
LLM_MODEL = 'Qwen3-4b'
API_KEY = os.getenv("API")
API_MODEL = "MODEL"
SPOT_API ='placeholder'
MAX_RESULTS = 6
VERBOSE = False
REF_DATE = date(2026, 2, 12)
MIN_SENT_LEN = 40
CHAT_MEMORY = "data/chats/chat.json"
os_name = platform.system()
Date = datetime.date.today()
Date = str(Date)
if os_name == "Windows" or "windows":
    def clear():
        os.system('cls')
elif os_name == "Linux" or "linux" or "Darwin" or "darwin":
    def clear():
        os.system0('clear')
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
         def vprint(*a, **k):
            if VERBOSE:
                print(*a, **k)

        # ---------- Search ----------
            def search_ddg(query, max_results=MAX_RESULTS):
                try:
                    with DDGS() as ddgs:
                        return list(ddgs.text(query, max_results=max_results))
                except Exception as e:
                    vprint("search_ddg error:", e)
                    return []

            # ---------- Fetch ----------
            def fetch_text(url):
                try:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    r = requests.get(url, headers=headers, timeout=8)
                    r.raise_for_status()
                    soup = BeautifulSoup(r.text, "html.parser")
                    for tag in soup(["script", "style", "noscript", "header", "footer", "svg", "form"]):
                        tag.decompose()
                    text = soup.get_text(separator=" ")
                    text = re.sub(r"\s+", " ", text).strip()
                    return text
                except Exception as e:
                    vprint(f"fetch_text failed for {url!r}: {e}")
                    return ""

            # ---------- Date / Age helpers ----------
            MONTHS = {
                "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
                "july":7,"august":8,"september":9,"october":10,"november":11,"december":12
            }

            def find_birthdate_in_text(text):
                """Try several common date formats. Return datetime.date or None."""
                if not text:
                    return None

                # Full month name: June 8, 1977
                m = re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(\d{4})\b', text, re.I)
                if m:
                    month = MONTHS[m.group(1).lower()]; day = int(m.group(2)); year = int(m.group(3))
                    try: return date(year, month, day)
                    except: pass

                # Abbrev: Jun 8, 1977
                m = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(\d{1,2}),\s*(\d{4})\b', text, re.I)
                if m:
                    mon_map = {"jan":"january","feb":"february","mar":"march","apr":"april","may":"may","jun":"june",
                            "jul":"july","aug":"august","sep":"september","sept":"september","oct":"october",
                            "nov":"november","dec":"december"}
                    mon = m.group(1).lower()
                    if mon in mon_map:
                        month = MONTHS[mon_map[mon]]; day = int(m.group(2)); year = int(m.group(3))
                        try: return date(year, month, day)
                        except: pass

                # Day Month Year: 8 June 1977
                m = re.search(r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b', text, re.I)
                if m:
                    day = int(m.group(1)); month = MONTHS[m.group(2).lower()]; year = int(m.group(3))
                    try: return date(year, month, day)
                    except: pass

                # ISO-ish: 1977-06-08
                m = re.search(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', text)
                if m:
                    year = int(m.group(1)); month = int(m.group(2)); day = int(m.group(3))
                    try: return date(year, month, day)
                    except: pass

                return None

            def compute_age(born_date, ref_date=REF_DATE):
                years = ref_date.year - born_date.year
                if (ref_date.month, ref_date.day) < (born_date.month, born_date.day):
                    years -= 1
                return years

            def extract_age_from_sentence(sentence):
                """
                If sentence contains 'X years old' pattern, return integer X (may be stale).
                Otherwise None.
                """
                m = re.search(r'\b(\d{1,3})\s+(years old|yrs old|yo|y\.o\.)\b', sentence, re.I)
                if m:
                    try:
                        return int(m.group(1))
                    except:
                        return None
                m2 = re.search(r'\bcurrently\s+(\d{1,3})\b', sentence, re.I)
                if m2:
                    try:
                        return int(m2.group(1))
                    except:
                        return None
                return None

            # ---------- Simple TF-IDF sentence extraction ----------
            def extract_best_sentence(text, query):
                # split sentences (simple)
                sents = re.split(r'(?<=[\.\?\!])\s+', text)
                sents = [s.strip() for s in sents if len(s.strip()) >= MIN_SENT_LEN]
                if not sents:
                    return ""

                try:
                    vect = TfidfVectorizer(stop_words="english")
                    mat = vect.fit_transform(sents + [query])
                    query_vec = mat[-1]
                    sent_vecs = mat[:-1]
                    sims = cosine_similarity(query_vec, sent_vecs).flatten()
                    best_idx = sims.argmax()
                    return sents[best_idx]
                except Exception as e:
                    vprint("extract_best_sentence TF-IDF error:", e)
                    return sents[0]

            # ---------- Wikipedia fallback (summary) ----------
            def wikipedia_fallback(query):
                """Return the wiki summary text or ''."""
                try:
                    search_url = "https://en.wikipedia.org/w/api.php"
                    params = {"action": "query", "list": "search", "srsearch": query, "format": "json"}
                    r = requests.get(search_url, params=params, timeout=6)
                    r.raise_for_status()
                    data = r.json()
                    hits = data.get("query", {}).get("search", [])
                    if not hits:
                        return ""
                    title = hits[0]["title"]
                    summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
                    r2 = requests.get(summary_url, timeout=6)
                    if r2.status_code != 200:
                        return ""
                    summary_data = r2.json()
                    return summary_data.get("extract", "")
                except Exception as e:
                    vprint("wikipedia_fallback error:", e)
                    return ""

            # ---------- Main answer function ----------
            def answer_query(query):
                query_stripped = query.strip()
                if not query_stripped:
                    return "No query provided."

                # If this looks like an age question, try Wikipedia first for birthdate
                if re.search(r'\bhow old\b', query_stripped.lower()):
                    # attempt wiki summary
                    wiki_text = wikipedia_fallback(query_stripped)
                    vprint("Wikipedia length:", len(wiki_text))
                    if wiki_text:
                        bd = find_birthdate_in_text(wiki_text)
                        if bd:
                            age = compute_age(bd)
                            name = guess_name_from_query(query_stripped)
                            monthname = bd.strftime("%B")
                            return f"{name} is {age} years old (born {monthname} {bd.day}, {bd.year})."
                        # if wiki summary doesn't have a birthdate but contains "years old", use it (less reliable)
                        sent = extract_best_sentence(wiki_text, query_stripped)
                        if sent:
                            possible_age = extract_age_from_sentence(sent)
                            if possible_age:
                                name = guess_name_from_query(query_stripped)
                                return f"{name} is {possible_age} years old."
                    # If wikipedia didn't help, run a focused ddg fallback (search "X birth date")
                    focused = focused_birth_search(query_stripped)
                    if focused:
                        return focused
                    # else continue to general pipeline

                # GENERAL pipeline (snippets + page sentences)
                # try search snippets first (fast)
                results = search_ddg(query_stripped, max_results=MAX_RESULTS)
                vprint("Search results:", len(results))

                # examine snippets for direct age/birthdate if relevant
                for r in results:
                    snippet = r.get("body") or r.get("text") or r.get("snippet") or r.get("description") or ""
                    if snippet:
                        # check birthdate in snippet
                        bd = find_birthdate_in_text(snippet)
                        if bd and re.search(r'\bhow old\b', query_stripped.lower()):
                            age = compute_age(bd)
                            name = guess_name_from_query(query_stripped)
                            monthname = bd.strftime("%B")
                            return f"{name} is {age} years old (born {monthname} {bd.day}, {bd.year})."
                        # check explicit 'years old' in snippet
                        possible_age = extract_age_from_sentence(snippet)
                        if possible_age and re.search(r'\bhow old\b', query_stripped.lower()):
                            name = guess_name_from_query(query_stripped)
                            return f"{name} is {possible_age} years old."

                # if no snippet direct answer: fetch pages and pick best sentence
                for r in results:
                    url = r.get("href") or r.get("url") or r.get("link")
                    if not url:
                        continue
                    vprint("Fetching:", url)
                    text = fetch_text(url)
                    if not text:
                        continue
                    # prioritize sentences with birthdate/years if query is age
                    if re.search(r'\bhow old\b', query_stripped.lower()):
                        bd = find_birthdate_in_text(text)
                        if bd:
                            age = compute_age(bd)
                            name = guess_name_from_query(query_stripped)
                            monthname = bd.strftime("%B")
                            return f"{name} is {age} years old (born {monthname} {bd.day}, {bd.year})."
                        # check sentences for "X years old"
                        s = extract_best_sentence(text, query_stripped)
                        if s:
                            possible_age = extract_age_from_sentence(s)
                            if possible_age:
                                name = guess_name_from_query(query_stripped)
                                return f"{name} is {possible_age} years old."

                    # general extraction for other queries
                    best_sent = extract_best_sentence(text, query_stripped)
                    if best_sent:
                        # avoid returning the query itself as an answer
                        if best_sent.strip().lower().rstrip('?') == query_stripped.lower().rstrip('?'):
                            continue
                        return best_sent

                # Last resort: try Wikipedia general summary (not only for age)
                wiki_text = wikipedia_fallback(query_stripped)
                if wiki_text:
                    # for age queries, try to compute birthdate again
                    if re.search(r'\bhow old\b', query_stripped.lower()):
                        bd = find_birthdate_in_text(wiki_text)
                        if bd:
                            age = compute_age(bd)
                            name = guess_name_from_query(query_stripped)
                            monthname = bd.strftime("%B")
                            return f"{name} is {age} years old (born {monthname} {bd.day}, {bd.year})."
                    # else return a concise wiki sentence
                    s = extract_best_sentence(wiki_text, query_stripped)
                    if s and s.strip().lower().rstrip('?') != query_stripped.lower().rstrip('?'):
                        return s

                return "No concise answer found."

            # ---------- Focused birth search (fallback) ----------
            def focused_birth_search(query):
                """
                For 'how old' queries try searching 'NAME birth date' and parse snippets/pages.
                """
                # try to extract the name from query
                name = guess_name_from_query(query)
                q2 = f"{name} birth date"
                vprint("Focused search query:", q2)
                results = search_ddg(q2, max_results=8)
                for r in results:
                    snippet = r.get("body") or r.get("text") or r.get("snippet") or ""
                    if snippet:
                        bd = find_birthdate_in_text(snippet)
                        if bd:
                            age = compute_age(bd)
                            monthname = bd.strftime("%B")
                            return f"{name} is {age} years old (born {monthname} {bd.day}, {bd.year})."
                for r in results:
                    url = r.get("href") or r.get("url") or r.get("link")
                    if not url:
                        continue
                    text = fetch_text(url)
                    bd = find_birthdate_in_text(text)
                    if bd:
                        age = compute_age(bd)
                        monthname = bd.strftime("%B")
                        return f"{name} is {age} years old (born {monthname} {bd.day}, {bd.year})."
                return ""

            # ---------- Helper: name guess ----------
            def guess_name_from_query(query):
                # crude but effective: take words after 'how old is' or after 'how old'
                q = query.strip()
                m = re.search(r'how old (is|was)\s+(.+)', q, re.I)
                if m:
                    name = m.group(2)
                else:
                    # fallback: take last 2-3 words
                    tokens = re.findall(r'\w+', q)
                    name = " ".join(tokens[-3:])
                # Capitalize tokens nicely
                return " ".join(t.capitalize() for t in re.findall(r'\w+', name))

            # ---------- CLI ----------
            if __name__ == "__main__":
                try:
                    query = input("Enter your question: ").strip()
                except Exception:
                    query = ""
                if not query:
                    print("No query entered.")
                    raise SystemExit(0)

                # temporarily turn on verbose to help debugging; set False if you don't want logs
                VERBOSE = False

                print("Searching and building answer...\n")
                ans = answer_query(query)
                print(ans)
#done with search ----------------------------------------------------------------






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
            


#