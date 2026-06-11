from flask import Flask, request, jsonify, render_template, redirect, session
import requests
import json
import logging
import random
import os
import tempfile
from datetime import timedelta
from dotenv import load_dotenv
from faster_whisper import WhisperModel

load_dotenv()

app = Flask(__name__)

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
    # 🛠️ ADMIN
    "admin@wec-bec.com": "WBcAdmin#Ultra2026",

    # 👨‍🎓 APPRENANTS A1 (1 à 30)
    "apprenant1@gmail.com": "WBcA1!Start01",
    "apprenant2@gmail.com": "WBcA1!Start02",
    "apprenant3@gmail.com": "WBcA1!Start03",
    "apprenant4@gmail.com": "WBcA1!Start04",
    "apprenant5@gmail.com": "WBcA1!Start05",
    "apprenant6@gmail.com": "WBcA1!Start06",
    "apprenant7@gmail.com": "WBcA1!Start07",
    "apprenant8@gmail.com": "WBcA1!Start08",
    "apprenant9@gmail.com": "WBcA1!Start09",
    "apprenant10@gmail.com": "WBcA1!Start10",
    "apprenant11@gmail.com": "WBcA1!Start11",
    "apprenant12@gmail.com": "WBcA1!Start12",
    "apprenant13@gmail.com": "WBcA1!Start13",
    "apprenant14@gmail.com": "WBcA1!Start14",
    "apprenant15@gmail.com": "WBcA1!Start15",
    "apprenant16@gmail.com": "WBcA1!Start16",
    "apprenant17@gmail.com": "WBcA1!Start17",
    "apprenant18@gmail.com": "WBcA1!Start18",
    "apprenant19@gmail.com": "WBcA1!Start19",
    "apprenant20@gmail.com": "WBcA1!Start20",
    "apprenant21@gmail.com": "WBcA1!Start21",
    "apprenant22@gmail.com": "WBcA1!Start22",
    "apprenant23@gmail.com": "WBcA1!Start23",
    "apprenant24@gmail.com": "WBcA1!Start24",
    "apprenant25@gmail.com": "WBcA1!Start25",
    "apprenant26@gmail.com": "WBcA1!Start26",
    "apprenant27@gmail.com": "WBcA1!Start27",
    "apprenant28@gmail.com": "WBcA1!Start28",
    "apprenant29@gmail.com": "WBcA1!Start29",
    "apprenant30@gmail.com": "WBcA1!Start30",

    # 🧑 UTILISATEURS SPÉCIAUX
    "tycoon@wec-bec.com": "Tycoon#Speak2026!",
    "shooter@wec-bec.com": "Shooter#Learn2026!",
    "mefia@wec-bec.com": "Mefia#English2026!"
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
    "apprenant18@gmail.com": "A1",
    "apprenant19@gmail.com": "A1",
    "apprenant20@gmail.com": "A1",
    "apprenant21@gmail.com": "A1",
    "apprenant22@gmail.com": "A1",
    "apprenant23@gmail.com": "A1",
    "apprenant24@gmail.com": "A1",
    "apprenant25@gmail.com": "A1",
    "apprenant26@gmail.com": "A1",
    "apprenant27@gmail.com": "A1",
    "apprenant28@gmail.com": "A1",
    "apprenant29@gmail.com": "A1",
    "apprenant30@gmail.com": "A1",
    "tycoon@wec-bec.com": "B2",
    "shooter@wec-bec.com": "B1",
    "mefia@wec-bec.com": "B1"
}

# =========================
# 🎤 FASTER-WHISPER
# =========================
WHISPER_MODEL_SIZE = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

print("🚀 Loading Whisper model...")
try:
    whisper_model = WhisperModel(
        WHISPER_MODEL_SIZE,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE_TYPE,
        cpu_threads=4,
        num_workers=2
    )
    print(f"✅ Whisper '{WHISPER_MODEL_SIZE}' ready")
except Exception as e:
    print(f"⚠️ Whisper error: {e}")
    whisper_model = None


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
# 🎤 TRANSCRIPTION ENDPOINT
# =========================
@app.route("/transcribe", methods=["POST"])
def transcribe():
    if whisper_model is None:
        return jsonify({"text": "", "error": "Model not ready"})

    if "audio" not in request.files:
        return jsonify({"text": "", "error": "No audio"})

    audio = request.files["audio"]
    if audio.filename == "":
        return jsonify({"text": "", "error": "Empty file"})

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            audio.save(tmp.name)
            tmp_path = tmp.name

        segments, info = whisper_model.transcribe(
            tmp_path,
            beam_size=1,
            language="en",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=300)
        )

        text = " ".join([segment.text for segment in segments]).strip()
        os.unlink(tmp_path)

        if not text:
            return jsonify({"text": "", "error": "No speech detected"})

        return jsonify({"text": text})

    except Exception as e:
        logging.error(f"Transcription error: {str(e)}")
        return jsonify({"text": "", "error": str(e)})


# =========================
# 🗣️ GESTIONNAIRE A1
# =========================
class A1ConversationManager:
    def __init__(self):
        self.user_sessions = {}
        self.all_questions = self.extract_questions()

    def extract_questions(self):
        questions = []
        for conv in A1_CONVERSATIONS:
            for ex in conv.get('exchanges', []):
                questions.append({
                    'question': ex.get('question', ''),
                    'expected': [a.lower() for a in ex.get('expected_answers', [])],
                    'topics': ex.get('accepted_topics', []),
                    'good_reply': ex.get('good_reply', 'Good job!'),
                    'wrong_reply': ex.get('wrong_reply', 'Try again.')
                })
        return questions

    def create_session(self):
        return {
            "current_q": None,
            "current_expected": [],
            "current_topics": [],
            "correct": 0,
            "total": 0,
            "name": None
        }

    def reset_user(self, email):
        self.user_sessions[email] = self.create_session()
        return True

    def start(self, email):
        if email not in self.user_sessions:
            self.user_sessions[email] = self.create_session()

        q_data = self.all_questions[0] if self.all_questions else None

        if q_data:
            self.user_sessions[email]["current_q"] = q_data['question']
            self.user_sessions[email]["current_expected"] = q_data['expected']
            self.user_sessions[email]["current_topics"] = q_data['topics']

        return {"reply": "Hello! Nice to meet you. What's your name?"}

    def process(self, email, answer):
        if email not in self.user_sessions:
            return self.start(email)

        session = self.user_sessions[email]
        current_q = session.get("current_q")
        expected = session.get("current_expected", [])
        topics = session.get("current_topics", [])

        # Extraire le nom
        if not session.get("name") and ("name" in str(current_q).lower() or "introduce" in str(current_q).lower()):
            name = answer.lower().replace("my name is", "").replace("i am", "").strip()
            if name and len(name) < 30 and not name.startswith(("what", "where", "how")):
                session["name"] = name.capitalize()

        # Vérifier la réponse
        answer_lower = answer.lower().strip()
        is_correct = False

        if topics:
            for t in topics:
                if t.lower() in answer_lower:
                    is_correct = True
                    break

        if not is_correct:
            for e in expected:
                if e.lower() in answer_lower:
                    is_correct = True
                    break

        session["total"] += 1

        if is_correct:
            session["correct"] += 1

            import random
            new_q = random.choice(self.all_questions)

            session["current_q"] = new_q['question']
            session["current_expected"] = new_q['expected']
            session["current_topics"] = new_q['topics']

            if session.get("name") and "name" in str(current_q).lower():
                reply = f"Nice to meet you, {session['name']}!"
            else:
                reply = "Great job!"

            return {"reply": f"{reply}\n\n{new_q['question']}"}
        else:
            return {"reply": f"Not quite. Try again! {current_q}"}

    def get_hint(self, email):
        if email not in self.user_sessions:
            return "Say 'hi' to start!"
        expected = self.user_sessions[email].get("current_expected", [])
        return f"Hint: {expected[0]}" if expected else "Answer naturally."

    def get_progress(self, email):
        if email not in self.user_sessions:
            return None
        s = self.user_sessions[email]
        score = round(s["correct"] / max(1, s["total"]) * 100, 1)
        return {"total": s["total"], "correct": s["correct"], "score": score}

    # ⚡ AJOUT DE LA MÉTHODE MANQUANTE ⚡
    def is_greeting(self, text):
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "bonjour"]
        text = text.lower().strip()
        return any(g in text for g in greetings)


a1_manager = A1ConversationManager()

# =========================
# 🤖 AI ENDPOINT
# =========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "meta-llama/llama-3-8b-instruct"


def ask_ai(message, level="B1"):
    try:
        prompt = f"You are WEC-BEC English teacher. Level {level}. Be friendly. Ask ONE question. Reply:"
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": MODEL,
                "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": message}]
            },
            timeout=15
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return "AI service error."
    except:
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

        # Vérification des identifiants
        if email in ALLOWED_USERS and ALLOWED_USERS[email] == pwd:
            session.permanent = True
            session["user"] = email
            return redirect("/")

        # Message d'erreur plus clair
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
                return jsonify({"reply": f"Progress: {p['score']}% - {p['correct']}/{p['total']} correct"})
            return jsonify({"reply": "Say 'hi' to start!"})

        if msg.lower() == "hint":
            return jsonify({"reply": a1_manager.get_hint(email)})

        if msg.lower() == "reset":
            a1_manager.reset_user(email)
            return jsonify({"reply": "Restarted! Say 'hi' to begin."})

        if a1_manager.is_greeting(msg) or email not in a1_manager.user_sessions:
            res = a1_manager.start(email)
            return jsonify({"reply": res["reply"]})

        res = a1_manager.process(email, msg)
        return jsonify({"reply": res["reply"]})

    reply = ask_ai(msg, level)
    return jsonify({"reply": reply})


@app.route("/courses")
def get_courses():
    return jsonify({"conversations": COURSES_DATA})


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)