from flask import Flask, request
import requests
import pandas as pd
import io
import re

app = Flask(__name__)

# Конфигурация
SPREADSHEET_ID = "1YrW7CcV4YURZjtNtZoXDiOmOUTtXqA_NxTDuwT0_nbU"  # Замените на ваш ID таблицы Google
TELEGRAM_TOKEN = "8080621408:AAFqJQYlHe7FgZKSd3P7Q82X6zi0betMWrE"  # Замените на ваш токен Telegram
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Функция экранирования MarkdownV2
def escape_markdown_v2(text):
    if not text:
        return ""
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!\\])', r'\\\1', str(text))

# Отправка сообщения в Telegram
def send_message(chat_id, text):
    url = f"{TELEGRAM_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "MarkdownV2"}
    try:
        response = requests.post(url, json=payload)
        print("Ответ Telegram API:", response.json())  # Логируем ответ Telegram
    except Exception as e:
        print("Ошибка при отправке сообщения:", e)

# Обработка данных из Google Sheets
def process_spreadsheet_data(chat_id):
    try:
        # Формируем URL для загрузки таблицы
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&range=C4:G22"
        response = requests.get(url)

        # Проверяем статус загрузки
        if response.status_code != 200:
            send_message(chat_id, "Ошибка загрузки таблицы. Проверьте доступ.")
            print(f"Ошибка загрузки таблицы, статус: {response.status_code}")
            return

        # Читаем и обрабатываем таблицу
        df = pd.read_csv(io.StringIO(response.content.decode("utf-8-sig"))).dropna(how="all")
        today = pd.Timestamp.now()
        messages = []

        for _, row in df.iterrows():
            deadline_str = row.get("Дедлайн", "")
            if pd.notnull(deadline_str):
                deadline = pd.to_datetime(f"{deadline_str}.{today.year}", format="%d.%m.%Y", errors="coerce")
                if pd.notnull(deadline) and (deadline - today).days <= 3:
                    message = (
                        f"*Предмет*: {escape_markdown_v2(row.get('Предмет', 'Не указано'))}\n"
                        f"*Тип*: {escape_markdown_v2(row.get('Тип пары', 'Не указано'))}\n"
                        f"*Долг*: {escape_markdown_v2(row.get('Долги', 'Нет'))}\n"
                        f"*Дедлайн*: {escape_markdown_v2(deadline.strftime('%d.%m.%Y'))}\n"
                    )
                    messages.append(message)

        # Отправляем результаты или сообщение о пустых данных
        if messages:
            send_message(chat_id, "\n\n".join(messages))
        else:
            send_message(chat_id, "Нет актуальных данных для отображения.")
    except Exception as e:
        print("Ошибка при обработке таблицы:", e)
        send_message(chat_id, "Произошла ошибка при обработке данных.")

# Обработчик Webhook
@app.route("/", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json()
        print("Полученные данные от Telegram:", data)  # Логируем входящие данные

        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            command = data["message"]["text"].lower()
            print(f"Чат ID: {chat_id}, Команда: {command}")

            if command == "/start":
                send_message(chat_id, "Добро пожаловать! Сейчас обработаю ваши данные...")
                process_spreadsheet_data(chat_id)
            else:
                send_message(chat_id, "Неизвестная команда. Попробуйте /start.")

        return "OK", 200
    except Exception as e:
        print("Ошибка в обработке Webhook:", e)
        return "Internal Server Error", 500

if __name__ == "__main__":
    app.run(debug=True)
