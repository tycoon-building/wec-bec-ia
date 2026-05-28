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
# Dans un cas réel, cette information viendrait d'une base de données
STUDENT_LEVELS = {
    "student1@gmail.com": "A1",  # Élève A1 utilise le JSON
    "admin@wec-bec.com": "C1"  # Admin niveau avancé utilise l'IA
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


# Chargement des conversations A1 au démarrage
A1_CONVERSATIONS = load_a1_questions()


# =========================
# 🗣️ GESTIONNAIRE DE CONVERSATION A1 (VERSION AMÉLIORÉE)
# =========================
class A1ConversationManager:
    def __init__(self):
        self.user_sessions = {}  # stocke l'état de chaque utilisateur

    def check_answer(self, user_answer, expected_answers):
        """Vérifie si la réponse de l'utilisateur correspond aux réponses attendues"""
        user_answer_lower = user_answer.lower().strip()

        for expected in expected_answers:
            if expected.lower() in user_answer_lower:
                return True
        return False

    def get_next_question(self, user_email, user_answer=None):
        """Récupère la prochaine question ou réponse basée sur l'état de l'utilisateur"""

        # Initialiser la session utilisateur si nécessaire
        if user_email not in self.user_sessions:
            if A1_CONVERSATIONS:
                self.user_sessions[user_email] = {
                    "current_conversation_index": 0,
                    "current_step": 0,
                    "current_attempts": 0,  # Nombre de tentatives pour la question actuelle
                    "conversation_history": []
                }
            else:
                return None

        session_data = self.user_sessions[user_email]
        current_conv_index = session_data["current_conversation_index"]
        current_step = session_data["current_step"]
        current_attempts = session_data.get("current_attempts", 0)

        # Vérifier si on a des conversations disponibles
        if current_conv_index >= len(A1_CONVERSATIONS):
            # Recommencer depuis le début
            current_conv_index = 0
            session_data["current_conversation_index"] = 0
            session_data["conversation_history"] = []
            current_step = 0
            session_data["current_step"] = 0
            current_attempts = 0
            session_data["current_attempts"] = 0

        conversation = A1_CONVERSATIONS[current_conv_index]
        exchanges = conversation.get("exchanges", [])

        # Si l'utilisateur a répondu à quelque chose
        if user_answer is not None and current_step > 0:
            previous_exchange = exchanges[current_step - 1]
            expected_answers = previous_exchange.get("expected_answers", [])
            good_reply = previous_exchange.get("good_reply", "Good job! 👍")
            wrong_reply = previous_exchange.get("wrong_reply", "Try again!")

            # Vérifier la réponse
            is_correct = self.check_answer(user_answer, expected_answers)

            # Stocker l'historique
            session_data["conversation_history"].append({
                "question": previous_exchange.get("question", ""),
                "user_answer": user_answer,
                "expected_answers": expected_answers,
                "is_correct": is_correct,
                "attempts": current_attempts + 1
            })

            if not is_correct:
                # Réponse incorrecte: incrémenter les tentatives et répéter la question
                session_data["current_attempts"] = current_attempts + 1

                # Ajouter un petit conseil si l'utilisateur a déjà essayé plusieurs fois
                if current_attempts >= 2:
                    hint = f"\n\n💡 Petit conseil: Essayez de dire: {expected_answers[0]}..."
                    wrong_reply += hint

                return {
                    "reply": wrong_reply,
                    "conversation_end": False,
                    "repeat_question": True,
                    "question_to_repeat": previous_exchange.get("question", "")
                }

            # Réponse correcte: réinitialiser les tentatives et passer à l'étape suivante
            session_data["current_attempts"] = 0
            current_step += 1
            session_data["current_step"] = current_step

            # Vérifier si la conversation est terminée
            if current_step > len(exchanges):
                # Passer à la conversation suivante
                session_data["current_conversation_index"] += 1
                session_data["current_step"] = 0
                session_data["current_attempts"] = 0
                session_data["conversation_history"] = []

                # Vérifier s'il y a une prochaine conversation
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
                    # Fin de toutes les conversations
                    return {
                        "reply": f"{good_reply}\n\n🎉 Félicitations ! Vous avez terminé toutes les conversations pour le niveau A1 ! 🎉\n\nVous pouvez maintenant pratiquer avec l'IA ou passer au niveau A2. Tapez 'menu' pour voir vos options.",
                        "conversation_end": True,
                        "repeat_question": False
                    }
            else:
                # Continuer avec la prochaine question
                next_exchange = exchanges[current_step - 1]
                next_question = next_exchange.get("question", "")
                return {
                    "reply": f"{good_reply}\n\n{next_question}",
                    "conversation_end": False,
                    "repeat_question": False
                }

        # Retourner la question actuelle (première fois ou après correction)
        if current_step < len(exchanges):
            current_exchange = exchanges[current_step]
            question = current_exchange.get("question", "")
            expected_answers = current_exchange.get("expected_answers", [])

            # Ajouter un message d'introduction pour la première question
            if current_step == 0:
                intro = f"📚 {conversation.get('title', 'Conversation A1')}\n\n"
                # Ajouter un exemple de réponse si disponible
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
                # Pour les questions suivantes, ajouter un exemple si l'utilisateur n'a pas encore essayé
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
        """Réinitialise la progression d'un utilisateur A1"""
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
        """Donne un indice pour la question actuelle"""
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
        """Retourne la progression de l'utilisateur"""
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


# Initialiser le gestionnaire A1
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
# 🧠 AI FUNCTION (POUR A2 ET PLUS)
# =========================
def ask_ai(message, student_level="B1"):
    try:
        # Adapter le prompt selon le niveau
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
    # Nettoyer la session A1 si nécessaire
    user_email = session.get("user")
    if user_email:
        # Optionnel: sauvegarder la progression avant déconnexion
        pass

    session.clear()
    return redirect("/login")


# =========================
# 💬 CHAT API (MODIFIÉ POUR A1)
# =========================
@app.route("/chat", methods=["POST"])
def chat():
    if not session.get("user"):
        return jsonify({"reply": "Not authorized"}), 403

    data = request.json or {}
    message = data.get("message", "").strip()
    reset = data.get("reset", False)  # Option pour réinitialiser la conversation A1

    if not message and not reset:
        return jsonify({"reply": "Empty message"}), 400

    user_email = session["user"]
    student_level = STUDENT_LEVELS.get(user_email, "B1")

    # Cas spécial: commande "menu" pour les A1
    if message.lower() == "menu" and student_level == "A1":
        progress = a1_manager.get_progress(user_email)
        if progress:
            menu_text = (
                f"📊 **Votre progression A1**:\n"
                f"📚 {progress['conversation_title']}\n"
                f"Conversation {progress['current_conversation']}/{progress['total_conversations']}\n"
                f"Question {progress['current_step'] + 1}/{progress['total_steps_in_current']}\n"
                f"Progression totale: {progress['progress_percent']:.1f}%\n"
                f"Tentatives sur la question actuelle: {progress['current_attempts']}\n\n"
                f"Commandes disponibles:\n"
                f"- Tapez 'reset' pour recommencer du début\n"
                f"- Tapez 'menu' pour voir ce menu\n"
                f"- Tapez 'hint' pour obtenir un indice\n"
                f"- Répondez normalement pour continuer la conversation\n\n"
                f"Souhaitez-vous continuer ou recommencer ?"
            )
            return jsonify({"reply": menu_text})
        else:
            return jsonify({"reply": "Aucune conversation A1 chargée. Veuillez vérifier le fichier JSON."})

    # Cas spécial: hint pour A1
    if message.lower() == "hint" and student_level == "A1":
        hint = a1_manager.get_hint(user_email)
        if hint:
            return jsonify({"reply": hint})
        else:
            return jsonify({"reply": "Aucun indice disponible pour le moment."})

    # Cas spécial: reset pour A1
    if message.lower() == "reset" and student_level == "A1":
        if a1_manager.reset_user(user_email):
            first_question = A1_CONVERSATIONS[0].get("exchanges", [{}])[0].get("question",
                                                                               "Commencez par vous présenter.")
            expected = A1_CONVERSATIONS[0].get("exchanges", [{}])[0].get("expected_answers", [])
            example = f"\n\n💬 Exemple: {expected[0]}" if expected else ""
            return jsonify({
                               "reply": f"🔄 Conversation réinitialisée ! Recommençons depuis le début.\n\n📚 {A1_CONVERSATIONS[0].get('title', 'Conversation A1')}\n\n{first_question}{example}"})
        else:
            return jsonify({"reply": "Impossible de réinitialiser. Veuillez réessayer."})

    # Pour les étudiants A1: utiliser le JSON
    if student_level == "A1":
        # Si c'est un reset explicite par le système
        if reset:
            a1_manager.reset_user(user_email)

        # Obtenir la prochaine question/réponse
        result = a1_manager.get_next_question(user_email, message if not reset else None)

        if result is None:
            # Fallback à l'IA si le JSON n'est pas disponible
            reply = ask_ai(message, "A1")
        else:
            reply = result["reply"]

            # Si la question doit être répétée, on pourrait logger quelque chose
            if result.get("repeat_question"):
                logging.info(f"Répétition de la question pour {user_email}")

            # Ajouter un message si la conversation est terminée
            if result.get("conversation_end"):
                # Option: réinitialiser automatiquement après la fin
                pass

        return jsonify({"reply": reply})

    # Pour les autres niveaux: utiliser l'IA normalement
    else:
        reply = ask_ai(message, student_level)
        return jsonify({"reply": reply})


# =========================
# 📊 API POUR OBTENIR LA PROGRESSION A1
# =========================
@app.route("/a1/progress", methods=["GET"])
def get_a1_progress():
    if not session.get("user"):
        return jsonify({"error": "Not authorized"}), 403

    user_email = session["user"]
    student_level = STUDENT_LEVELS.get(user_email, "B1")

    if student_level != "A1":
        return jsonify({"error": "Cette fonction est réservée aux étudiants A1"}), 400

    progress = a1_manager.get_progress(user_email)
    if progress:
        return jsonify(progress)
    else:
        return jsonify({"error": "Aucune progression trouvée"}), 404


# =========================
# 📚 ROUTE POUR CHARGER/RELOAD LE JSON A1
# =========================
@app.route("/admin/reload-a1", methods=["POST"])
def reload_a1():
    """Route admin pour recharger le fichier JSON sans redémarrer le serveur"""
    if not session.get("user") or session["user"] != "admin@wec-bec.com":
        return jsonify({"error": "Admin only"}), 403

    global A1_CONVERSATIONS
    A1_CONVERSATIONS = load_a1_questions()

    return jsonify({
        "status": "success",
        "conversations_loaded": len(A1_CONVERSATIONS)
    })


# =========================
# loading json file
# =========================
@app.route("/courses")
def courses():
    with open("data/courses.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


# =========================
# 🚀 RUN SERVER
# =========================
if __name__ == "__main__":
    app.run(
        debug=False,
        host="0.0.0.0",
        port=5000
    )