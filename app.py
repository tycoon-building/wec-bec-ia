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
from flask_cors import CORS
import time

load_dotenv()

app = Flask(__name__)

# =========================
# 🔐 CORS CONFIGURATION
# =========================
CORS(app, origins=['*'], supports_credentials=True)

# =========================
# 🔐 SECURITY CONFIG
# =========================
app.secret_key = os.getenv("SECRET_KEY", "wec-bec-secret-key")
app.permanent_session_lifetime = timedelta(hours=2)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max

# =========================
# 👤 USERS DATABASE (garde tes identifiants)
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
# 🎤 FASTER-WHISPER - VERSION TINY (RAPIDE) ⚡
# =========================
WHISPER_MODEL_SIZE = "tiny"  # tiny = plus rapide, moins de RAM
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

print("🚀 Loading Whisper model...")
try:
    whisper_model = WhisperModel(
        WHISPER_MODEL_SIZE,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE_TYPE,
        cpu_threads=2,
        num_workers=1
    )
    print(f"✅ Whisper '{WHISPER_MODEL_SIZE}' ready (fast mode)")
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
# 🎤 TRANSCRIPTION ENDPOINT - VERSION STABLE
# =========================
@app.route("/transcribe", methods=["POST"])
def transcribe():
    start_time = time.time()

    # Vérification 1: Whisper chargé
    if whisper_model is None:
        return jsonify({"text": "", "error": "Whisper model not ready"}), 503

    # Vérification 2: Audio présent
    if "audio" not in request.files:
        return jsonify({"text": "", "error": "No audio file"}), 400

    audio = request.files["audio"]
    if audio.filename == "":
        return jsonify({"text": "", "error": "Empty file"}), 400

    # Vérification 3: Taille du fichier
    audio.seek(0, 2)
    size = audio.tell()
    audio.seek(0)
    if size < 1000:  # Moins de 1KB
        return jsonify({"text": "", "error": "Audio too short"}), 400

    print(f"📁 Audio received: {size} bytes")

    try:
        # Sauvegarder temporairement
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            audio.save(tmp.name)
            tmp_path = tmp.name

        print(f"📁 Saved to: {tmp_path}")

        # Transcription avec paramètres rapides
        segments, info = whisper_model.transcribe(
            tmp_path,
            beam_size=1,  # Plus rapide
            language="en",
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                threshold=0.5
            )
        )

        text = " ".join([segment.text for segment in segments]).strip()

        # Nettoyer
        os.unlink(tmp_path)

        elapsed = time.time() - start_time
        print(f"📝 Transcribed ({elapsed:.2f}s): '{text}'")

        if not text:
            return jsonify({"text": "", "error": "No speech detected"}), 200

        return jsonify({"text": text})

    except Exception as e:
        logging.error(f"Transcription error: {str(e)}")
        return jsonify({"text": "", "error": str(e)}), 500


# =========================
# 🏓 ROUTE DE TEST
# =========================
@app.route("/test", methods=["GET"])
def test():
    return jsonify({
        "status": "ok",
        "whisper_ready": whisper_model is not None,
        "whisper_model": WHISPER_MODEL_SIZE
    })


# =========================
# 🗣️ GESTIONNAIRE A1 (garde ton code existant)
# =========================
class A1ConversationManager:
    # ... garde toute ta classe intacte
    pass


a1_manager = A1ConversationManager()

# =========================
# 🤖 AI ENDPOINT (garde ton code)
# =========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "meta-llama/llama-3-8b-instruct"


def ask_ai(message, level="B1"):
    # ... garde ton code
    pass


# =========================
# 🌐 ROUTES (garde tes routes)
# =========================
@app.route("/")
def home():
    if not session.get("user"):
        return redirect("/login")
    return render_template("index.html", user=session["user"], level=STUDENT_LEVELS.get(session["user"], "B1"))


@app.route("/login", methods=["GET", "POST"])
def login():
    # ... garde ton code
    pass


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/chat", methods=["POST"])
def chat():
    # ... garde ton code
    pass


@app.route("/courses")
def get_courses():
    return jsonify({"conversations": COURSES_DATA})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)