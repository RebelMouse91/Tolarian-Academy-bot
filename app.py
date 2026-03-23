import os
import requests
from flask import Flask, request

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

MTG_KEYWORDS = [
    "mtg", "magic", "card", "deck", "commander",
    "mana", "spell", "creature", "planeswalker",
    "standard", "modern", "draft", "arena",
    "haste", "trample", "flying", "vigilance",
    "lifelink", "deathtouch", "hexproof"
]


def is_mtg_related(text):
    text = (text or "").lower()
    return any(word in text for word in MTG_KEYWORDS)


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": chat_id,
            "text": text[:4000]
        }, timeout=10)
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
                "input": f"Ты эксперт по MTG. Отвечай кратко.\n\n{user_text}",
                "max_output_tokens": 150
            },
            timeout=30
        )

        # если ошибка HTTP
        if response.status_code != 200:
            return f"Ошибка OpenAI: {response.text}"

        try:
            data = response.json()
        except:
            return "Ошибка: OpenAI вернул не JSON"

        # если API вернул ошибку
        if isinstance(data, dict) and "error" in data:
            return f"Ошибка OpenAI: {data['error'].get('message', 'неизвестная')}"

        # извлекаем текст безопасно
        output = data.get("output") or []

        texts = []
        for item in output:
            content = item.get("content") or []
            for block in content:
                if isinstance(block, dict):
                    txt = block.get("text")
                    if txt:
                        texts.append(txt)

        if texts:
            return "\n".join(texts)

        return "OpenAI вернул пустой ответ."

    except Exception as e:
        return f"Ошибка: {str(e)}"


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

    # реагируем только на упоминание или команду
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