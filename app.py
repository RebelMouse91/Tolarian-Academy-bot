import os
import requests
from flask import Flask, request

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

MTG_KEYWORDS = [
    "mtg", "magic", "card", "deck", "commander",
    "mana", "spell", "creature", "planeswalker",
    "standard", "modern", "draft", "arena"
]

def is_mtg_related(text):
    text = text.lower()
    return any(word in text for word in MTG_KEYWORDS)

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })

def ask_openai(user_text):
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-5.3",
            "input": [
                {
                    "role": "system",
                    "content": "Ты эксперт по Magic: The Gathering. Отвечай кратко и только по теме MTG. Если вопрос не по теме — отвечай: 'Я отвечаю только по MTG.'"
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            "max_output_tokens": 150
        }
    )

    data = response.json()
    try:
        print(data)
return str(data)
    except:
        return "Ошибка ответа от ИИ"

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.json

    if "message" not in data:
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
    app.run(host="0.0.0.0", port=10000)
