import requests
import os
import datetime
import threading
import json
import sys
import pythoncom
import win32com.client
import queue
import re
import speech_recognition as sr
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx
from collections import deque, defaultdict
from datetime import timedelta
import sqlite3
from enum import Enum


# ============================================================================
# CONFIG
# ============================================================================

LLM_URL = 'http://10.0.0.231:1234/v1/chat/completions'
LLM_MODEL = 'qwen/qwen3-4b'
CHAT_MEMORY = "data/chats/jarvis_memory.json"
PERSONALITY = "Pioneer"
Date = str(datetime.date.today())
wake_word = "observer"
Search_Site = "https://interface.ghst.best/ddg?q="

recognizer = sr.Recognizer()
SpeechRecoModel = "base"
WakeWordDetectModel = "tiny"
audio_queue = queue.Queue()
tts_queue = queue.Queue()

temp = 0.7
timeout = 60

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def ping_website(search_url):
    try:
        response = requests.head(search_url, timeout=5)
        return response.status_code < 400
    except requests.RequestException:
        return False

# ============================================================================
# USER PROFILING (Simplified for local LLM)
# ============================================================================

class UserProfile:
    """Track user preferences and behavior"""
    
    def __init__(self):
        self.preferences = defaultdict(lambda: {'score': 0, 'contexts': []})
        self.habits = defaultdict(lambda: {'frequency': 0, 'times': []})
        self.communication_style = {
            'formality': 0.5,
            'verbosity': 0.5,
            'technical_level': 0.5,
            'humor': 0.5
        }
        self.expertise_areas = defaultdict(float)
        self.topic_interests = defaultdict(lambda: {'interactions': 0})
        self.goals = []
        self.interaction_count = 0
    
    def record_interaction(self, user_input, response):
        """Learn from interaction"""
        self.interaction_count += 1
        
        # Track topics mentioned
        words = user_input.lower().split()
        for word in words:
            if len(word) > 4:
                self.topic_interests[word]['interactions'] += 1
        
        # Detect technical content
        technical_words = ['code', 'python', 'api', 'algorithm', 'database', 'server', 'system']
        if any(tech in user_input.lower() for tech in technical_words):
            self.communication_style['technical_level'] = min(1.0, 
                self.communication_style['technical_level'] * 0.9 + 0.15)
        
        # Detect preferences from response feedback (would need user rating)
        self.communication_style['verbosity'] = 0.5  # Neutral for now
    
    def get_adapted_style(self):
        """Get response style tailored to user"""
        style = {}
        
        if self.communication_style['formality'] > 0.7:
            style['tone'] = 'professional'
        elif self.communication_style['formality'] < 0.3:
            style['tone'] = 'casual'
        else:
            style['tone'] = 'friendly'
        
        if self.communication_style['technical_level'] > 0.6:
            style['technical'] = 'advanced'
        elif self.communication_style['technical_level'] < 0.3:
            style['technical'] = 'simplified'
        else:
            style['technical'] = 'balanced'
        
        return style
    
    def to_dict(self):
        return {
            'interaction_count': self.interaction_count,
            'communication_style': self.communication_style,
            'expertise_areas': dict(self.expertise_areas),
            'top_topics': sorted(
                self.topic_interests.items(),
                key=lambda x: x[1]['interactions'],
                reverse=True
            )[:5],
            'goals': self.goals
        }


# ============================================================================
# ATTENTION SYSTEM
# ============================================================================

class AttentionSystem:
    """Track what's important right now"""
    
    def __init__(self, max_items=15):
        self.focused_topics = deque(maxlen=max_items)
        self.salience_scores = defaultdict(float)
        self.context_stack = []
    
    def calculate_salience(self, topic, recency=1.0, frequency=1.0, relevance=1.0):
        """Calculate importance score"""
        salience = (recency * 0.3 + frequency * 0.2 + relevance * 0.5)
        self.salience_scores[topic] = salience
        return salience
    
    def add_focus(self, topic, importance=0.5):
        """Add topic to focus"""
        self.focused_topics.append({
            'topic': topic,
            'importance': importance,
            'timestamp': datetime.datetime.now()
        })
    
    def get_focused(self, limit=3):
        """Get currently focused topics"""
        items = list(self.focused_topics)
        items.sort(key=lambda x: x['importance'], reverse=True)
        return items[:limit]
    
    def push_context(self, context):
        """Push context (for subtopics)"""
        self.context_stack.append(context)
    
    def pop_context(self):
        """Pop context"""
        if self.context_stack:
            return self.context_stack.pop()
    
    def get_context(self):
        """Get current context"""
        return self.context_stack[-1] if self.context_stack else None


# ============================================================================
# VECTOR MEMORY (Semantic Search)
# ============================================================================

class VectorMemory:
    """Find semantically relevant past interactions"""
    
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.vectors = []
        self.memories = []
    
    def add(self, user_input, ai_response):
        """Store interaction"""
        full_text = f"{user_input} {ai_response}"
        vector = self.model.encode(full_text)
        self.vectors.append(vector)
        self.memories.append({
            'user': user_input,
            'ai': ai_response,
            'timestamp': datetime.datetime.now(),
            'access_count': 0
        })
    
    def recall(self, query, top_k=3, threshold=0.3):
        """Find relevant memories"""
        if not self.vectors:
            return []
        
        query_vector = self.model.encode(query)
        vectors_array = np.array(self.vectors)
        similarities = cosine_similarity([query_vector], vectors_array)[0]
        
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = []
        
        for idx in top_indices:
            if similarities[idx] > threshold:
                self.memories[idx]['access_count'] += 1
                results.append({
                    'user': self.memories[idx]['user'],
                    'ai': self.memories[idx]['ai'],
                    'similarity': float(similarities[idx])
                })
        
        return results


# ============================================================================
# KNOWLEDGE GRAPH (Relationships)
# ============================================================================

class KnowledgeGraph:
    """Track entity relationships"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.entities = {}
    
    def add_fact(self, subject, predicate, obj):
        """Add relationship"""
        self.graph.add_edge(subject, obj, relation=predicate)
        
        if subject not in self.entities:
            self.entities[subject] = {'mentions': 0, 'type': 'unknown'}
        if obj not in self.entities:
            self.entities[obj] = {'mentions': 0, 'type': 'unknown'}
        
        self.entities[subject]['mentions'] += 1
        self.entities[obj]['mentions'] += 1
    
    def get_entity_context(self, entity, depth=1):
        """Get facts about entity"""
        context = {'entity': entity, 'facts': []}
        
        try:
            for neighbor in self.graph.neighbors(entity):
                edge_data = self.graph[entity][neighbor]
                context['facts'].append({
                    'subject': entity,
                    'relation': edge_data.get('relation', ''),
                    'object': neighbor
                })
        except:
            pass
        
        return context
    
    def to_dict(self):
        return {
            'nodes': list(self.graph.nodes()),
            'edges': [(u, v, self.graph[u][v]) for u, v in self.graph.edges()],
            'entities': dict(self.entities)
        }


# ============================================================================
# 
# ============================================================================

class LocalInference:
    """Make inferences using local LLM"""
    
    def __init__(self, llm_url, llm_model):
        self.llm_url = llm_url
        self.llm_model = llm_model
    
    def extract_facts(self, text):
        """Extract facts from text using local LLM"""
        prompt = f"""Extract key facts from this text as a JSON list. Return ONLY valid JSON.
Text: {text}

Format: {{"facts": [["subject", "relation", "object"], ...]}}"""
        
        try:
            response = requests.post(self.llm_url, json={
                "model": self.llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200
            }, timeout=30)
            
            response_text = response.json()["choices"][0]["message"]["content"]
            
            # Try to parse JSON
            try:
                result = json.loads(response_text)
                return result.get('facts', [])
            except:
                # Fallback: return empty
                return []
        except:
            return []
    
    def predict_intent(self, user_input, conversation_context):
        """Predict what user wants"""
        context_str = "\n".join([f"{msg['role']}: {msg['content'][:100]}" 
                                 for msg in conversation_context[-3:]])
        
        prompt = f"""Based on this conversation, what is the user asking for? Be brief.

{context_str}
User: {user_input}

Respond with just the intent (e.g., "asking for help with code", "making small talk", etc)"""
        
        try:
            response = requests.post(self.llm_url, json={
                "model": self.llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 50
            }, timeout=30)
            
            return response.json()["choices"][0]["message"]["content"]
        except:
            return "general conversation"


# ============================================================================
#  (Main System)         this shit is so confusing
# ============================================================================

class JarvisVoiceAssistant:
    """Advanced voice assistant with memory and profiling"""
    
    def __init__(self, personality_name="Pioneer"):
        # Load personality
        with open(f"data/Personalities/{personality_name}/{personality_name}.txt", "r") as file:
            self.personality = file.read()
        
        # Initialize conversation history
        self.conversation = [{"role": "system", "content": self.personality}]
        
        # Initialize all memory systems
        self.user_profile = UserProfile()
        self.attention = AttentionSystem()
        self.vector_memory = VectorMemory()
        self.knowledge_graph = KnowledgeGraph()
        self.inference = LocalInference(LLM_URL, LLM_MODEL)
        
        # Settings
        self.llm_url = LLM_URL
        self.llm_model = LLM_MODEL
        self.chat_memory_file = CHAT_MEMORY
        self.conversation_count = 0
        
        # Load saved memory if exists
        self._load_memory()
    
    def _load_memory(self):
        """Load conversation history from disk"""
        if os.path.exists(self.chat_memory_file):
            try:
                with open(self.chat_memory_file, "r") as f:
                    data = json.load(f)
                    self.conversation = data.get('conversation', self.conversation)
                    # Rebuild vector memory from history
                    for msg in self.conversation:
                        if msg['role'] == 'user':
                            idx = self.conversation.index(msg)
                            if idx + 1 < len(self.conversation):
                                next_msg = self.conversation[idx + 1]
                                if next_msg['role'] == 'assistant':
                                    self.vector_memory.add(msg['content'], next_msg['content'])
            except:
                pass
    
    def _save_memory(self):
        """Save memory to disk"""
        os.makedirs(os.path.dirname(self.chat_memory_file), exist_ok=True)
        
        data = {
            'conversation': self.conversation,
            'user_profile': self.user_profile.to_dict(),
            'focused_topics': [t['topic'] for t in self.attention.get_focused()],
            'knowledge_graph': self.knowledge_graph.to_dict(),
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        with open(self.chat_memory_file, "w") as f:
            json.dump(data, f, indent=4)
    
    def _build_system_prompt(self, user_input):
        """Build enhanced system prompt with memory context"""
        # Get relevant memories
        relevant_memories = self.vector_memory.recall(user_input, top_k=3)
        
        # Get focused topics
        focused = self.attention.get_focused(limit=2)
        
        # Get user profile info
        profile = self.user_profile.get_adapted_style()
        
        # Build context string
        context = self.personality
        
        if relevant_memories:
            context += "\n\nRELEVANT PAST INTERACTIONS:"
            for mem in relevant_memories:
                context += f"\nUser: {mem['user'][:80]}"
                context += f"\nYou: {mem['ai'][:80]}"
        
        if focused:
            context += "\n\nCURRENTLY FOCUSED ON:"
            for topic in focused:
                context += f"\n- {topic['topic']}"
        
        context += f"\n\nCOMMUNICATION STYLE:"
        context += f"\n- Tone: {profile.get('tone', 'friendly')}"
        context += f"\n- Technical level: {profile.get('technical', 'balanced')}"
        
        return context
    
    def get_response(self, user_input):
        """Get response with all memory systems engaged"""
        
        # 1. Update user profile
        self.user_profile.record_interaction(user_input, "")
        
        # 2. Extract facts and update knowledge graph
        facts = self.inference.extract_facts(user_input)
        for subject, relation, obj in facts:
            self.knowledge_graph.add_fact(subject, relation, obj)
        
        # 3. Update attention based on topics
        words = user_input.lower().split()
        for word in words:
            if len(word) > 5:
                importance = self.user_profile.topic_interests[word]['interactions'] / 10.0
                self.attention.add_focus(word, min(1.0, importance))
        
        # 4. Build context-aware system prompt
        system_prompt = self._build_system_prompt(user_input)
        
        # 5. Build messages with conversation history
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.conversation[1:])  # Skip original system message
        messages.append({"role": "user", "content": user_input})
        
        # 6. Get response from local LLM
        try:
            response = requests.post(self.llm_url, json={
                "model": self.llm_model,
                "messages": messages,
                "temperature": 0.7,
                "chat_template_kwargs": {"thinking": False}
            }, timeout=60)
            
            response.raise_for_status()
            llm_reply = response.json()["choices"][0]["message"]["content"]
            
            # 7. Store in conversation and memory
            self.conversation.append({"role": "user", "content": user_input})
            self.conversation.append({"role": "assistant", "content": llm_reply})
            self.vector_memory.add(user_input, llm_reply)
            self.user_profile.record_interaction(user_input, llm_reply)
            
            # 8. Save memory
            self.conversation_count += 1
            if self.conversation_count % 3 == 0:  # Save every 3 interactions
                threading.Thread(target=self._save_memory, daemon=True).start()
            
            return llm_reply
        
        except Exception as e:
            error_msg = f"Error getting response: {str(e)}"
            print(error_msg)
            return "I'm having trouble right now. Can you try again?"
    
    def get_profile_summary(self):
        """Get summary of learned user profile"""
        return {
            'interactions': self.user_profile.interaction_count,
            'communication_style': self.user_profile.communication_style,
            'top_topics': dict(sorted(
                self.user_profile.topic_interests.items(),
                key=lambda x: x[1]['interactions'],
                reverse=True
            )[:5]),
            'entities_tracked': len(self.knowledge_graph.entities),
            'focused_topics': [t['topic'] for t in self.attention.get_focused()]
        }


# ============================================================================
# VOICE PROCESSING
# ============================================================================

def transcribe_audio(audio, model="base"):
    """Transcribe audio using Whisper"""
    try:
        return recognizer.recognize_whisper(audio, model=model, language="en").lower()
    except sr.UnknownValueError:
        return None

def listen(source, timeout=5):
    """Listen for audio"""
    try:
        return recognizer.listen(source, timeout=timeout, phrase_time_limit=None)
    except sr.WaitTimeoutError:
        return None

def tts_worker(tts_queue):
    """Text-to-speech worker thread"""
    pythoncom.CoInitialize()
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

def process_command(audio, jarvis):
    """Process voice command through JARVIS"""
    try:
        # Transcribe
        user_input = transcribe_audio(audio, model="base")
        if not user_input:
            print("Could not understand audio")
            return
        
        print(f"You said: {user_input}")
        
        # Get response from JARVIS (with all memory systems)
        response = jarvis.get_response(user_input)
        
        print(f"{PERSONALITY}: {response}")
        
        # Speak response
        tts_queue.put(response)
        
    except Exception as e:
        print(f"Error processing command: {e}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    # Initialize JARVIS
    jarvis = JarvisVoiceAssistant(personality_name=PERSONALITY)
    
    # Start TTS worker
    threading.Thread(target=tts_worker, args=(tts_queue,), daemon=True).start()
    
    # Microphone setup
    with sr.Microphone() as source:
        win32com.client.Dispatch("SAPI.SpVoice").Speak("calibrating")
        print("Calibrating...")
        recognizer.adjust_for_ambient_noise(source, duration=10)
        win32com.client.Dispatch("SAPI.SpVoice").Speak("calibration complete")
        print(f"Calibrated — say '{wake_word}' | Ctrl+C to stop\n")
        
        while True:
            try:
                print("Waiting for wake word...")
                audio = listen(source)
                if audio is None:
                    continue
                
                # Check for wake word
                sst_words = transcribe_audio(audio, model="tiny")
                if not sst_words or wake_word not in sst_words:
                    continue
                
                print("Wake word detected, listening for command...")
                audio = listen(source)
                if audio is None:
                    continue
                
                # Process in background thread
                threading.Thread(
                    target=process_command,
                    args=(audio, jarvis),
                    daemon=True
                ).start()
            
            except sr.UnknownValueError:
                pass
            except KeyboardInterrupt:
                tts_queue.put(None)
                print("\nStopping...")
                # Final save
                jarvis._save_memory()
                print(f"Saved memory. User profile: {jarvis.get_profile_summary()}")
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()