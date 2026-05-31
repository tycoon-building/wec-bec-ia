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
# 🗣️ GESTIONNAIRE DE CONVERSATION A1 (STYLE PROFESSEUR)
# =========================
class A1ConversationManager:
    def __init__(self):
        self.user_sessions = {}
        self.all_questions = self.extract_all_questions()

    def extract_all_questions(self):
        """Extrait toutes les questions du JSON avec leurs métadonnées"""
        all_questions = []
        for conv in A1_CONVERSATIONS:
            title = conv.get('title', 'Lesson')
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
                    'title': title
                })
        return all_questions

    def get_random_question(self, exclude_question=None):
        """Retourne une question aléatoire parmi toutes"""
        available = [q for q in self.all_questions if q['question'] != exclude_question]
        return random.choice(available) if available else random.choice(self.all_questions)

    def check_answer(self, user_answer, expected_answers, validation_type="free", accepted_topics=None):
        """Vérifie si la réponse est correcte"""
        user_answer = user_answer.lower().strip()
        user_answer = user_answer.replace("wèk bèk", "wec bec").replace("wek bek", "wec bec").replace("walk back", "wec bec")

        if validation_type == "exact" or validation_type == "translation":
            for expected in expected_answers:
                expected = expected.lower().strip()
                if expected == user_answer:
                    return True
                if expected in user_answer:
                    return True
                words = expected.split()
                if len(words) > 1:
                    matches = sum(1 for word in words if word in user_answer)
                    if matches >= max(1, len(words) // 2):
                        return True
            return False
        else:
            if not accepted_topics or len(accepted_topics) == 0:
                return True
            for topic in accepted_topics:
                if topic.lower() in user_answer:
                    return True
            return False

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
            "correct_count": 0,
            "wrong_count": 0,
            "total_questions": 0,
            "detected_level": "A1"
        }

    def reset_user(self, user_email):
        self.user_sessions[user_email] = self.create_session()
        return True

    def start_conversation(self, user_email):
        """Démarre la conversation avec une question aléatoire"""
        if user_email not in self.user_sessions:
            self.user_sessions[user_email] = self.create_session()

        session = self.user_sessions[user_email]
        question_data = self.get_random_question()

        session["current_question"] = question_data['question']
        session["current_validation_type"] = question_data['validation_type']
        session["current_expected_answers"] = question_data['expected_answers']
        session["current_accepted_topics"] = question_data['accepted_topics']
        session["current_allow_correction"] = question_data['allow_correction']
        session["current_good_reply"] = question_data['good_reply']
        session["current_wrong_reply"] = question_data['wrong_reply']

        return {
            "reply": question_data['question'],
            "question_data": question_data
        }

    def process_answer(self, user_email, user_answer):
        """Traite la réponse et retourne la prochaine question"""
        if user_email not in self.user_sessions:
            return self.start_conversation(user_email)

        session = self.user_sessions[user_email]
        session["total_questions"] += 1

        current_q = session.get("current_question")
        expected = session.get("current_expected_answers", [])
        validation_type = session.get("current_validation_type", "free")
        accepted_topics = session.get("current_accepted_topics", [])
        allow_correction = session.get("current_allow_correction", True)
        good_reply = session.get("current_good_reply", "Good job! 👍")
        wrong_reply = session.get("current_wrong_reply", "Try again.")

        # Vérifier si l'élève a un niveau avancé
        advanced_keywords = [
            "present perfect", "past perfect", "conditional", "subjunctive",
            "could you explain", "difference between", "would have", "should have",
            "passive voice", "relative clause", "phrasal verb", "idiom"
        ]
        is_advanced = any(keyword in user_answer.lower() for keyword in advanced_keywords)

        if is_advanced and session["detected_level"] == "A1":
            session["detected_level"] = "A2"
            return {
                "reply": f"Very good question! Your English seems quite strong.\n\nYou're ready for A2 level! Let's continue.",
                "level_up": True,
                "new_level": "A2"
            }

        is_correct = self.check_answer(user_answer, expected, validation_type, accepted_topics)

        if is_correct:
            session["correct_count"] += 1
            # Choisir une nouvelle question aléatoire
            new_question = self.get_random_question(current_q)
            session["current_question"] = new_question['question']
            session["current_validation_type"] = new_question['validation_type']
            session["current_expected_answers"] = new_question['expected_answers']
            session["current_accepted_topics"] = new_question['accepted_topics']
            session["current_allow_correction"] = new_question['allow_correction']
            session["current_good_reply"] = new_question['good_reply']
            session["current_wrong_reply"] = new_question['wrong_reply']

            score = (session["correct_count"] / session["total_questions"]) * 100 if session["total_questions"] > 0 else 0

            # Si score élevé, féliciter
            if score > 80 and session["total_questions"] >= 5:
                return {
                    "reply": f"{good_reply}\n\n{new_question['question']}",
                    "next_question": new_question['question'],
                    "correct": True,
                    "score": round(score, 1)
                }
            else:
                return {
                    "reply": f"{good_reply}\n\n{new_question['question']}",
                    "next_question": new_question['question'],
                    "correct": True
                }
        else:
            session["wrong_count"] += 1
            if allow_correction and expected:
                return {
                    "reply": f"{wrong_reply}\n\n{current_q}",
                    "repeat_question": True,
                    "correct": False
                }
            return {
                "reply": f"{wrong_reply}\n\n{current_q}",
                "repeat_question": True,
                "correct": False
            }

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
            "IMPORTANT: Do NOT show lesson titles or example answers. Just speak naturally like a real teacher.\n"
            "If the student asks a question above their level, answer it and suggest moving to a higher level.\n"
            "Never display 'Expected answer' or 'Example'. Just have a natural conversation.\n"
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
            if progress:
                return jsonify({
                    "reply": f"📊 **Your Progress**:\n"
                             f"Questions answered: {progress['total_questions']}\n"
                             f"✅ Correct: {progress['correct_answers']}\n"
                             f"❌ Wrong: {progress['wrong_answers']}\n"
                             f"Score: {progress['score']}%\n"
                             f"Current level: {progress['level']}\n\n"
                             f"Commands:\n- 'reset' to start over\n- 'menu' for this menu\n- 'hint' for a hint"
                })
            return jsonify({"reply": "Say 'hi' to start a conversation!"})

        if message.lower() == "hint":
            hint = a1_manager.get_hint(user_email)
            return jsonify({"reply": hint})

        if message.lower() == "reset":
            a1_manager.reset_user(user_email)
            return jsonify({"reply": "🔄 Conversation restarted. Say 'hi' to begin!"})

        # Si l'utilisateur dit bonjour ou première fois
        if a1_manager.is_greeting(message) or user_email not in a1_manager.user_sessions:
            result = a1_manager.start_conversation(user_email)
            return jsonify({"reply": result["reply"]})

        # Traitement normal de la réponse
        result = a1_manager.process_answer(user_email, message)
        return jsonify({"reply": result.get("reply", "Let's continue our conversation!")})

    # Autres niveaux : utiliser l'IA
    reply = ask_ai(message, student_level)
    return jsonify({"reply": reply})


@app.route("/courses")
def get_courses():
    return jsonify({"conversations": COURSES_DATA})


@app.route("/admin/reload-courses", methods=["POST"])
def reload_courses():
    global COURSES_DATA
    COURS_DATA = load_courses()
    return jsonify({"status": "success", "courses_loaded": len(COURSES_DATA)})


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)