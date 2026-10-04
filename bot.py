import os
import requests
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}"

client = genai.Client(api_key=GEMINI_API_KEY)


def get_business_connection(business_connection_id):
    response = requests.get(
        f"{telegram_url}/getBusinessConnection",
        params={
            "business_connection_id": business_connection_id
        },
        timeout=15
    )

    data = response.json()

    if data.get("ok"):
        return data.get("result")

    print("BUSINESS CONNECTION ERROR:", data)
    return None


def generate_reply(message):
    prompt = f"""
You are a personal AI assistant for the owner of this Telegram account.

You are NOT the account owner.
You must never pretend to be her or speak as if you are her.

Your role is to politely handle incoming messages when she is unavailable.

Rules:
- Make it clear that you are her personal assistant when appropriate.
- If someone wants to talk to her, say briefly that she is currently unavailable.
- Invite them to leave a message for her.
- You can tell them that you will pass their message to her.
- Do not claim to know where she is, what she is doing, or when she will return.
- Do not invent anything about her personal life.
- Never pretend that you are her.
- Never say things like "أنا موجودة" or "كنت مشغولة" as if you are the account owner.
- If someone jokes with you, you can respond warmly and naturally, but remain the assistant.
- Use Yemeni Arabic when appropriate.
- Keep replies short: usually 1–2 sentences.
- Avoid customer-service language.
- Do not repeatedly introduce yourself as an assistant if it is already clear.
- If someone leaves a message for her, acknowledge it briefly.
- Never reveal private information.

Incoming Telegram message:
{message}
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )

    return response.text.strip()


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


def notify_owner(user_chat_id, sender_name, message_text):
    notification = (
        f"📩 رسالة جديدة من {sender_name}\n\n"
        f"{message_text}"
    )

    response = requests.post(
        f"{telegram_url}/sendMessage",
        json={
            "chat_id": user_chat_id,
            "text": notification
        },
        timeout=15
    )

    print("OWNER NOTIFICATION:", response.text)


@app.get("/")
def home():
    return "Telegram AI bot is running!"


@app.post("/telegram-webhook")
def webhook():
    update = request.get_json(silent=True) or {}

    message = update.get("business_message")

    if not message:
        return jsonify({"ok": True})

    text = message.get("text")
    chat_id = message.get("chat", {}).get("id")
    business_connection_id = message.get("business_connection_id")

    if not text or not chat_id or not business_connection_id:
        return jsonify({"ok": True})

    try:
        business_connection = get_business_connection(
            business_connection_id
        )

        if not business_connection:
            return jsonify({"ok": True})

        owner_user = business_connection.get("user", {})
        owner_user_id = owner_user.get("id")
        owner_chat_id = business_connection.get("user_chat_id")

        sender = message.get("from", {})
        sender_id = sender.get("id")

        # Do not respond to messages sent by the account owner
        if sender_id == owner_user_id:
            return jsonify({"ok": True})

        # Get sender's name
        first_name = sender.get("first_name", "")
        last_name = sender.get("last_name", "")

        sender_name = f"{first_name} {last_name}".strip()

        if not sender_name:
            sender_name = "شخص"

        # Generate AI reply
        reply = generate_reply(text)

        if reply:
            send_reply(
                chat_id,
                reply,
                business_connection_id
            )

        # Notify the account owner
        if owner_chat_id:
            notify_owner(
                owner_chat_id,
                sender_name,
                text
            )

    except Exception as error:
        print("ERROR:", error)

    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)