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


class A1ConversationManager:
    def __init__(self):
        self.user_sessions = {}

    def check_answer(self, user_answer, expected_answers):
        user_answer_lower = user_answer.lower().strip()
        for expected in expected_answers:
            if expected.lower() in user_answer_lower:
                return True
        return False

    def get_next_question(self, user_email, user_answer=None):
        # Initialiser la session si nécessaire
        if user_email not in self.user_sessions:
            if not A1_CONVERSATIONS:
                return None

            # Initialiser la session avec la première question
            first_conversation = A1_CONVERSATIONS[0]
            first_exchange = first_conversation.get("exchanges", [])[0]
            first_question = first_exchange.get("question", "")
            expected_answers = first_exchange.get("expected_answers", [])
            example = f"\n\n💬 Example: {expected_answers[0]}" if expected_answers else ""
            intro = f"📚 {first_conversation.get('title', 'A1 Conversation')}\n\n"

            self.user_sessions[user_email] = {
                "current_conversation_index": 0,
                "current_step": 1,
                "current_attempts": 0,
                "conversation_history": [],
                "waiting_for_answer": True,
                "current_question": first_question
            }

            return {
                "reply": f"{intro}{first_question}{example}",
                "conversation_end": False,
                "repeat_question": False,
                "first_question": True
            }

        session_data = self.user_sessions[user_email]

        # Si l'utilisateur envoie un message et qu'on attend sa réponse
        if user_answer is not None:
            if not session_data.get("waiting_for_answer", False):
                current_q = session_data.get("current_question", "Please answer the question.")
                return {
                    "reply": f"👋 {current_q}",
                    "conversation_end": False,
                    "repeat_question": True,
                    "question_to_repeat": current_q
                }

            current_conv_index = session_data["current_conversation_index"]
            current_step = session_data["current_step"]

            if current_conv_index >= len(A1_CONVERSATIONS):
                return {
                    "reply": "🎉 Congratulations! You've completed all A1 conversations! Type 'reset' to start over.",
                    "conversation_end": True,
                    "repeat_question": False
                }

            conversation = A1_CONVERSATIONS[current_conv_index]
            exchanges = conversation.get("exchanges", [])

            question_index = current_step - 1
            if question_index >= len(exchanges):
                session_data["current_conversation_index"] += 1
                session_data["current_step"] = 1
                session_data["current_attempts"] = 0
                session_data["waiting_for_answer"] = True

                if session_data["current_conversation_index"] >= len(A1_CONVERSATIONS):
                    return {
                        "reply": "🎉 Congratulations! You've completed all A1 conversations! Type 'reset' to start over.",
                        "conversation_end": True,
                        "repeat_question": False
                    }

                new_conv = A1_CONVERSATIONS[session_data["current_conversation_index"]]
                new_exchange = new_conv.get("exchanges", [])[0]
                new_question = new_exchange.get("question", "")
                new_expected = new_exchange.get("expected_answers", [])
                new_example = f"\n\n💬 Example: {new_expected[0]}" if new_expected else ""
                new_intro = f"📚 {new_conv.get('title', 'New Conversation')}\n\n"

                session_data["current_question"] = new_question
                session_data["current_question_data"] = new_exchange

                return {
                    "reply": f"✨ Great job! Let's move to a new topic. ✨\n\n{new_intro}{new_question}{new_example}",
                    "conversation_end": False,
                    "repeat_question": False
                }

            current_exchange = exchanges[question_index]
            expected_answers = current_exchange.get("expected_answers", [])
            good_reply = current_exchange.get("good_reply", "Good job! 👍")
            wrong_reply = current_exchange.get("wrong_reply", "Try again!")

            is_correct = self.check_answer(user_answer, expected_answers)

            if not is_correct:
                session_data["current_attempts"] = session_data.get("current_attempts", 0) + 1
                session_data["waiting_for_answer"] = True

                if session_data["current_attempts"] >= 2:
                    hint = f"\n\n💡 Hint: Try saying something like: {expected_answers[0]}"
                    wrong_reply += hint

                return {
                    "reply": wrong_reply,
                    "conversation_end": False,
                    "repeat_question": True,
                    "question_to_repeat": current_exchange.get("question", "")
                }

            session_data["current_attempts"] = 0
            session_data["current_step"] += 1
            session_data["waiting_for_answer"] = True
            current_step = session_data["current_step"]

            if current_step > len(exchanges):
                session_data["current_conversation_index"] += 1
                session_data["current_step"] = 1

                if session_data["current_conversation_index"] >= len(A1_CONVERSATIONS):
                    session_data["waiting_for_answer"] = False
                    return {
                        "reply": f"{good_reply}\n\n🎉 Félicitations! You have completed all A1 conversations! 🎉\n\nType 'reset' to start over.",
                        "conversation_end": True,
                        "repeat_question": False
                    }

                new_conv = A1_CONVERSATIONS[session_data["current_conversation_index"]]
                new_exchange = new_conv.get("exchanges", [])[0]
                new_question = new_exchange.get("question", "")
                new_expected = new_exchange.get("expected_answers", [])
                new_example = f"\n\n💬 Example: {new_expected[0]}" if new_expected else ""
                new_intro = f"📚 {new_conv.get('title', 'New Conversation')}\n\n"

                session_data["current_question"] = new_question
                session_data["current_question_data"] = new_exchange

                return {
                    "reply": f"{good_reply}\n\n✨ Great job! Let's move to a new topic. ✨\n\n{new_intro}{new_question}{new_example}",
                    "conversation_end": False,
                    "repeat_question": False
                }

            next_exchange = exchanges[current_step - 1]
            next_question = next_exchange.get("question", "")
            next_expected = next_exchange.get("expected_answers", [])
            next_example = f"\n\n💬 Example: {next_expected[0]}" if next_expected else ""

            session_data["current_question"] = next_question
            session_data["current_question_data"] = next_exchange

            return {
                "reply": f"{good_reply}\n\n{next_question}{next_example}",
                "conversation_end": False,
                "repeat_question": False
            }

        if session_data.get("waiting_for_answer", False):
            current_q = session_data.get("current_question", "")
            if current_q:
                return {
                    "reply": current_q,
                    "conversation_end": False,
                    "repeat_question": True,
                    "question_to_repeat": current_q
                }

        if A1_CONVERSATIONS:
            conv = A1_CONVERSATIONS[0]
            exch = conv.get("exchanges", [])[0]
            question = exch.get("question", "")
            expected = exch.get("expected_answers", [])
            example = f"\n\n💬 Example: {expected[0]}" if expected else ""

            session_data["current_conversation_index"] = 0
            session_data["current_step"] = 1
            session_data["waiting_for_answer"] = True
            session_data["current_question"] = question
            session_data["current_question_data"] = exch
            session_data["current_attempts"] = 0

            return {
                "reply": f"📚 {conv.get('title', 'A1 Conversation')}\n\n{question}{example}",
                "conversation_end": False,
                "repeat_question": False
            }

        return None

    def reset_user(self, user_email):
        if user_email in self.user_sessions:
            del self.user_sessions[user_email]
        self.get_next_question(user_email)
        return True

    def get_hint(self, user_email):
        if user_email not in self.user_sessions:
            return None

        session_data = self.user_sessions[user_email]
        current_conv_index = session_data["current_conversation_index"]
        current_step = session_data["current_step"]

        if current_conv_index >= len(A1_CONVERSATIONS):
            return "You've completed all conversations! Type 'reset' to start over."

        conversation = A1_CONVERSATIONS[current_conv_index]
        exchanges = conversation.get("exchanges", [])
        question_index = current_step - 1

        if 0 <= question_index < len(exchanges):
            current_exchange = exchanges[question_index]
            expected_answers = current_exchange.get("expected_answers", [])
            if expected_answers:
                return f"💡 Hint for: {current_exchange.get('question', '')}\nTry saying: {expected_answers[0]}"

        return "💡 Hint: Listen carefully and answer simply."

    def get_progress(self, user_email):
        if user_email not in self.user_sessions:
            return None

        session_data = self.user_sessions[user_email]
        total_conversations = len(A1_CONVERSATIONS)
        current_conv = session_data["current_conversation_index"]

        if total_conversations > 0 and current_conv < len(A1_CONVERSATIONS):
            progress_percent = (current_conv / total_conversations) * 100
            current_exchanges = A1_CONVERSATIONS[current_conv].get("exchanges", [])
            return {
                "current_conversation": current_conv + 1,
                "total_conversations": total_conversations,
                "progress_percent": progress_percent,
                "current_step": session_data["current_step"],
                "total_steps_in_current": len(current_exchanges),
                "conversation_title": A1_CONVERSATIONS[current_conv].get("title", "Conversation"),
                "current_attempts": session_data.get("current_attempts", 0)
            }
        return None


# =========================
# 🗣️ INITIALISATION DU GESTIONNAIRE A1
# =========================
a1_manager = A1ConversationManager()


# =========================
# 🤖 OPENROUTER CONFIG
# =========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "meta-llama/llama-3-8b-instruct"


def ask_ai(message, student_level="B1"):
    try:
        level_prompts = {
            "A2": "Use very simple English with short sentences.",
            "B1": "Use intermediate English with natural conversations.",
            "B2": "Use fluent English with rich vocabulary.",
            "C1": "Use advanced fluent English, professional vocabulary, idioms.",
            "C2": "Use expert-level English with sophisticated vocabulary."
        }
        level_instruction = level_prompts.get(student_level, level_prompts["B1"])

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://wec-bec-ai.com",
                "X-OpenRouter-Title": "WEC-BEC English AI"
            },
            data=json.dumps({
                "model": MODEL,
                "messages": [{
                    "role": "system",
                    "content": f"You are WEC-BEC English Teacher AI. The student is at level {student_level}. {level_instruction} Be friendly, patient, and professional. Correct grammar politely. Ask only ONE question at a time."
                }, {"role": "user", "content": message}]
            }),
            timeout=45
        )
        if response.status_code != 200:
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

    # Commandes spéciales pour A1
    if student_level == "A1":
        if message.lower() == "menu":
            progress = a1_manager.get_progress(user_email)
            if progress:
                return jsonify({
                    "reply": f"📊 **Your A1 Progress**:\n📚 {progress['conversation_title']}\nConversation {progress['current_conversation']}/{progress['total_conversations']}\nProgress: {progress['progress_percent']:.1f}%\n\nCommands:\n- 'reset' to start over\n- 'menu' for this menu\n- 'hint' for a hint"
                })
            return jsonify({"reply": "No A1 conversations loaded."})

        if message.lower() == "hint":
            hint = a1_manager.get_hint(user_email)
            return jsonify({"reply": hint or "No hint available."})

        if message.lower() == "reset":
            a1_manager.reset_user(user_email)
            result = a1_manager.get_next_question(user_email, None)
            return jsonify({"reply": result["reply"] if result else "Conversation reset! Type anything to start."})

        # Normal A1 conversation
        result = a1_manager.get_next_question(user_email, message)
        if result:
            return jsonify({"reply": result["reply"]})
        else:
            return jsonify({"reply": "Loading A1 conversations... Please wait."})

    # Autres niveaux : utiliser l'IA
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