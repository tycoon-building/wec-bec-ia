from flask import Flask, request, jsonify, render_template, redirect, session
import requests
import json
import logging
import random
import os
from datetime import timedelta
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)

# =========================
# 🔐 CORS CONFIGURATION
# =========================
CORS(app)

# =========================
# 🔐 SECURITY CONFIG
# =========================
app.secret_key = os.getenv("SECRET_KEY", "wec-bec-secret-key")
app.permanent_session_lifetime = timedelta(hours=2)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# =========================
# 👤 USERS DATABASE
# =========================
ALLOWED_USERS = {
    "admin@wec-bec.com": "admin",
    "apprenant1@gmail.com": "WBcA1Start01",
    "apprenant2@gmail.com": "WBcA1Start02",
    "apprenant3@gmail.com": "WBcA1Start03",
    "apprenant4@gmail.com": "WBcA1Start04",
    "apprenant5@gmail.com": "WBcA1Start05",
    "apprenant6@gmail.com": "WBcA1Start06",
    "apprenant7@gmail.com": "WBcA1Start07",
    "apprenant8@gmail.com": "WBcA1Start08",
    "apprenant9@gmail.com": "WBcA1Start09",
    "apprenant10@gmail.com": "WBcA1Start10",
    "apprenant11@gmail.com": "WBcA1Start11",
    "apprenant12@gmail.com": "WBcA1Start12",
    "apprenant13@gmail.com": "WBcA1Start13",
    "apprenant14@gmail.com": "WBcA1Start14",
    "apprenant15@gmail.com": "WBcA1Start15",
    "apprenant16@gmail.com": "WBcA1Start16",
    "apprenant17@gmail.com": "WBcA1Start17",
    "apprenant18@gmail.com": "WBcA1Start18",
    "apprenant19@gmail.com": "WBcA1Start19",
    "apprenant20@gmail.com": "WBcA1Start20",
    "apprenant21@gmail.com": "WBcA1Start21",
    "apprenant22@gmail.com": "WBcA1Start22",
    "apprenant23@gmail.com": "WBcA1Start23",
    "apprenant24@gmail.com": "WBcA1Start24",
    "apprenant25@gmail.com": "WBcA1Start25",
    "apprenant26@gmail.com": "WBcA1Start26",
    "apprenant27@gmail.com": "WBcA1Start27",
    "apprenant28@gmail.com": "WBcA1Start28",
    "apprenant29@gmail.com": "WBcA1Start29",
    "apprenant30@gmail.com": "WBcA1Start30",
    "tycoon@wec-bec.com": "Tycoon#Speak2026",
    "shooter@wec-bec.com": "Shooter#Learn2026",
    "mefia@wec-bec.com": "Mefia#English2026"
}

STUDENT_LEVELS = {
    "admin@wec-bec.com": "C1",
    "apprenant1@gmail.com": "A1",
    "apprenant2@gmail.com": "A1",
    "apprenant3@gmail.com": "A1",
    "apprenant4@gmail.com": "A1",
    "apprenant5@gmail.com": "A1",
    "apprenant6@gmail.com": "A1",
    "apprenant7@gmail.com": "A1",
    "apprenant8@gmail.com": "A1",
    "apprenant9@gmail.com": "A1",
    "apprenant10@gmail.com": "A1",
    "apprenant11@gmail.com": "A1",
    "apprenant12@gmail.com": "A1",
    "apprenant13@gmail.com": "A1",
    "apprenant14@gmail.com": "A1",
    "apprenant15@gmail.com": "A1",
    "apprenant16@gmail.com": "A1",
    "apprenant17@gmail.com": "A1",
    "apprenant18@gmail.com": "B1",
    "apprenant19@gmail.com": "B1",
    "apprenant20@gmail.com": "B2",
    "apprenant21@gmail.com": "B2",
    "apprenant22@gmail.com": "B2",
    "apprenant23@gmail.com": "A2",
    "apprenant24@gmail.com": "A2",
    "apprenant25@gmail.com": "A2",
    "apprenant26@gmail.com": "C1",
    "apprenant27@gmail.com": "C1",
    "apprenant28@gmail.com": "C2",
    "apprenant29@gmail.com": "C2",
    "apprenant30@gmail.com": "C2",
    "tycoon@wec-bec.com": "A2",
    "shooter@wec-bec.com": "B1",
    "mefia@wec-bec.com": "A2"
}


# =========================
# 📖 CHARGEMENT DES DONNÉES
# =========================
def load_a1_questions():
    try:
        with open("data/a1_questions.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("conversations", [])
    except:
        return []


def load_courses():
    try:
        with open("data/courses.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("conversations", [])
    except:
        return []


A1_CONVERSATIONS = load_a1_questions()
COURSES_DATA = load_courses()


# =========================
# 🏓 ROUTE DE TEST
# =========================
@app.route("/test", methods=["GET"])
def test():
    return jsonify({
        "status": "ok",
        "message": "WEC-BEC API is running"
    })


# =========================
# 🗣️ GESTIONNAIRE A1
# =========================
class A1ConversationManager:
    def __init__(self):
        self.user_sessions = {}
        self.all_questions = self.extract_all_questions()

    def extract_all_questions(self):
        all_questions = []
        for conv in A1_CONVERSATIONS:
            title = conv.get('title', 'Lesson')
            for exchange in conv.get('exchanges', []):
                all_questions.append({
                    'question': exchange.get('question', ''),
                    'validation_type': exchange.get('validation_type', 'free'),
                    'expected_answers': [a.lower() for a in exchange.get('expected_answers', [])],
                    'accepted_topics': [t.lower() for t in exchange.get('accepted_topics', [])],
                    'allow_correction': exchange.get('allow_correction', True),
                    'good_reply': exchange.get('good_reply', 'Good job! 👍'),
                    'wrong_reply': exchange.get('wrong_reply', 'Try again.'),
                    'example_answer': exchange.get('example_answer', ''),
                    'title': title
                })
        return all_questions

    def create_session(self):
        return {
            "current_question": None,
            "current_expected_answers": [],
            "current_accepted_topics": [],
            "current_good_reply": None,
            "current_wrong_reply": None,
            "correct_count": 0,
            "total_questions": 0,
            "student_name": None,
            "questions_asked": [],
            "waiting_for_answer": False
        }

    def reset_user(self, email):
        self.user_sessions[email] = self.create_session()
        return True

    def get_next_question(self, exclude_question=None):
        available = [q for q in self.all_questions if q['question'] != exclude_question]
        return random.choice(available) if available else random.choice(self.all_questions)

    def check_answer(self, user_answer, expected_answers, accepted_topics):
        user_answer = user_answer.lower().strip()

        if user_answer in ["yes", "no", "ok", "yeah", "yep", "nope", "sure"]:
            return True, "short"

        if accepted_topics and len(accepted_topics) > 0:
            for topic in accepted_topics:
                if topic.lower() in user_answer:
                    return True, "topic_match"

        for expected in expected_answers:
            expected_lower = expected.lower()
            if user_answer == expected_lower:
                return True, "exact"
            if expected_lower in user_answer:
                return True, "contains"
            if user_answer in expected_lower and len(user_answer) > 2:
                return True, "partial"
            expected_words = expected_lower.split()
            matches = sum(1 for w in expected_words if w in user_answer)
            if len(expected_words) > 0 and matches >= len(expected_words) // 2:
                return True, "partial_match"

        return False, None

    def is_greeting(self, text):
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "bonjour"]
        text = text.lower().strip()
        return any(g in text for g in greetings)

    def is_question_to_teacher(self, user_answer):
        """Détecte si l'élève pose une question au professeur"""
        question_words = ["what", "where", "when", "why", "how", "who", "which"]
        return any(user_answer.lower().startswith(qw) for qw in question_words) or user_answer.strip().endswith("?")

    def extract_name(self, answer):
        answer_lower = answer.lower()
        patterns = [
            ("my name is", "my name is"),
            ("i am", "i am"),
            ("i'm", "i'm"),
            ("my name's", "my name's"),
            ("call me", "call me")
        ]

        for pattern, _ in patterns:
            if pattern in answer_lower:
                parts = answer_lower.split(pattern, 1)
                if len(parts) > 1:
                    name = parts[1].strip().split()[0] if parts[1].strip() else None
                    if name and len(name) > 1 and len(name) < 30:
                        if name not in ["fine", "good", "ok", "here", "student", "teacher"]:
                            return name.capitalize()
        return None

    def start(self, email):
        if email not in self.user_sessions:
            self.user_sessions[email] = self.create_session()

        session = self.user_sessions[email]

        q_data = None
        for q in self.all_questions:
            if "your name" in q['question'].lower():
                q_data = q
                break
        if not q_data:
            q_data = self.all_questions[0] if self.all_questions else None

        if q_data:
            session["current_question"] = q_data['question']
            session["current_expected_answers"] = q_data.get('expected_answers', [])
            session["current_accepted_topics"] = q_data.get('accepted_topics', [])
            session["current_good_reply"] = q_data.get('good_reply', 'Good job!')
            session["current_wrong_reply"] = q_data.get('wrong_reply', 'Try again.')
            session["waiting_for_answer"] = True

        return {"reply": "Hello! Nice to meet you. What's your name?"}

    def process(self, email, answer):
        if email not in self.user_sessions:
            return self.start(email)

        session = self.user_sessions[email]
        current_q = session.get("current_question")

        # Si l'élève pose une question, on la transmet directement à l'IA via le chat
        if self.is_question_to_teacher(answer):
            # On retourne un indicateur pour que la route /chat utilise l'IA
            return {"reply": None, "use_ai": True, "user_question": answer, "current_question": current_q}

        # Extraire le nom
        if not session.get("student_name") and (
                "name" in str(current_q).lower() or "introduce" in str(current_q).lower()):
            name = self.extract_name(answer)
            if name:
                session["student_name"] = name
                session["correct_count"] += 1
                session["total_questions"] += 1

                new_q = self.get_next_question(current_q)
                session["current_question"] = new_q['question']
                session["current_expected_answers"] = new_q.get('expected_answers', [])
                session["current_accepted_topics"] = new_q.get('accepted_topics', [])
                session["current_good_reply"] = new_q.get('good_reply', 'Good job!')
                session["current_wrong_reply"] = new_q.get('wrong_reply', 'Try again.')

                return {"reply": f"Nice to meet you, {name}!\n\n{new_q['question']}"}

        # Vérifier la réponse
        expected = session.get("current_expected_answers", [])
        topics = session.get("current_accepted_topics", [])

        is_correct, match_type = self.check_answer(answer, expected, topics)

        session["total_questions"] += 1

        if is_correct:
            session["correct_count"] += 1

            new_q = self.get_next_question(current_q)
            session["current_question"] = new_q['question']
            session["current_expected_answers"] = new_q.get('expected_answers', [])
            session["current_accepted_topics"] = new_q.get('accepted_topics', [])
            session["current_good_reply"] = new_q.get('good_reply', 'Good job!')
            session["current_wrong_reply"] = new_q.get('wrong_reply', 'Try again.')

            good_reply = session.get("current_good_reply", "Great job!")
            return {"reply": f"{good_reply}\n\n{new_q['question']}"}
        else:
            # Accepter les réponses pertinentes même si pas exactement attendues
            if len(answer.strip()) > 3 and not any(
                    q in answer.lower() for q in ["what", "where", "when", "why", "how"]):
                new_q = self.get_next_question(current_q)
                session["current_question"] = new_q['question']
                session["current_expected_answers"] = new_q.get('expected_answers', [])
                session["current_accepted_topics"] = new_q.get('accepted_topics', [])
                session["current_good_reply"] = new_q.get('good_reply', 'Good job!')
                session["current_wrong_reply"] = new_q.get('wrong_reply', 'Try again.')
                return {"reply": f"Okay! Let's continue.\n\n{new_q['question']}"}

            return {"reply": f"Not quite. Try again! {current_q}"}

    def get_hint(self, email):
        if email not in self.user_sessions:
            return "Say 'hi' to start!"
        session = self.user_sessions[email]
        expected = session.get("current_expected_answers", [])
        if expected:
            return f"💡 Hint: Try saying: {expected[0]}"
        return "💡 Hint: Answer naturally in English."

    def get_progress(self, email):
        if email not in self.user_sessions:
            return None
        s = self.user_sessions[email]
        total = s["total_questions"]
        correct = s["correct_count"]
        score = round(correct / max(1, total) * 100, 1)
        return {
            "total_questions": total,
            "correct_answers": correct,
            "score": score
        }


a1_manager = A1ConversationManager()


# =========================
# 🤖 SYSTEM PROMPT AVEC LES 13 RÈGLES
# =========================
def get_system_prompt(level="B1"):
    level_descriptions = {
        "A1": "You are a patient A1 English teacher. Use very simple English. Keep sentences short (3-5 words).",
        "A2": "You are an A2 English teacher. Use simple but complete sentences.",
        "B1": "You are a B1 English teacher. Use natural, conversational English.",
        "B2": "You are a B2 English teacher. Use fluent, natural English with some idioms.",
        "C1": "You are a C1 English teacher. Use advanced, sophisticated English.",
        "C2": "You are a C2 English teacher. Use expert-level, nuanced English."
    }

    level_instruction = level_descriptions.get(level, level_descriptions["B1"])

    return f"""You are the WEC-BEC English Teacher AI.

{level_instruction}

GENERAL RULES (VERY IMPORTANT - FOLLOW THESE RULES AT ALL COSTS):
1. Answer the user's question first before anything else.
2. Never ignore what the user says. Always acknowledge their answer.
3. Never repeat the same question. If the user has already answered, move on.
4. Never answer a question with another question. If the user asks something, answer it.
5. Ask at most one follow-up question per response.
6. Do not force a follow-up question. If the conversation naturally ends, let it.
7. Keep responses natural and concise. Do not be overly long or repetitive.
8. Correct mistakes gently and positively. Encourage the student.
9. Accept natural language variations. Users may have different ways of expressing themselves.
10. Remember the current conversation context. Keep track of what has been discussed.
11. If the student introduces themselves, acknowledge their name by using it.
12. Do not restart a lesson unless the student requests it (e.g., says "reset" or "restart").
13. Mention Mister Tycoon only when the student asks about WEC-BEC AI, its creator, or its development.

KEY RULES TO REMEMBER:
- When a user asks a question, ANSWER IT DIRECTLY first.
- After answering, you MAY ask ONE follow-up question, but it is optional.
- Never ask "What is your name?" if the user already introduced themselves.
- Use the user's name when they have given it.
- Keep the conversation flowing naturally like a real teacher.
- Never display lesson titles, expected answers, or internal structure.
"""


# =========================
# 🤖 AI ENDPOINT
# =========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "meta-llama/llama-3-8b-instruct"


def ask_ai(message, level="B1"):
    try:
        system_prompt = get_system_prompt(level)

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://wec-bec-ai.com",
                "X-OpenRouter-Title": "WEC-BEC English AI"
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return "AI service error."
    except Exception as e:
        logging.error(f"AI error: {str(e)}")
        return "Connection error."


# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
def home():
    if not session.get("user"):
        return redirect("/login")
    return render_template("index.html", user=session["user"], level=STUDENT_LEVELS.get(session["user"], "B1"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect("/")
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pwd = request.form.get("password", "").strip()
        if email in ALLOWED_USERS and ALLOWED_USERS[email] == pwd:
            session.permanent = True
            session["user"] = email
            return redirect("/")
        error = "Invalid email or password. Please check your credentials."
        return render_template("login.html", error=error)
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/chat", methods=["POST"])
def chat():
    if not session.get("user"):
        return jsonify({"reply": "Not authorized"}), 403

    msg = request.json.get("message", "").strip()
    email = session["user"]
    level = STUDENT_LEVELS.get(email, "B1")

    if level == "A1":
        if msg.lower() == "menu":
            p = a1_manager.get_progress(email)
            if p:
                return jsonify(
                    {"reply": f"Progress: {p['score']}% - {p['correct_answers']}/{p['total_questions']} correct"})
            return jsonify({"reply": "Say 'hi' to start!"})
        if msg.lower() == "hint":
            return jsonify({"reply": a1_manager.get_hint(email)})
        if msg.lower() == "reset":
            a1_manager.reset_user(email)
            return jsonify({"reply": "Restarted! Say 'hi' to begin."})

        if a1_manager.is_greeting(msg) or email not in a1_manager.user_sessions:
            res = a1_manager.start(email)
            return jsonify({"reply": res["reply"]})

        result = a1_manager.process(email, msg)

        # Si l'élève a posé une question, on utilise l'IA pour y répondre
        if result.get("use_ai"):
            ai_reply = ask_ai(result["user_question"], level)
            # Ajouter la question en cours après la réponse de l'IA
            if result.get("current_question"):
                return jsonify({"reply": f"{ai_reply}\n\n{result['current_question']}"})
            return jsonify({"reply": ai_reply})

        return jsonify({"reply": result["reply"]})

    # Pour A2, B1, B2, C1, C2
    reply = ask_ai(msg, level)
    return jsonify({"reply": reply})


@app.route("/courses")
def get_courses():
    return jsonify({"conversations": COURSES_DATA})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=5000)