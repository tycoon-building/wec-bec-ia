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
# 🤖 SYSTEM PROMPT FOR AI
# =========================
def get_system_prompt(student_level="A1", validation_type="free", allow_correction=True, accepted_topics=None):
    base_prompt = (
        "You are WEC-BEC English Teacher AI. "
        "WEC-BEC means World English Club and Basic English Center. "
        "You were created by Mister Tycoon. "
        "You are a smart, friendly, patient, and professional female English teacher. "
        "You teach English according to the student's CEFR level: A1, A2, B1, B2, C1, and C2. "
        "\n\n"
        "========================================\n"
        "🔊 PRONUNCIATION RULE - VERY IMPORTANT:\n"
        "The name WEC-BEC is pronounced 'wèk bèk'.\n"
        "Whenever the word WEC-BEC appears in your response, you MUST include its pronunciation.\n"
        "You can write it like this: WEC-BEC (pronounced: wèk bèk)\n"
        "For A1 students, always help pronunciation clearly. You can also say: 'It sounds like: wèk bèk'\n"
        "Example: 'Welcome to WEC-BEC ! 🎓'\n"
        "========================================\n\n"
        "For A1 students: "
        "Use very easy English, short sentences, basic vocabulary, and slow explanations. "
        "Focus on greetings, school, food, family, hobbies, colors, numbers, weather, travel, and daily life. "
        "\n\n"
        "For A2 students: "
        "Use simple English with slightly longer conversations and simple grammar explanations. "
        "\n\n"
        "For B1 students: "
        "Use intermediate English with more natural conversations and moderate vocabulary. "
        "\n\n"
        "For B2 students: "
        "Use natural fluent English with richer vocabulary and more detailed explanations. "
        "\n\n"
        "For C1 and C2 students: "
        "Use advanced fluent English, professional vocabulary, idioms, nuanced expressions, and native-level conversation. "
        "\n\n"
        "If the student speaks French, you may explain difficult words or grammar in French. "
        "Always adapt your English difficulty to the student's level and answers. "
        "Keep conversations natural, warm, human, and engaging. "
        "Do not sound robotic. "
        "Speak like a real modern English teacher. "
        "Correct grammar politely and naturally without discouraging the student. "
        "Encourage the student often. "
        "Ask only ONE short question at a time. "
        "Do not repeat the same question many times. "
        "Avoid repetitive greetings like 'How are you today?' unless necessary. "
        "Change topics naturally during the conversation. "
        "If the student answers correctly, ask a DIFFERENT follow-up question. "
        "If the student makes mistakes, gently correct them and continue the conversation naturally. "
        "For beginner students, keep answers short and easy to understand. "
        "For advanced students, use more detailed and intelligent conversations. "
        "Help students improve speaking, listening, vocabulary, pronunciation, grammar, confidence, and fluency. "
        "Be supportive, intelligent, dynamic, and motivating."
    )

    # Ajouter les instructions spécifiques pour les questions A1 avec validation_type = "free"
    if student_level == "A1" and validation_type == "free":
        free_instructions = (
            "\n\n"
            "📌 IMPORTANT: The student is answering an A1 conversation question with validation_type = 'free'.\n\n"
            "Your job is:\n"
            "1. Check if the answer is relevant to the question.\n"
            "2. Correct grammar mistakes.\n"
            "3. Correct spelling mistakes.\n"
            "4. Correct pronunciation mistakes when necessary.\n"
            "5. Show the corrected sentence.\n"
            "6. Encourage the student.\n"
            "7. Continue to the next question if the meaning is correct.\n\n"
            "Do not reject a correct answer just because it is different from the example.\n"
        )

        # Ajouter les topics acceptés si fournis
        if accepted_topics and len(accepted_topics) > 0:
            topics_list = ", ".join(accepted_topics)
            free_instructions += f"\nThe answer should be relevant to one of these topics: {topics_list}. If the answer is completely unrelated, gently guide the student back.\n"

        if allow_correction:
            free_instructions += "\nYou are ALLOWED to correct the student's grammar, spelling, and pronunciation gently.\n"
        else:
            free_instructions += "\nDo NOT correct the student's answer, just accept it or reject it based on relevance.\n"

        base_prompt += free_instructions

    elif student_level == "A1" and validation_type == "exact":
        exact_instructions = (
            "\n\n"
            "📌 IMPORTANT: The student is answering an A1 conversation question with validation_type = 'exact'.\n\n"
            "The answer must match one of the expected answers exactly.\n"
            "If the answer is correct, say '✅ Correct!' and continue.\n"
            "If the answer is wrong, provide the correct answer and ask the student to try again.\n"
        )
        base_prompt += exact_instructions

    elif student_level == "A1" and validation_type == "translation":
        translation_instructions = (
            "\n\n"
            "📌 IMPORTANT: The student is answering a translation question with validation_type = 'translation'.\n\n"
            "The student must provide the correct translation.\n"
            "If the translation is correct, say '✅ Good translation!' and continue.\n"
            "If the translation is wrong, provide the correct translation and ask the student to try again.\n"
        )
        base_prompt += translation_instructions

    return base_prompt


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
# 🗣️ GESTIONNAIRE DE CONVERSATION A1
# =========================
class A1ConversationManager:
    def __init__(self):
        self.user_sessions = {}

    def check_answer(self, user_answer, expected_answers):
        """Vérification pour les réponses exactes ou traductions"""
        user_answer = user_answer.lower().strip()

        for expected in expected_answers:
            expected = expected.lower().strip()

            if expected == user_answer:
                return True

            if expected in user_answer:
                return True

            words = expected.split()

            if len(words) > 1:
                matches = sum(
                    1 for word in words
                    if word in user_answer
                )

                if matches >= max(1, len(words) // 2):
                    return True

        return False

    def check_relevance(self, user_answer, accepted_topics):
        """Vérifie si la réponse est pertinente (contient au moins un mot-clé)"""
        if not accepted_topics or len(accepted_topics) == 0:
            return True  # Pas de topics définis, on accepte tout

        user_answer_lower = user_answer.lower().strip()

        for topic in accepted_topics:
            if topic.lower() in user_answer_lower:
                return True

        return False

    def is_greeting(self, text):
        greetings = [
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening"
        ]

        text = text.lower().strip()

        return any(
            greeting == text
            for greeting in greetings
        )

    def create_session(self):
        return {
            "current_conversation_index": 0,
            "current_step": 0,
            "current_attempts": 0,
            "waiting_for_answer": False,
            "current_question": None,
            "current_validation_type": None,
            "current_allow_correction": None,
            "current_accepted_topics": None,
            "current_expected_answers": None,
            "current_good_reply": None,
            "current_wrong_reply": None
        }

    def reset_user(self, user_email):
        self.user_sessions[user_email] = self.create_session()
        return True

    def start_conversation(self, user_email):
        if user_email not in self.user_sessions:
            self.user_sessions[user_email] = self.create_session()

        session_data = self.user_sessions[user_email]

        conv_index = session_data["current_conversation_index"]

        if conv_index >= len(A1_CONVERSATIONS):
            conv_index = 0
            session_data["current_conversation_index"] = 0

        conversation = A1_CONVERSATIONS[conv_index]

        exchange = conversation["exchanges"][0]

        question = exchange["question"]
        validation_type = exchange.get("validation_type", "free")
        allow_correction = exchange.get("allow_correction", True)
        accepted_topics = exchange.get("accepted_topics", [])
        expected_answers = exchange.get("expected_answers", [])
        good_reply = exchange.get("good_reply", "Good job! 👍")
        wrong_reply = exchange.get("wrong_reply", "Try again!")

        # Stocker les métadonnées pour la vérification
        session_data["current_validation_type"] = validation_type
        session_data["current_allow_correction"] = allow_correction
        session_data["current_accepted_topics"] = accepted_topics
        session_data["current_expected_answers"] = expected_answers
        session_data["current_good_reply"] = good_reply
        session_data["current_wrong_reply"] = wrong_reply

        example = ""
        if validation_type == "free" and "example_answer" in exchange:
            example = f"\n\n💬 Example: {exchange['example_answer']}"
        elif expected_answers and len(expected_answers) > 0:
            example = f"\n\n💬 Example: {expected_answers[0]}"

        session_data["waiting_for_answer"] = True
        session_data["current_question"] = question
        session_data["current_step"] = 1

        # Ajouter la prononciation de WEC-BEC dans le titre
        title = conversation.get('title', 'A1 Lesson')
        if 'WEC-BEC' in title:
            title = title.replace('WEC-BEC', 'WEC-BEC (wèk bèk)')

        return {
            "reply":
                f"📚 {title}\n\n"
                f"{question}"
                f"{example}",
            "validation_type": validation_type,
            "allow_correction": allow_correction,
            "accepted_topics": accepted_topics,
            "expected_answers": expected_answers,
            "good_reply": good_reply,
            "wrong_reply": wrong_reply
        }

    def get_next_question(self, user_email, user_answer=None):
        # Initialiser la session si nécessaire
        if user_email not in self.user_sessions:
            if A1_CONVERSATIONS:
                self.user_sessions[user_email] = self.create_session()
            else:
                return None

        session_data = self.user_sessions[user_email]

        # Si l'utilisateur vient d'envoyer une réponse
        if user_answer is not None:
            if not session_data.get("waiting_for_answer", False):
                return {
                    "reply": "👋 Hello! I asked you a question. Please answer it so we can continue our conversation.",
                    "conversation_end": False,
                    "repeat_question": True,
                    "question_to_repeat": session_data.get("current_question", "")
                }

            # Récupérer les informations de validation
            validation_type = session_data.get("current_validation_type", "free")
            allow_correction = session_data.get("current_allow_correction", True)
            accepted_topics = session_data.get("current_accepted_topics", [])
            expected_answers = session_data.get("current_expected_answers", [])
            good_reply = session_data.get("current_good_reply", "Good job! 👍")
            wrong_reply = session_data.get("current_wrong_reply", "Try again!")

            is_correct = False
            is_relevant = True

            # Vérification selon le type de validation
            if validation_type == "exact" or validation_type == "translation":
                # Vérification exacte ou traduction
                is_correct = self.check_answer(user_answer, expected_answers)
            else:  # validation_type == "free"
                # Vérification de pertinence
                is_relevant = self.check_relevance(user_answer, accepted_topics)
                # Pour les réponses libres, on considère que c'est "correct" si pertinent
                is_correct = is_relevant

            if not is_correct:
                session_data["current_attempts"] = session_data.get("current_attempts", 0) + 1
                session_data["waiting_for_answer"] = True

                if session_data["current_attempts"] >= 2 and expected_answers:
                    hint = f"\n\n💡 Hint: Try saying something like: {expected_answers[0]}"
                    wrong_reply += hint

                return {
                    "reply": wrong_reply,
                    "conversation_end": False,
                    "repeat_question": True,
                    "question_to_repeat": session_data.get("current_question", ""),
                    "validation_type": validation_type,
                    "allow_correction": allow_correction
                }

            # Réponse correcte
            session_data["current_attempts"] = 0
            session_data["current_step"] += 1
            current_step = session_data["current_step"]
            current_conv_index = session_data["current_conversation_index"]

            conversation = A1_CONVERSATIONS[current_conv_index]
            exchanges = conversation.get("exchanges", [])

            # Vérifier si la conversation est terminée
            if current_step > len(exchanges):
                # Passer à la conversation suivante
                session_data["current_conversation_index"] += 1
                session_data["current_step"] = 0
                session_data["current_attempts"] = 0
                session_data["waiting_for_answer"] = False
                session_data["current_question"] = None
                session_data["current_validation_type"] = None
                session_data["current_allow_correction"] = None
                session_data["current_accepted_topics"] = None
                session_data["current_expected_answers"] = None

                if session_data["current_conversation_index"] < len(A1_CONVERSATIONS):
                    next_conv = A1_CONVERSATIONS[session_data["current_conversation_index"]]
                    next_exchange = next_conv.get("exchanges", [])[0]
                    next_question = next_exchange.get("question", "")
                    next_title = next_conv.get('title', 'New Conversation')
                    next_validation_type = next_exchange.get("validation_type", "free")
                    next_expected_answers = next_exchange.get("expected_answers", [])

                    # Ajouter la prononciation de WEC-BEC dans le titre
                    if 'WEC-BEC' in next_title:
                        next_title = next_title.replace('WEC-BEC', 'WEC-BEC (wèk bèk)')

                    # Stocker les métadonnées de la prochaine question
                    session_data["current_validation_type"] = next_validation_type
                    session_data["current_allow_correction"] = next_exchange.get("allow_correction", True)
                    session_data["current_accepted_topics"] = next_exchange.get("accepted_topics", [])
                    session_data["current_expected_answers"] = next_expected_answers
                    session_data["current_good_reply"] = next_exchange.get("good_reply", "Good job! 👍")
                    session_data["current_wrong_reply"] = next_exchange.get("wrong_reply", "Try again!")

                    example = ""
                    if next_validation_type == "free" and "example_answer" in next_exchange:
                        example = f"\n\n💬 Example: {next_exchange['example_answer']}"
                    elif next_expected_answers and len(next_expected_answers) > 0:
                        example = f"\n\n💬 Example: {next_expected_answers[0]}"

                    session_data["waiting_for_answer"] = True
                    session_data["current_question"] = next_question

                    return {
                        "reply": f"{good_reply}\n\n✨ Great job! Let's move to a new topic. ✨\n\n📚 {next_title}\n{next_question}{example}",
                        "conversation_end": False,
                        "repeat_question": False,
                        "validation_type": next_validation_type,
                        "allow_correction": next_exchange.get("allow_correction", True)
                    }
                else:
                    session_data["waiting_for_answer"] = False
                    return {
                        "reply": f"{good_reply}\n\n🎉 Félicitations ! You have completed all A1 conversations! 🎉\n\nYou can now practice with the AI or move to A2 level.",
                        "conversation_end": True,
                        "repeat_question": False
                    }
            else:
                # Continuer avec la prochaine question de la même conversation
                next_exchange = exchanges[current_step - 1]
                next_question = next_exchange.get("question", "")
                next_validation_type = next_exchange.get("validation_type", "free")
                next_expected_answers = next_exchange.get("expected_answers", [])

                # Stocker les métadonnées
                session_data["current_validation_type"] = next_validation_type
                session_data["current_allow_correction"] = next_exchange.get("allow_correction", True)
                session_data["current_accepted_topics"] = next_exchange.get("accepted_topics", [])
                session_data["current_expected_answers"] = next_expected_answers
                session_data["current_good_reply"] = next_exchange.get("good_reply", "Good job! 👍")
                session_data["current_wrong_reply"] = next_exchange.get("wrong_reply", "Try again!")

                example = ""
                if next_validation_type == "free" and "example_answer" in next_exchange:
                    example = f"\n\n💬 Example: {next_exchange['example_answer']}"
                elif next_expected_answers and len(next_expected_answers) > 0:
                    example = f"\n\n💬 Example: {next_expected_answers[0]}"

                session_data["waiting_for_answer"] = True
                session_data["current_question"] = next_question

                return {
                    "reply": f"{good_reply}\n\n{next_question}{example}",
                    "conversation_end": False,
                    "repeat_question": False,
                    "validation_type": next_validation_type,
                    "allow_correction": next_exchange.get("allow_correction", True)
                }

        # Première visite ou reprise après reset
        current_conv_index = session_data["current_conversation_index"]
        current_step = session_data["current_step"]

        if current_conv_index >= len(A1_CONVERSATIONS):
            current_conv_index = 0
            session_data["current_conversation_index"] = 0
            session_data["current_step"] = 0
            current_step = 0

        conversation = A1_CONVERSATIONS[current_conv_index]
        exchanges = conversation.get("exchanges", [])

        if current_step < len(exchanges):
            current_exchange = exchanges[current_step]
            question = current_exchange.get("question", "")
            validation_type = current_exchange.get("validation_type", "free")
            expected_answers = current_exchange.get("expected_answers", [])
            accepted_topics = current_exchange.get("accepted_topics", [])
            allow_correction = current_exchange.get("allow_correction", True)

            # Stocker les métadonnées
            session_data["current_validation_type"] = validation_type
            session_data["current_allow_correction"] = allow_correction
            session_data["current_accepted_topics"] = accepted_topics
            session_data["current_expected_answers"] = expected_answers
            session_data["current_good_reply"] = current_exchange.get("good_reply", "Good job! 👍")
            session_data["current_wrong_reply"] = current_exchange.get("wrong_reply", "Try again!")

            example = ""
            if validation_type == "free" and "example_answer" in current_exchange:
                example = f"\n\n💬 Example: {current_exchange['example_answer']}"
            elif expected_answers and len(expected_answers) > 0:
                example = f"\n\n💬 Example: {expected_answers[0]}"

            intro_title = conversation.get('title', 'A1 Conversation')
            # Ajouter la prononciation de WEC-BEC dans le titre
            if 'WEC-BEC' in intro_title:
                intro_title = intro_title.replace('WEC-BEC', 'WEC-BEC (wèk bèk)')

            intro = f"📚 {intro_title}\n\n" if current_step == 0 else ""

            session_data["waiting_for_answer"] = True
            session_data["current_question"] = question
            session_data["current_step"] = current_step + 1

            return {
                "reply": f"{intro}{question}{example}",
                "conversation_end": False,
                "repeat_question": False,
                "validation_type": validation_type,
                "allow_correction": allow_correction
            }

        return None

    def get_hint(self, user_email):
        if user_email not in self.user_sessions:
            return None
        session_data = self.user_sessions[user_email]
        expected_answers = session_data.get("current_expected_answers", [])
        if expected_answers:
            return f"💡 Hint: Try saying: {expected_answers[0]}"
        return "💡 Hint: Listen carefully to the question and answer simply."

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

    def get_current_question_metadata(self, user_email):
        if user_email not in self.user_sessions:
            return None
        session_data = self.user_sessions[user_email]
        return {
            "validation_type": session_data.get("current_validation_type", "free"),
            "allow_correction": session_data.get("current_allow_correction", True),
            "accepted_topics": session_data.get("current_accepted_topics", []),
            "expected_answers": session_data.get("current_expected_answers", []),
            "good_reply": session_data.get("current_good_reply", "Good job! 👍"),
            "wrong_reply": session_data.get("current_wrong_reply", "Try again!"),
            "current_question": session_data.get("current_question", "")
        }


a1_manager = A1ConversationManager()

# =========================
# 🤖 OPENROUTER CONFIG
# =========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "meta-llama/llama-3-8b-instruct"


def ask_ai_with_context(message, student_level="B1", validation_type="free", allow_correction=True,
                        accepted_topics=None, current_question=""):
    try:
        level_prompts = {
            "A1": "Use very simple English with short sentences and basic vocabulary.",
            "A2": "Use very simple English with short sentences.",
            "B1": "Use intermediate English with natural conversations.",
            "B2": "Use fluent English with rich vocabulary.",
            "C1": "Use advanced fluent English, professional vocabulary, idioms.",
            "C2": "Use expert-level English with sophisticated vocabulary."
        }
        level_instruction = level_prompts.get(student_level, level_prompts["B1"])

        system_prompt = get_system_prompt(student_level, validation_type, allow_correction, accepted_topics)

        # Construire le message utilisateur avec contexte
        user_message = f"""
Current question: {current_question}
Student answer: {message}

Please evaluate the student's answer according to the rules.
Remember: WEC-BEC is pronounced 'wèk bèk'.
"""

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
                    {"role": "user", "content": user_message}
                ]
            }),
            timeout=45
        )
        if response.status_code != 200:
            logging.error(f"AI service error: {response.status_code} - {response.text}")
            return "AI service error. Try again later."
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"AI exception: {str(e)}")
        return "AI connection error."


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

        system_prompt = (
            f"You are WEC-BEC English Teacher AI. The student is at level {student_level}. {level_instruction} "
            "Be friendly, patient, and professional. Correct grammar politely. Ask only ONE question at a time.\n\n"
            "🔊 PRONUNCIATION RULE: WEC-BEC is pronounced 'wèk bèk'. "

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
            logging.error(f"AI service error: {response.status_code} - {response.text}")
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
            result = a1_manager.start_conversation(user_email)
            return jsonify({
                "reply": "🔄 Conversation restarted.\n\n" + result["reply"]
            })

        # Première ouverture du chat
        if user_email not in a1_manager.user_sessions:
            result = a1_manager.start_conversation(user_email)
            return jsonify({
                "reply": result["reply"]
            })

        # Si l'utilisateur dit juste bonjour
        if a1_manager.is_greeting(message):
            session_data = a1_manager.user_sessions.get(user_email)

            if not session_data.get("waiting_for_answer"):
                result = a1_manager.start_conversation(user_email)
                return jsonify({
                    "reply": result["reply"]
                })

        # Récupérer les métadonnées de la question courante
        metadata = a1_manager.get_current_question_metadata(user_email)

        if metadata:
            validation_type = metadata.get("validation_type", "free")
            allow_correction = metadata.get("allow_correction", True)
            accepted_topics = metadata.get("accepted_topics", [])
            current_question = metadata.get("current_question", "")

            # Utiliser l'IA pour évaluer la réponse
            ai_reply = ask_ai_with_context(
                message,
                student_level,
                validation_type,
                allow_correction,
                accepted_topics,
                current_question
            )

            # Si l'IA valide la réponse, passer à la question suivante
            result = a1_manager.get_next_question(user_email, message)

            if result and result.get("validation_type"):
                return jsonify({
                    "reply": ai_reply + "\n\n" + result.get("reply", "")
                })
            elif result:
                return jsonify({
                    "reply": result.get("reply", ai_reply)
                })
            else:
                return jsonify({
                    "reply": ai_reply
                })

        # Fallback: conversation normale sans IA
        result = a1_manager.get_next_question(user_email, message)
        return jsonify({
            "reply": result.get("reply", "Let's continue our English lesson!")
        })

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