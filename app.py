from flask import Flask, request, jsonify, render_template, redirect, session
import requests
import json
import logging
import random
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# =========================
# 🔐 SECURITY CONFIG
# =========================
app.secret_key = os.getenv("SECRET_KEY", "wec-bec-secret-key")
app.permanent_session_lifetime = timedelta(hours=2)

# =========================
# 👤 USERS DATABASE (DEMO)
# =========================
ALLOWED_USERS = {
    "student1@gmail.com": "1234",
    "admin@wec-bec.com": "admin"
}

# =========================
# 📚 STUDENT LEVELS
# =========================
STUDENT_LEVELS = {
    "student1@gmail.com": "A1",
    "admin@wec-bec.com": "C1"
}


# =========================
# 📖 CHARGEMENT DES FICHIERS JSON
# =========================
def load_a1_questions():
    try:
        with open("data/a1_questions.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("conversations", [])
    except FileNotFoundError:
        logging.warning("Fichier a1_questions.json non trouvé")
        return []
    except Exception as e:
        logging.error(f"Erreur chargement A1: {str(e)}")
        return []


def load_courses():
    try:
        with open("data/courses.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("conversations", [])
    except FileNotFoundError:
        logging.warning("Fichier courses.json non trouvé")
        return []
    except Exception as e:
        logging.error(f"Erreur chargement courses: {str(e)}")
        return []


A1_CONVERSATIONS = load_a1_questions()
COURSES_DATA = load_courses()


# =========================
# 🗣️ GESTIONNAIRE DE CONVERSATION A1 (STYLE PROFESSEUR NATUREL)
# =========================
class A1ConversationManager:
    def __init__(self):
        self.user_sessions = {}
        self.all_questions = self.extract_all_questions()
        self.themes = {
            "greetings": ["greet", "hello", "hi", "good morning", "good afternoon", "good evening", "goodbye",
                          "farewell"],
            "personal": ["name", "age", "live", "nationality", "from", "born", "profession", "job"],
            "family": ["family", "brother", "sister", "parents", "position", "eldest", "youngest"],
            "hobbies": ["free time", "hobby", "like", "dislike", "favorite", "weekend", "holiday"],
            "education": ["school", "study", "learn", "english", "center", "university", "level", "grade"],
            "travel": ["travel", "abroad", "country", "visit", "go to"],
            "daily": ["morning", "night", "day", "week", "month", "time", "today", "yesterday"],
            "numbers": ["number", "count", "how much", "phone", "price", "age"],
            "congo": ["congo", "flag", "capital", "currency", "language", "brazzaville"]
        }

    def extract_all_questions(self):
        """Extrait toutes les questions du JSON avec leurs métadonnées"""
        all_questions = []
        for conv in A1_CONVERSATIONS:
            theme = conv.get('title', 'General')
            for exchange in conv.get('exchanges', []):
                all_questions.append({
                    'question': exchange.get('question', ''),
                    'validation_type': exchange.get('validation_type', 'free'),
                    'expected_answers': exchange.get('expected_answers', []),
                    'accepted_topics': exchange.get('accepted_topics', []),
                    'allow_correction': exchange.get('allow_correction', True),
                    'good_reply': exchange.get('good_reply', 'Good job! 👍'),
                    'wrong_reply': exchange.get('wrong_reply', 'Try again.'),
                    'example_answer': exchange.get('example_answer', ''),
                    'theme': theme
                })
        return all_questions

    def get_question_by_theme(self, theme_keyword, exclude_question=None):
        """Retourne une question d'un thème spécifique"""
        theme_topics = self.themes.get(theme_keyword, [])
        available = []
        for q in self.all_questions:
            if q['question'] != exclude_question:
                q_lower = q['question'].lower()
                # Vérifier si la question correspond au thème
                for topic in theme_topics:
                    if topic in q_lower:
                        available.append(q)
                        break
        if available:
            return random.choice(available)
        return self.get_random_question(exclude_question)

    def get_random_question(self, exclude_question=None):
        """Retourne une question aléatoire parmi toutes"""
        available = [q for q in self.all_questions if q['question'] != exclude_question]
        return random.choice(available) if available else random.choice(self.all_questions)

    def check_answer(self, user_answer, expected_answers, validation_type="free", accepted_topics=None):
        """Vérifie si la réponse est correcte"""
        user_answer = user_answer.lower().strip()
        user_answer = user_answer.replace("wèk bèk", "wec bec").replace("wek bek", "wec bec").replace("walk back",
                                                                                                      "wec bec")

        # Réponses absurdes (trop courtes ou sans sens)
        if len(user_answer) < 2 or user_answer in ["a", "b", "c", "d", "yes", "no", "ok"]:
            # On accepte quand même mais on encourage plus
            return True, "short"

        if validation_type == "exact" or validation_type == "translation":
            for expected in expected_answers:
                expected = expected.lower().strip()
                if expected == user_answer or expected in user_answer:
                    return True, "exact"
                words = expected.split()
                if len(words) > 1:
                    matches = sum(1 for word in words if word in user_answer)
                    if matches >= max(1, len(words) // 2):
                        return True, "partial"
            return False, None
        else:
            if not accepted_topics or len(accepted_topics) == 0:
                return True, "free"
            for topic in accepted_topics:
                if topic.lower() in user_answer:
                    return True, "topic_match"
            return False, None

    def detect_question_type(self, user_question):
        """Détecte si l'élève pose une question à l'IA"""
        question_words = ["what", "where", "when", "why", "how", "who", "which", "could you", "can you", "do you"]
        return any(user_question.lower().startswith(qw) for qw in question_words) or user_question.endswith("?")

    def react_to_question(self, user_question):
        """Répond quand l'élève pose une question à l'IA"""
        q_lower = user_question.lower()

        if "how are you" in q_lower or "how are you doing" in q_lower:
            return "I'm doing great, thank you for asking! 😊 How about you?"
        elif "where are you from" in q_lower or "your nationality" in q_lower:
            return "I'm an AI, so I don't have a nationality. But I was created to help you learn English! 🌍"
        elif "how old are you" in q_lower or "your age" in q_lower:
            return "I'm an AI, so I don't age. But I'm here to help you whenever you need! 🎂"
        elif "what is your name" in q_lower:
            return "I'm your WEC-BEC English teacher! You can call me Teacher AI. 📚"
        elif "do you like" in q_lower:
            return "I love helping students learn English! It's my favorite thing to do. 💖"
        elif "can you help me" in q_lower:
            return "Of course! That's why I'm here. What would you like to practice? 🤝"
        else:
            return f"That's a great question! Let me answer: {self.get_helpful_answer(q_lower)}"

    def get_helpful_answer(self, question):
        """Réponse générique pour les questions"""
        if "english" in question:
            return "English is a wonderful language to learn. Practice every day and you'll improve quickly!"
        elif "learn" in question:
            return "The best way to learn is to practice speaking, reading, and listening every day!"
        else:
            return "I'm here to help you practice English. Let's continue our conversation!"

    def is_greeting(self, text):
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "bonjour"]
        text = text.lower().strip()
        return any(greeting in text for greeting in greetings)

    def create_session(self):
        return {
            "current_question": None,
            "current_validation_type": None,
            "current_expected_answers": None,
            "current_accepted_topics": None,
            "current_allow_correction": None,
            "current_good_reply": None,
            "current_wrong_reply": None,
            "current_theme": None,
            "correct_count": 0,
            "wrong_count": 0,
            "total_questions": 0,
            "detected_level": "A1",
            "conversation_history": [],
            "last_question": None
        }

    def reset_user(self, user_email):
        self.user_sessions[user_email] = self.create_session()
        return True

    def start_conversation(self, user_email):
        """Démarre la conversation avec une question simple"""
        if user_email not in self.user_sessions:
            self.user_sessions[user_email] = self.create_session()

        session = self.user_sessions[user_email]

        # Commencer par une question simple sur le nom
        question_data = None
        for q in self.all_questions:
            if "name" in q['question'].lower() and "your name" in q['question'].lower():
                question_data = q
                break

        if not question_data:
            question_data = self.get_question_by_theme("personal")

        session["current_question"] = question_data['question']
        session["current_validation_type"] = question_data['validation_type']
        session["current_expected_answers"] = question_data['expected_answers']
        session["current_accepted_topics"] = question_data['accepted_topics']
        session["current_allow_correction"] = question_data['allow_correction']
        session["current_good_reply"] = question_data['good_reply']
        session["current_wrong_reply"] = question_data['wrong_reply']
        session["last_question"] = question_data['question']

        # Message d'accueil naturel
        welcome = "Hello! Nice to meet you. What's your name? 😊"

        return {
            "reply": welcome,
            "question_data": question_data
        }

    def process_answer(self, user_email, user_answer):
        """Traite la réponse et retourne la réponse de l'IA"""
        if user_email not in self.user_sessions:
            return self.start_conversation(user_email)

        session = self.user_sessions[user_email]

        # Si l'élève pose une question à l'IA
        if self.detect_question_type(user_answer):
            ai_reply = self.react_to_question(user_answer)
            # Garder la même question en attente
            return {
                "reply": ai_reply,
                "question_repeat": session.get("current_question")
            }

        session["total_questions"] += 1

        current_q = session.get("current_question")
        expected = session.get("current_expected_answers", [])
        validation_type = session.get("current_validation_type", "free")
        accepted_topics = session.get("current_accepted_topics", [])
        good_reply = session.get("current_good_reply", "Good job! 👍")
        wrong_reply = session.get("current_wrong_reply", "Try again.")

        # Vérifier la réponse
        is_correct, match_type = self.check_answer(user_answer, expected, validation_type, accepted_topics)

        # Détection de niveau avancé
        advanced_keywords = [
            "present perfect", "past perfect", "conditional", "subjunctive",
            "could you explain", "difference between", "would have", "should have"
        ]
        is_advanced = any(keyword in user_answer.lower() for keyword in advanced_keywords)

        if is_advanced and session["detected_level"] == "A1":
            session["detected_level"] = "A2"
            return {
                "reply": f"Wow! Your English is quite strong. You're asking advanced questions! 👏\n\nLet's continue practicing!",
                "level_up": True
            }

        if is_correct:
            session["correct_count"] += 1

            # Choisir la prochaine question en fonction du thème actuel
            current_theme = self.get_question_theme(current_q)

            # 70% de chance de rester dans le même thème, 30% de changer
            if random.random() < 0.7:
                new_question = self.get_question_by_theme(current_theme, current_q)
            else:
                # Changer de thème
                themes_list = list(self.themes.keys())
                current_theme_index = themes_list.index(current_theme) if current_theme in themes_list else 0
                next_theme = themes_list[(current_theme_index + 1) % len(themes_list)]
                new_question = self.get_question_by_theme(next_theme, current_q)

            if not new_question:
                new_question = self.get_random_question(current_q)

            session["current_question"] = new_question['question']
            session["current_validation_type"] = new_question['validation_type']
            session["current_expected_answers"] = new_question['expected_answers']
            session["current_accepted_topics"] = new_question['accepted_topics']
            session["current_allow_correction"] = new_question['allow_correction']
            session["current_good_reply"] = new_question['good_reply']
            session["current_wrong_reply"] = new_question['wrong_reply']
            session["last_question"] = new_question['question']

            # Réponse naturelle avec transition
            if match_type == "short":
                natural_reply = f"Nice! {new_question['question']}"
            elif "name" in current_q.lower() and user_answer.strip():
                # Extraire le nom pour personnaliser
                name = user_answer.replace("my name is", "").replace("i am", "").strip()
                if len(name) > 0 and len(name) < 30:
                    natural_reply = f"Nice to meet you, {name}! {new_question['question']}"
                else:
                    natural_reply = f"Nice to meet you! {new_question['question']}"
            else:
                natural_reply = f"{good_reply}\n\n{new_question['question']}"

            return {
                "reply": natural_reply,
                "next_question": new_question['question'],
                "correct": True,
                "score": round((session["correct_count"] / session["total_questions"]) * 100, 1) if session[
                                                                                                        "total_questions"] > 0 else 0
            }
        else:
            session["wrong_count"] += 1
            # Ne pas répéter indéfiniment la même question
            if session["wrong_count"] >= 2:
                # Passer à une question plus simple
                easier_question = self.get_question_by_theme("greetings", current_q)
                if easier_question:
                    session["current_question"] = easier_question['question']
                    session["current_expected_answers"] = easier_question['expected_answers']
                    session["current_accepted_topics"] = easier_question['accepted_topics']
                    session["wrong_count"] = 0
                    return {
                        "reply": f"Let's try an easier question. {easier_question['question']}",
                        "correct": False
                    }

            if expected:
                hint = f" Try saying: '{expected[0]}'"
                return {
                    "reply": f"{wrong_reply}{hint}\n\n{current_q}",
                    "repeat_question": True,
                    "correct": False
                }
            return {
                "reply": f"{wrong_reply}\n\n{current_q}",
                "repeat_question": True,
                "correct": False
            }

    def get_question_theme(self, question):
        """Détermine le thème d'une question"""
        q_lower = question.lower()
        for theme, keywords in self.themes.items():
            for keyword in keywords:
                if keyword in q_lower:
                    return theme
        return "personal"

    def get_hint(self, user_email):
        if user_email not in self.user_sessions:
            return "Say 'hi' to start a conversation!"
        session = self.user_sessions[user_email]
        expected = session.get("current_expected_answers", [])
        if expected:
            return f"💡 Hint: Try saying: {expected[0]}"
        return "💡 Hint: Answer naturally in English."

    def get_progress(self, user_email):
        if user_email not in self.user_sessions:
            return None
        session = self.user_sessions[user_email]
        total = session["total_questions"]
        correct = session["correct_count"]
        score = (correct / total * 100) if total > 0 else 0
        return {
            "total_questions": total,
            "correct_answers": correct,
            "wrong_answers": session["wrong_count"],
            "score": round(score, 1),
            "level": session["detected_level"]
        }


a1_manager = A1ConversationManager()

# =========================
# 🤖 OPENROUTER CONFIG
# =========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "meta-llama/llama-3-8b-instruct"


def ask_ai(message, student_level="B1"):
    try:
        level_prompts = {
            "A1": "Use very simple English with short sentences and basic vocabulary.",
            "A2": "Use simple English with short sentences.",
            "B1": "Use intermediate English with natural conversations.",
            "B2": "Use fluent English with rich vocabulary.",
            "C1": "Use advanced fluent English, professional vocabulary, idioms.",
            "C2": "Use expert-level English with sophisticated vocabulary."
        }
        level_instruction = level_prompts.get(student_level, level_prompts["B1"])

        system_prompt = (
            f"You are WEC-BEC English Teacher AI. The student is at level {student_level}. {level_instruction} "
            "Be friendly, patient, and professional. Correct grammar politely. Ask only ONE question at a time.\n\n"
            "IMPORTANT: Behave like a real human teacher. If the student asks you a question, answer it naturally.\n"
            "Never display 'Lesson X:' or 'Example:'. Just have a natural conversation.\n"
            "Respond to what the student says before asking the next question.\n"
            "If the student says 'and you?', answer the question yourself.\n"
            "Keep the conversation flowing naturally, like a real dialogue.\n"
            "The name WEC-BEC is pronounced 'wèk bèk' by YOU, the teacher.\n"
        )

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://wec-bec-ai.com",
                "X-OpenRouter-Title": "WEC-BEC English AI"
            },
            data=json.dumps({
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
            }),
            timeout=45
        )
        if response.status_code != 200:
            logging.error(f"AI service error: {response.status_code}")
            return "AI service error. Try again later."
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"AI exception: {str(e)}")
        return "AI connection error."


# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
def home():
    if not session.get("user"):
        return redirect("/login")
    return render_template("index.html", user=session["user"], student_level=STUDENT_LEVELS.get(session["user"], "B1"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect("/")
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        if email in ALLOWED_USERS and ALLOWED_USERS[email] == password:
            session.permanent = True
            session["user"] = email
            return redirect("/")
        return render_template("login.html", error="Invalid email or password ❌")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/chat", methods=["POST"])
def chat():
    if not session.get("user"):
        return jsonify({"reply": "Not authorized"}), 403

    data = request.json or {}
    message = data.get("message", "").strip()
    user_email = session["user"]
    student_level = STUDENT_LEVELS.get(user_email, "B1")

    if student_level == "A1":
        if message.lower() == "menu":
            progress = a1_manager.get_progress(user_email)
            if progress and progress["total_questions"] > 0:
                return jsonify({
                    "reply": f"📊 **Your Progress**:\n"
                             f"Questions answered: {progress['total_questions']}\n"
                             f"✅ Correct: {progress['correct_answers']}\n"
                             f"❌ Wrong: {progress['wrong_answers']}\n"
                             f"Score: {progress['score']}%\n"
                             f"Level: {progress['level']}\n\n"
                             f"Commands:\n- 'reset' to start over\n- 'menu' for this menu\n- 'hint' for a hint"
                })
            return jsonify({"reply": "Say 'hi' to start a conversation!"})

        if message.lower() == "hint":
            hint = a1_manager.get_hint(user_email)
            return jsonify({"reply": hint})

        if message.lower() == "reset":
            a1_manager.reset_user(user_email)
            return jsonify({"reply": "🔄 Conversation restarted. Say 'hi' to begin!"})

        if a1_manager.is_greeting(message) or user_email not in a1_manager.user_sessions:
            result = a1_manager.start_conversation(user_email)
            return jsonify({"reply": result["reply"]})

        result = a1_manager.process_answer(user_email, message)
        return jsonify({"reply": result.get("reply", "Let's continue our conversation!")})

    reply = ask_ai(message, student_level)
    return jsonify({"reply": reply})


@app.route("/courses")
def get_courses():
    return jsonify({"conversations": COURSES_DATA})


@app.route("/admin/reload-courses", methods=["POST"])
def reload_courses():
    global COURSES_DATA
    COURSES_DATA = load_courses()
    return jsonify({"status": "success", "courses_loaded": len(COURSES_DATA)})


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)