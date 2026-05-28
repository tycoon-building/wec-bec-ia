from flask import Flask, request, jsonify, render_template, redirect, session
import requests
import json
import logging
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
# loading json file
@app.route("/courses")
def courses():
    with open("data/courses.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)
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
def ask_ai(message):

    try:

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

                            "You teach English according to the student's CEFR level: A1, A2, B1, B2, C1, and C2. "

                            "For A1 students: "
                            "Use very easy English, short sentences, basic vocabulary, and slow explanations. "
                            "Focus on greetings, school, food, family, hobbies, colors, numbers, weather, travel, and daily life. "

                            "For A2 students: "
                            "Use simple English with slightly longer conversations and simple grammar explanations. "

                            "For B1 students: "
                            "Use intermediate English with more natural conversations and moderate vocabulary. "

                            "For B2 students: "
                            "Use natural fluent English with richer vocabulary and more detailed explanations. "

                            "For C1 and C2 students: "
                            "Use advanced fluent English, professional vocabulary, idioms, nuanced expressions, and native-level conversation. "

                            "If the student speaks French, you may explain difficult words or grammar in French. "

                            "Always adapt your English difficulty to the student's level and answers. "

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

                            "For advanced students, use more detailed and intelligent conversations. "

                            "Help students improve speaking, listening, vocabulary, pronunciation, grammar, confidence, and fluency. "

                            "Be supportive, intelligent, dynamic, and motivating."
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
# 🌐 HOME (PROTECTED)
# =========================
@app.route("/")
def home():

    if not session.get("user"):

        return redirect("/login")

    return render_template(
        "index.html",
        user=session["user"]
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

    if not message:

        return jsonify({"reply": "Empty message"}), 400

    reply = ask_ai(message)

    return jsonify({"reply": reply})


# =========================
# 🚀 RUN SERVER
# =========================
if __name__ == "__main__":

    app.run(
        debug=False,
        host="0.0.0.0",
        port=5000
    )