import os
import requests
from flask import Flask, request

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

MTG_KEYWORDS = [
    "mtg", "magic", "card", "deck", "commander",
    "mana", "spell", "creature", "planeswalker",
    "haste", "trample", "flying", "vigilance",
    "lifelink", "deathtouch"
]


def is_mtg_related(text):
    if not text:
        return False
    text = text.lower()
    return any(word in text for word in MTG_KEYWORDS)


def send_message(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": str(text)[:4000]},
            timeout=10
        )
    except:
        pass


def ask_openai(user_text):
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4.1-mini",
                "input": user_text,
                "max_output_tokens": 150
            },
            timeout=30
        )

        if response.status_code != 200:
            return f"OpenAI error: {response.text}"

        data = response.json()

        # ✅ ПРАВИЛЬНЫЙ способ получения текста
        if isinstance(data, dict) and "output_text" in data:
            if data["output_text"]:
                return data["output_text"]

        # 🔁 fallback (если другой формат)
        try:
            return data["output"][0]["content"][0]["text"]
        except:
            return f"Не удалось разобрать ответ: {data}"

    except Exception as e:
        return f"Ошибка запроса: {str(e)}"


@app.route("/", methods=["GET"])
def home():
    return "Bot is running"


@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.json

    if not data or "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # отвечаем только на упоминание или /mtg
    if "@RebelMouse_bot" not in text and not text.startswith("/mtg"):
        return "ok"

    if not is_mtg_related(text):
        send_message(chat_id, "Я отвечаю только по MTG.")
        return "ok"

    answer = ask_openai(text)
    send_message(chat_id, answer)

    return "ok"


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)