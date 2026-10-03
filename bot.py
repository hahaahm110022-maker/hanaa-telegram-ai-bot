import os
import requests
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}"

client = genai.Client(api_key=GEMINI_API_KEY)


def get_ai_reply(message):
    prompt = f"""
You are an assistant replying on behalf of the Telegram account owner.

Reply naturally, warmly, and briefly.
Sound like a real person.
Do not claim to be the account owner.
Do not invent personal information.

Incoming message:
{message}
"""

    response = client.interactions.create(
        model="gemini-3.8-flash",
        input=prompt
    )

    return response.output_text.strip()


def send_reply(chat_id, text, business_connection_id):
    requests.post(
        f"{telegram_url}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "business_connection_id": business_connection_id
        },
        timeout=30
    )


@app.route("/", methods=["GET"])
def home():
    return "Telegram AI bot is running!"


@app.route("/telegram-webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}

    message = update.get("business_message")

    if not message:
        return jsonify({"ok": True})

    text = message.get("text")
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    business_connection_id = message.get("business_connection_id")

    if not text or not chat_id or not business_connection_id:
        return jsonify({"ok": True})

    try:
        reply = get_ai_reply(text)

        if reply:
            send_reply(
                chat_id,
                reply,
                business_connection_id
            )

    except Exception as error:
        print("ERROR:", error)

    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
