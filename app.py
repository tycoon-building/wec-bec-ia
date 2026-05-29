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

# session expire après 2 heures
app.permanent_session_lifetime = timedelta(hours=2)

# =========================
# 👤 USERS DATABASE (DEMO)
# =========================
ALLOWED_USERS = {
    "student1@gmail.com": "1234",
    "admin@wec-bec.com": "admin"
}

# =========================
# 📚 STUDENT LEVELS (DEMO - À CONNECTER À VOTRE DB)
# =========================
STUDENT_LEVELS = {
    "student1@gmail.com": "A1",
    "admin@wec-bec.com": "C1"
}


# =========================
# 📖 CHARGEMENT DU FICHIER JSON POUR A1
# =========================
def load_a1_questions():
    """Charge les questions/réponses pour le niveau A1 depuis un fichier JSON"""
    try:
        with open("data/a1_questions.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("conversations", [])
    except FileNotFoundError:
        logging.warning("Fichier a1_questions.json non trouvé, utilisation du mode IA par défaut")
        return []
    except Exception as e:
        logging.error(f"Erreur lors du chargement du JSON A1: {str(e)}")
        return []


# =========================
# 📖 CHARGEMENT DU FICHIER COURSES.JSON
# =========================
def load_courses():
    """Charge les cours depuis courses.json"""
    try:
        with open("data/courses.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("conversations", [])
    except FileNotFoundError:
        logging.warning("Fichier courses.json non trouvé")
        return []
    except Exception as e:
        logging.error(f"Erreur lors du chargement du JSON courses: {str(e)}")
        return []


# Chargement des données au démarrage
A1_CONVERSATIONS = load_a1_questions()
COURSES_DATA = load_courses()


# =========================
# 🗣️ GESTIONNAIRE DE CONVERSATION A1 (VERSION AMÉLIORÉE)
# =========================
class A1ConversationManager:
    def __init__(self):
        self.user_sessions = {}

    def check_answer(self, user_answer, expected_answers):
        """Vérifie si la réponse de l'utilisateur correspond aux réponses attendues"""
        user_answer_lower = user_answer.lower().strip()

        for expected in expected_answers:
            if expected.lower() in user_answer_lower:
                return True
        return False

    def get_next_question(self, user_email, user_answer=None):
        """Récupère la prochaine question ou réponse basée sur l'état de l'utilisateur"""

        if user_email not in self.user_sessions:
            if A1_CONVERSATIONS:
                self.user_sessions[user_email] = {
                    "current_conversation_index": 0,
                    "current_step": 0,
                    "current_attempts": 0,
                    "conversation_history": []
                }
            else:
                return None

        session_data = self.user_sessions[user_email]
        current_conv_index = session_data["current_conversation_index"]
        current_step = session_data["current_step"]
        current_attempts = session_data.get("current_attempts", 0)

        if current_conv_index >= len(A1_CONVERSATIONS):
            current_conv_index = 0
            session_data["current_conversation_index"] = 0
            session_data["conversation_history"] = []
            current_step = 0
            session_data["current_step"] = 0
            current_attempts = 0
            session_data["current_attempts"] = 0

        conversation = A1_CONVERSATIONS[current_conv_index]
        exchanges = conversation.get("exchanges", [])

        if user_answer is not None and current_step > 0:
            previous_exchange = exchanges[current_step - 1]
            expected_answers = previous_exchange.get("expected_answers", [])
            good_reply = previous_exchange.get("good_reply", "Good job! 👍")
            wrong_reply = previous_exchange.get("wrong_reply", "Try again!")

            is_correct = self.check_answer(user_answer, expected_answers)

            session_data["conversation_history"].append({
                "question": previous_exchange.get("question", ""),
                "user_answer": user_answer,
                "expected_answers": expected_answers,
                "is_correct": is_correct,
                "attempts": current_attempts + 1
            })

            if not is_correct:
                session_data["current_attempts"] = current_attempts + 1

                if current_attempts >= 2:
                    hint = f"\n\n💡 Petit conseil: Essayez de dire: {expected_answers[0]}..."
                    wrong_reply += hint

                return {
                    "reply": wrong_reply,
                    "conversation_end": False,
                    "repeat_question": True,
                    "question_to_repeat": previous_exchange.get("question", "")
                }

            session_data["current_attempts"] = 0
            current_step += 1
            session_data["current_step"] = current_step

            if current_step > len(exchanges):
                session_data["current_conversation_index"] += 1
                session_data["current_step"] = 0
                session_data["current_attempts"] = 0
                session_data["conversation_history"] = []

                if session_data["current_conversation_index"] < len(A1_CONVERSATIONS):
                    next_conv = A1_CONVERSATIONS[session_data["current_conversation_index"]]
                    next_question = next_conv.get("exchanges", [])[0].get("question", "")
                    next_title = next_conv.get('title', 'Nouvelle conversation')
                    return {
                        "reply": f"{good_reply}\n\n✨ Bien joué ! Passons à un nouveau sujet. ✨\n\n📚 {next_title}\n{next_question}",
                        "conversation_end": False,
                        "repeat_question": False
                    }
                else:
                    return {
                        "reply": f"{good_reply}\n\n🎉 Félicitations ! Vous avez terminé toutes les conversations pour le niveau A1 ! 🎉\n\nTapez 'menu' pour voir vos options.",
                        "conversation_end": True,
                        "repeat_question": False
                    }
            else:
                next_exchange = exchanges[current_step - 1]
                next_question = next_exchange.get("question", "")
                return {
                    "reply": f"{good_reply}\n\n{next_question}",
                    "conversation_end": False,
                    "repeat_question": False
                }

        if current_step < len(exchanges):
            current_exchange = exchanges[current_step]
            question = current_exchange.get("question", "")
            expected_answers = current_exchange.get("expected_answers", [])

            if current_step == 0:
                intro = f"📚 {conversation.get('title', 'Conversation A1')}\n\n"
                if expected_answers:
                    example = f"\n\n💬 Exemple: {expected_answers[0]}"
                    return {
                        "reply": intro + question + example,
                        "conversation_end": False,
                        "repeat_question": False
                    }
                return {
                    "reply": intro + question,
                    "conversation_end": False,
                    "repeat_question": False
                }
            else:
                if current_attempts == 0 and expected_answers:
                    example = f"\n\n💬 Exemple: {expected_answers[0]}"
                    return {
                        "reply": question + example,
                        "conversation_end": False,
                        "repeat_question": False
                    }
                return {
                    "reply": question,
                    "conversation_end": False,
                    "repeat_question": False
                }

        return None

    def reset_user(self, user_email):
        if user_email in self.user_sessions:
            self.user_sessions[user_email] = {
                "current_conversation_index": 0,
                "current_step": 0,
                "current_attempts": 0,
                "conversation_history": []
            }
            return True
        return False

    def get_hint(self, user_email):
        if user_email not in self.user_sessions:
            return None

        session_data = self.user_sessions[user_email]
        current_conv_index = session_data["current_conversation_index"]
        current_step = session_data["current_step"]

        if current_conv_index >= len(A1_CONVERSATIONS):
            return None

        conversation = A1_CONVERSATIONS[current_conv_index]
        exchanges = conversation.get("exchanges", [])

        if current_step < len(exchanges):
            current_exchange = exchanges[current_step]
            expected_answers = current_exchange.get("expected_answers", [])
            if expected_answers:
                return f"💡 Indice: Essayez de dire quelque chose comme: {expected_answers[0]}"

        return "💡 Indice: Relisez la question et essayez de répondre simplement."

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


a1_manager = A1ConversationManager()


# =========================
# 🤖 OPENROUTER CONFIG
# =========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "meta-llama/llama-3-8b-instruct"


# =========================
# 📊 LOGGING
# =========================
logging.basicConfig(level=logging.INFO)


# =========================
# 🧠 AI FUNCTION
# =========================
def ask_ai(message, student_level="B1"):
    try:
        level_prompts = {
            "A2": "Use very simple English with short sentences. Focus on basic grammar and common phrases.",
            "B1": "Use intermediate English with natural conversations and moderate vocabulary.",
            "B2": "Use fluent English with rich vocabulary and detailed explanations.",
            "C1": "Use advanced fluent English, professional vocabulary, idioms, and nuanced expressions.",
            "C2": "Use expert-level English with sophisticated vocabulary and native-like fluency."
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
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are WEC-BEC English Teacher AI. "
                            "WEC-BEC means World English Club and Basic English Center. "
                            "You were created by Mister Tycoon. "
                            "You are a smart, friendly, patient, and professional female English teacher. "
                            f"The student is at level {student_level}. {level_instruction} "
                            "Keep conversations natural, warm, human, and engaging. "
                            "Do not sound robotic. "
                            "Speak like a real modern English teacher. "
                            "Correct grammar politely and naturally without discouraging the student. "
                            "Encourage the student often. "
                            "Ask only ONE short question at a time. "
                            "Do not repeat the same question many times. "
                            "Avoid repetitive greetings like 'How are you today?'."
                            "Change topics naturally during the conversation. "
                            "If the student answers correctly, ask a DIFFERENT follow-up question. "
                            "If the student makes mistakes, gently correct them and continue the conversation naturally. "
                            "For beginner students, keep answers short and easy to understand. "
                            "For advanced students, use more detailed and intelligent conversations."
                        )
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ]
            }),
            timeout=45
        )

        if response.status_code != 200:
            logging.error(f"OpenRouter error: {response.text}")
            return "AI service error. Try again later."

        data = response.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        logging.error(f"AI exception: {str(e)}")
        return "AI connection error."


# =========================
# 🌐 HOME
# =========================
@app.route("/")
def home():
    if not session.get("user"):
        return redirect("/login")

    user_email = session["user"]
    student_level = STUDENT_LEVELS.get(user_email, "B1")
    is_a1 = (student_level == "A1")

    return render_template(
        "index.html",
        user=session["user"],
        student_level=student_level,
        is_a1=is_a1
    )


# =========================
# 🔐 LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect("/")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        logging.info(f"Login attempt: {email}")

        if email in ALLOWED_USERS and ALLOWED_USERS[email] == password:
            session.permanent = True
            session["user"] = email
            logging.info(f"Login success: {email}")
            return redirect("/")

        return render_template(
            "login.html",
            error="Invalid email or password ❌"
        )

    return render_template("login.html")


# =========================
# 🚪 LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# 💬 CHAT API
# =========================
@app.route("/chat", methods=["POST"])
def chat():
    if not session.get("user"):
        return jsonify({"reply": "Not authorized"}), 403

    data = request.json or {}
    message = data.get("message", "").strip()
    reset = data.get("reset", False)

    if not message and not reset:
        return jsonify({"reply": "Empty message"}), 400

    user_email = session["user"]
    student_level = STUDENT_LEVELS.get(user_email, "B1")

    if message.lower() == "menu" and student_level == "A1":
        progress = a1_manager.get_progress(user_email)
        if progress:
            menu_text = (
                f"📊 **Your A1 Progress**:\n"
                f"📚 {progress['conversation_title']}\n"
                f"Conversation {progress['current_conversation']}/{progress['total_conversations']}\n"
                f"Question {progress['current_step'] + 1}/{progress['total_steps_in_current']}\n"
                f"Total progress: {progress['progress_percent']:.1f}%\n"
                f"Attempts on current question: {progress['current_attempts']}\n\n"
                f"Commands:\n"
                f"- Type 'reset' to start over\n"
                f"- Type 'menu' to see this menu\n"
                f"- Type 'hint' to get a hint\n"
                f"- Answer normally to continue\n\n"
                f"Continue or reset?"
            )
            return jsonify({"reply": menu_text})
        else:
            return jsonify({"reply": "No A1 conversations loaded. Check JSON file."})

    if message.lower() == "hint" and student_level == "A1":
        hint = a1_manager.get_hint(user_email)
        if hint:
            return jsonify({"reply": hint})
        else:
            return jsonify({"reply": "No hint available at the moment."})

    if message.lower() == "reset" and student_level == "A1":
        if a1_manager.reset_user(user_email):
            first_question = A1_CONVERSATIONS[0].get("exchanges", [{}])[0].get("question", "Introduce yourself.")
            expected = A1_CONVERSATIONS[0].get("exchanges", [{}])[0].get("expected_answers", [])
            example = f"\n\n💬 Example: {expected[0]}" if expected else ""
            return jsonify({
                "reply": f"🔄 Conversation reset! Let's start over.\n\n📚 {A1_CONVERSATIONS[0].get('title', 'A1 Conversation')}\n\n{first_question}{example}"
            })
        else:
            return jsonify({"reply": "Cannot reset. Please try again."})

    if student_level == "A1":
        if reset:
            a1_manager.reset_user(user_email)

        result = a1_manager.get_next_question(user_email, message if not reset else None)

        if result is None:
            reply = ask_ai(message, "A1")
        else:
            reply = result["reply"]

        return jsonify({"reply": reply})

    else:
        reply = ask_ai(message, student_level)
        return jsonify({"reply": reply})


# =========================
# 📊 API PROGRESSION A1
# =========================
@app.route("/a1/progress", methods=["GET"])
def get_a1_progress():
    if not session.get("user"):
        return jsonify({"error": "Not authorized"}), 403

    user_email = session["user"]
    student_level = STUDENT_LEVELS.get(user_email, "B1")

    if student_level != "A1":
        return jsonify({"error": "Reserved for A1 students"}), 400

    progress = a1_manager.get_progress(user_email)
    if progress:
        return jsonify(progress)
    else:
        return jsonify({"error": "No progress found"}), 404


# =========================
# 📚 ROUTE POUR COURSES.JSON
# =========================
@app.route("/courses")
def get_courses():
    """Retourne les données du fichier courses.json"""
    global COURSES_DATA
    # Recharger pour être sûr d'avoir les dernières données
    COURSES_DATA = load_courses()
    return jsonify({"conversations": COURSES_DATA})


# =========================
# 🔄 ROUTE POUR RELOAD COURSES (ADMIN)
# =========================
@app.route("/admin/reload-courses", methods=["POST"])
def reload_courses():
    if not session.get("user") or session["user"] != "admin@wec-bec.com":
        return jsonify({"error": "Admin only"}), 403

    global COURSES_DATA
    COURSES_DATA = load_courses()
    return jsonify({
        "status": "success",
        "courses_loaded": len(COURSES_DATA)
    })


# =========================
# 🔄 ROUTE POUR RELOAD A1 (ADMIN)
# =========================
@app.route("/admin/reload-a1", methods=["POST"])
def reload_a1():
    if not session.get("user") or session["user"] != "admin@wec-bec.com":
        return jsonify({"error": "Admin only"}), 403

    global A1_CONVERSATIONS
    A1_CONVERSATIONS = load_a1_questions()

    return jsonify({
        "status": "success",
        "conversations_loaded": len(A1_CONVERSATIONS)
    })


# =========================
# 🚀 RUN SERVER
# =========================
if __name__ == "__main__":
    app.run(
        debug=False,
        host="0.0.0.0",
        port=5000
    )