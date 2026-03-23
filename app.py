import os
import requests
from flask import Flask, request, jsonify

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

MTG_KEYWORDS = [
    "mtg", "magic", "card", "deck", "commander",
    "mana", "spell", "creature", "planeswalker",
    "standard", "modern", "draft", "arena",
    "haste", "trample", "flying", "vigilance",
    "lifelink", "deathtouch", "hexproof", "indestructible",
    "scry", "draw", "discard", "token", "counter",
    "land", "artifact", "enchantment", "instant", "sorcery"
]


def is_mtg_related(text: str) -> bool:
    text = (text or "").lower()
    return any(word in text for word in MTG_KEYWORDS)


def send_message(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text[:4000],  # Telegram limit safety
        },
        timeout=20,
    )


def extract_response_text(data: dict) -> str:
    # 1) Самый удобный случай
    if data.get("output_text"):
        return data["output_text"].strip()

    # 2) Разбор стандартной структуры Responses API
    output = data.get("output", [])
    parts = []

    for item in output:
        content = item.get("content", [])
        for block in content:
            if block.get("type") == "output_text" and block.get("text"):
                parts.append(block["text"])
            elif block.get("type") == "text" and block.get("text"):
                parts.append(block["text"])

    text = "\n".join(parts).strip()
    if text:
        return text

    return ""


def ask_openai(user_text: str) -> str:
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4.1-mini",
                "instructions": (
                    "Ты помощник только по Magic: The Gathering. "
                    "Отвечай кратко, точно и только по теме MTG. "
                    "Если вопрос не про MTG, отвечай: 'Я отвечаю только по MTG.'"
                ),
                "input": user_text,
                "max_output_tokens": 150,
            },
            timeout=45,
        )

        # Если OpenAI вернул 4xx/5xx — покажем реальную ошибку
        if not response.ok:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
            except Exception:
                error_msg = response.text
            return f"Ошибка OpenAI: {error_msg}"

        data = response.json()

        # Если API вернул error в JSON
        if "error" in data:
            return f"Ошибка OpenAI: {data['error'].get('message', 'неизвестная ошибка')}"

        text = extract_response_text(data)
        if text:
            return text

        return "OpenAI вернул пустой ответ."

    except requests.Timeout:
        return "Ошибка OpenAI: превышено время ожидания."
    except Exception as e:
        return f"Ошибка запроса: {str(e)}"


@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200


@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    if not BOT_TOKEN or not OPENAI_API_KEY:
        return jsonify({"ok": False, "error": "Missing BOT_TOKEN or OPENAI_API_KEY"}), 500

    data = request.get_json(silent=True) or {}

    if "message" not in data:
        return "ok", 200

    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "") or ""

    # Отвечаем только на упоминание бота или на /mtg
    if "@RebelMouse_bot" not in text and not text.startswith("/mtg"):
        return "ok", 200

    if not is_mtg_related(text):
        send_message(chat_id, "Я отвечаю только по MTG.")
        return "ok", 200

    answer = ask_openai(text)
    send_message(chat_id, answer)

    return "ok", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)