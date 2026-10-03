import os
import requests
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

ai = genai.Client(api_key=GEMINI_API_KEY)


def generate_ai_reply(user_message):
    prompt = f"""
You are an AI assistant replying on behalf of a woman on her personal Telegram account.

Reply naturally and warmly, like a real person.
Do not say that you are an AI unless directly asked.
Keep replies concise and conversational.
Do not invent personal information about the account owner.

Message received:
{user_message}
"""

    response = ai.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    return response.text.strip()


def send_message(chat_id, text, business_connection_id):
    url = f"{TELEGRAM_API}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": text,
        "business_connection_id": business_connection_id
    }

    requests.post(url, json=data, timeout=30)


@app.route("/")
def home():
    return "Telegram AI bot is running!"


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True) or {}

    message = update.get("business_message")

    if not message:
        return jsonify({"ok": True})

    text = message.get("text")

    if not text:
        return jsonify({"ok": True})

    chat = message.get("chat", {})
    chat_id = chat.get("id")

    business_connection_id = message.get("business_connection_id")

    if not chat_id or not business_connection_id:
        return jsonify({"ok": True})

    try:
        reply = generate_ai_reply(text)

        if reply:
            send_message(
                chat_id,
                reply,
                business_connection_id
            )

    except Exception as e:
        print("ERROR:", e)

    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
