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
# 🗣️ GESTIONNAIRE DE CONVERSATION A1 (AVEC MODE TEACHER)
# =========================
class A1ConversationManager:
    def __init__(self):
        self.user_sessions = {}
        self.all_questions = self.extract_all_questions()

        # Ordre logique des thèmes pour progression naturelle
        self.theme_sequence = [
            "greetings",  # Saluer
            "personal",  # Présentation (nom, âge, pays)
            "family",  # Famille
            "hobbies",  # Loisirs
            "daily",  # Vie quotidienne
            "education",  # Éducation
            "numbers",  # Chiffres
            "travel",  # Voyage
            "congo",  # Culture Congo
            "general"  # Général
        ]

        # Mots-clés indiquant que l'élève a besoin d'aide
        self.help_keywords = [
            "help me", "explain", "teach me", "i don't know", "i forgot",
            "give me the answer", "name them for me", "what is the answer",
            "i need help", "show me", "tell me the answer", "i don't understand",
            "i'm lost", "i am lost", "i don't remember", "repeat please"
        ]

    def extract_all_questions(self):
        """Extrait toutes les questions du JSON avec leurs métadonnées"""
        all_questions = []
        for conv in A1_CONVERSATIONS:
            title = conv.get('title', 'General')
            theme = self.get_theme_from_title(title)

            for exchange in conv.get('exchanges', []):
                all_questions.append({
                    'question': exchange.get('question', ''),
                    'validation_type': exchange.get('validation_type', 'free'),
                    'expected_answers': [a.lower() for a in exchange.get('expected_answers', [])],
                    'accepted_topics': exchange.get('accepted_topics', []),
                    'allow_correction': exchange.get('allow_correction', True),
                    'good_reply': exchange.get('good_reply', 'Good job! 👍'),
                    'wrong_reply': exchange.get('wrong_reply', 'Try again.'),
                    'example_answer': exchange.get('example_answer', ''),
                    'theme': theme
                })
        return all_questions

    def get_theme_from_title(self, title):
        """Détermine le thème à partir du titre de la leçon"""
        title_lower = title.lower()
        if "greeting" in title_lower or "farewell" in title_lower:
            return "greetings"
        if "color" in title_lower:
            return "hobbies"
        if "introduc" in title_lower or "yourself" in title_lower:
            return "personal"
        if "number" in title_lower or "cardinal" in title_lower:
            return "numbers"
        if "date" in title_lower or "day" in title_lower or "week" in title_lower or "month" in title_lower:
            return "daily"
        if "travel" in title_lower or "abroad" in title_lower:
            return "travel"
        if "family" in title_lower:
            return "family"
        if "education" in title_lower or "school" in title_lower or "university" in title_lower:
            return "education"
        if "congo" in title_lower or "africa" in title_lower:
            return "congo"
        if "hobby" in title_lower or "free time" in title_lower:
            return "hobbies"
        return "general"

    def get_questions_by_theme(self, theme):
        """Retourne toutes les questions d'un thème"""
        return [q for q in self.all_questions if q['theme'] == theme]

    def get_next_question_in_theme(self, theme, current_question=None):
        """Retourne la prochaine question dans le même thème"""
        theme_questions = self.get_questions_by_theme(theme)
        if not theme_questions:
            return None

        if current_question:
            for i, q in enumerate(theme_questions):
                if q['question'] == current_question and i + 1 < len(theme_questions):
                    return theme_questions[i + 1]

        return random.choice(theme_questions) if theme_questions else None

    def check_answer(self, user_answer, expected_answers, accepted_topics=None):
        """Vérifie si la réponse est correcte (tolérante)"""
        user_answer = user_answer.lower().strip()
        user_answer = user_answer.replace("wèk bèk", "wec bec").replace("wek bek", "wec bec").replace("walk back",
                                                                                                      "wec bec")

        # Si l'élève demande de l'aide, on ne valide pas comme réponse
        if self.needs_help(user_answer):
            return False, "need_help"

        # Réponses très courtes mais valides
        if user_answer in ["yes", "no", "ok", "yeah", "yep", "nope", "sure"]:
            return True, "short"

        # Vérification par mots-clés (accepted_topics)
        if accepted_topics and len(accepted_topics) > 0:
            for topic in accepted_topics:
                if topic.lower() in user_answer:
                    return True, "topic_match"

        # Vérification par réponses attendues
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

    def needs_help(self, user_answer):
        """Détecte si l'élève demande de l'aide"""
        user_lower = user_answer.lower()
        for keyword in self.help_keywords:
            if keyword in user_lower:
                return True
        return False

    def provide_help(self, current_question, expected_answers):
        """Fournit une explication pédagogique"""
        # Extraire le type de question pour donner une aide adaptée
        q_lower = current_question.lower()

        if "month" in q_lower:
            return "Of course! The 12 months of the year are:\n\n📅 January, February, March, April, May, June, July, August, September, October, November, December.\n\nNow, can you tell me three months of the year?"

        if "day" in q_lower and "week" in q_lower:
            return "Sure! The days of the week are:\n\n📆 Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday.\n\nNow, can you name the first day of the week?"

        if "color" in q_lower or "colour" in q_lower:
            return "Here are some colors in English:\n\n🎨 Red, Blue, Green, Yellow, Black, White, Pink, Purple, Orange, Brown.\n\nWhat is your favorite color?"

        if "number" in q_lower or "count" in q_lower:
            return "Let me help you with numbers:\n\n🔢 One (1), Two (2), Three (3), Four (4), Five (5), Six (6), Seven (7), Eight (8), Nine (9), Ten (10).\n\nCan you count from 1 to 5 for me?"

        if "nationality" in q_lower or "country" in q_lower:
            return "Nationality means which country you are from. For example:\n\n🌍 I am from Congo → I am Congolese.\nI am from France → I am French.\n\nWhat is your nationality?"

        if expected_answers:
            return f"Let me help you. For example, you can say: \"{expected_answers[0]}\"\n\nNow, can you try answering the question again?"

        return "Let me help you. Try to answer with a simple sentence. I know you can do it! 💪"

    def extract_name_from_answer(self, user_answer):
        """Extrait un nom potentiel de la réponse"""
        user_answer = user_answer.lower()
        if "my name is" in user_answer:
            parts = user_answer.split("my name is")
            if len(parts) > 1:
                name = parts[1].strip().split()[0] if parts[1].strip() else None
                if name and len(name) > 1:
                    return name.capitalize()
        if "i am" in user_answer and len(user_answer) < 30:
            parts = user_answer.split("i am")
            if len(parts) > 1:
                name = parts[1].strip().split()[0] if parts[1].strip() else None
                if name and len(name) > 1 and name not in ["fine", "good", "ok", "here", "student"]:
                    return name.capitalize()
        if "call me" in user_answer:
            parts = user_answer.split("call me")
            if len(parts) > 1:
                name = parts[1].strip().split()[0] if parts[1].strip() else None
                if name and len(name) > 1:
                    return name.capitalize()
        return None

    def extract_age_from_answer(self, user_answer):
        """Extrait un âge potentiel de la réponse"""
        import re
        numbers = re.findall(r'\d+', user_answer)
        if numbers:
            age = int(numbers[0])
            if 1 <= age <= 120:
                return age
        return None

    def is_question_to_teacher(self, user_answer):
        """Détecte si l'élève pose une question au professeur (hors demande d'aide)"""
        if self.needs_help(user_answer):
            return False  # Les demandes d'aide sont traitées séparément

        question_words = ["what", "where", "when", "why", "how", "who", "which", "could you", "can you", "do you"]
        if " and you" in user_answer.lower() or " and you?" in user_answer.lower():
            return True
        return any(user_answer.lower().startswith(qw) for qw in question_words) or user_answer.strip().endswith("?")

    def answer_student_question(self, user_question, student_name=None):
        """Répond aux questions que l'élève pose au professeur"""
        q_lower = user_question.lower()

        if "and you" in q_lower or "and you?" in q_lower:
            return "I'm an AI teacher, so I don't have personal details. But I'm here to help you learn English! 😊"

        if "how are you" in q_lower:
            return "I'm doing great, thank you for asking! How are you today? 😊"

        if "what is your name" in q_lower or "your name" in q_lower:
            return "I'm your WEC-BEC English teacher! You can call me WEC-BEC AI. 😊"

        if "where are you from" in q_lower:
            return "I'm an AI, so I live in the cloud! But I was created to help students like you learn English. 🌍"

        if "how old are you" in q_lower:
            return "As an AI, I don't have an age. But I'm always here to help you learn! 🎂"

        if "do you like" in q_lower:
            return "I love helping students learn English! It's my favorite thing to do. 💖"

        if "can you help me" in q_lower:
            return "Of course! That's why I'm here. Let's practice together! 🤝"

        return "That's a great question! Let me help you with that. Could you try answering my question first? 😊"

    def is_greeting(self, text):
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "bonjour", "good day"]
        text = text.lower().strip()
        return any(greeting in text for greeting in greetings)

    def create_session(self):
        return {
            "current_question": None,
            "current_expected_answers": [],
            "current_accepted_topics": [],
            "current_theme": None,
            "current_validation_type": "free",
            "correct_count": 0,
            "wrong_count": 0,
            "total_questions": 0,
            "detected_level": "A1",
            "student_name": None,
            "student_age": None,
            "current_theme_index": 0,
            "questions_asked_in_theme": 0,
            "help_mode": False  # Mode aide activé
        }

    def reset_user(self, user_email):
        self.user_sessions[user_email] = self.create_session()
        return True

    def start_conversation(self, user_email):
        """Démarre la conversation de manière naturelle"""
        if user_email not in self.user_sessions:
            self.user_sessions[user_email] = self.create_session()

        session = self.user_sessions[user_email]

        # Commencer par une question simple sur le prénom
        theme_questions = self.get_questions_by_theme("personal")
        question_data = None

        for q in theme_questions:
            if "your name" in q['question'].lower() and "name" in q['question'].lower():
                question_data = q
                break

        if not question_data and theme_questions:
            question_data = theme_questions[0]

        if not question_data and self.all_questions:
            question_data = self.all_questions[0]

        if question_data:
            session["current_question"] = question_data['question']
            session["current_expected_answers"] = question_data.get('expected_answers', [])
            session["current_accepted_topics"] = question_data.get('accepted_topics', [])
            session["current_validation_type"] = question_data.get('validation_type', 'free')
            session["current_theme"] = question_data.get('theme', 'personal')
            session["questions_asked_in_theme"] = 1
            session["help_mode"] = False

        return {
            "reply": "Hello! Nice to meet you. What's your name? 😊",
            "question": session.get("current_question")
        }

    def process_answer(self, user_email, user_answer):
        """Traite la réponse de l'élève comme un vrai professeur"""
        if user_email not in self.user_sessions:
            return self.start_conversation(user_email)

        session = self.user_sessions[user_email]
        current_q = session.get("current_question")
        expected = session.get("current_expected_answers", [])
        accepted_topics = session.get("current_accepted_topics", [])
        current_theme = session.get("current_theme", "personal")

        # 1. D'abord, vérifier si l'élève demande de l'aide
        if self.needs_help(user_answer):
            help_message = self.provide_help(current_q, expected)
            session["help_mode"] = True
            return {
                "reply": help_message,
                "in_help_mode": True
            }

        # 2. Si l'élève pose une question, y répondre et répéter la question
        if self.is_question_to_teacher(user_answer):
            ai_response = self.answer_student_question(user_answer, session.get("student_name"))
            return {
                "reply": f"{ai_response}\n\n{current_q}",
                "keep_question": True
            }

        # 3. Vérifier la réponse
        is_correct, match_type = self.check_answer(user_answer, expected, accepted_topics)

        # 4. Extraire les informations utiles
        extracted_name = self.extract_name_from_answer(user_answer) if not session.get("student_name") else None
        if extracted_name:
            session["student_name"] = extracted_name

        extracted_age = self.extract_age_from_answer(user_answer) if not session.get("student_age") else None
        if extracted_age:
            session["student_age"] = extracted_age

        # 5. Si la réponse est correcte
        if is_correct:
            session["correct_count"] += 1
            session["total_questions"] += 1
            session["wrong_count"] = 0
            session["questions_asked_in_theme"] += 1
            session["help_mode"] = False

            # Construire une réponse de félicitations naturelle
            if session.get("student_name") and "name" in current_q.lower():
                name = session["student_name"]
                natural_reply = f"Nice to meet you, {name}! 😊"
            elif "age" in current_q.lower() and extracted_age:
                natural_reply = f"Great! You are {extracted_age} years old! 🎂"
            elif match_type == "short":
                natural_reply = f"Good!"
            else:
                natural_reply = "Great job! 👍"

            # Décider la prochaine question
            max_per_theme = 3
            if session["questions_asked_in_theme"] >= max_per_theme:
                current_index = self.theme_sequence.index(current_theme) if current_theme in self.theme_sequence else 0
                next_index = (current_index + 1) % len(self.theme_sequence)
                next_theme = self.theme_sequence[next_index]
                next_q_data = self.get_next_question_in_theme(next_theme)
                session["current_theme"] = next_theme
                session["questions_asked_in_theme"] = 1
            else:
                next_q_data = self.get_next_question_in_theme(current_theme, current_q)
                if not next_q_data:
                    current_index = self.theme_sequence.index(
                        current_theme) if current_theme in self.theme_sequence else 0
                    next_index = (current_index + 1) % len(self.theme_sequence)
                    next_theme = self.theme_sequence[next_index]
                    next_q_data = self.get_next_question_in_theme(next_theme)
                    session["current_theme"] = next_theme
                    session["questions_asked_in_theme"] = 1

            if not next_q_data:
                next_q_data = random.choice(self.all_questions) if self.all_questions else None

            if next_q_data:
                session["current_question"] = next_q_data['question']
                session["current_expected_answers"] = next_q_data.get('expected_answers', [])
                session["current_accepted_topics"] = next_q_data.get('accepted_topics', [])
                session["current_validation_type"] = next_q_data.get('validation_type', 'free')

                return {
                    "reply": f"{natural_reply}\n\n{next_q_data['question']}",
                    "next_question": next_q_data['question'],
                    "correct": True
                }
            else:
                return {
                    "reply": f"{natural_reply}\n\nYou've completed all lessons! 🎉",
                    "completed": True
                }

        # 6. Si la réponse est incorrecte
        else:
            session["wrong_count"] += 1

            # Ne pas compter les demandes d'aide comme des erreurs
            if match_type != "need_help":
                session["total_questions"] += 1

            # Après 2 erreurs, proposer de l'aide
            if session["wrong_count"] >= 2 and not session["help_mode"]:
                return {
                    "reply": f"You're having trouble with this question. Would you like me to help you? Just say 'help me' and I'll explain! 😊\n\n{current_q}",
                    "repeat_question": True,
                    "correct": False
                }

            # Donner un indice simple
            if expected:
                return {
                    "reply": f"Not quite. Try again! {current_q}",
                    "repeat_question": True,
                    "correct": False
                }

            return {
                "reply": f"Let me repeat the question: {current_q}",
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
            "IMPORTANT: Behave like a real human teacher.\n"
            "If the student asks for help (help me, explain, I don't know, etc.), provide a clear explanation or example.\n"
            "Then ask an easier question to check understanding.\n"
            "Respond to what the student says before asking the next question.\n"
            "If the student says 'and you?', answer the question yourself.\n"
            "Keep the conversation flowing naturally, like a real dialogue.\n"
            "Never show lesson titles or expected answers. Just have a natural conversation.\n"
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