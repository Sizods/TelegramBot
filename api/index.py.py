import requests
import pandas as pd
import io
import re

# Конфигурация
SPREADSHEET_ID = "1YrW7CcV4YURZjtNtZoXDiOmOUTtXqA_NxTDuwT0_nbU"  # ID вашей таблицы
TELEGRAM_TOKEN = "8080621408:AAFqJQYlHe7FgZKSd3P7Q82X6zi0betMWrE"  # Токен вашего бота
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Функция экранирования MarkdownV2
def escape_markdown_v2(text):
    """
    Экранирует специальные символы для Telegram MarkdownV2.
    """
    if not text:
        return ""
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!\\])', r'\\\1', str(text))

# Отправка сообщений в Telegram
def send_message(chat_id, text):
    url = f"{TELEGRAM_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "MarkdownV2"}
    try:
        response = requests.post(url, json=payload)
        print("Ответ API:", response.json())
    except Exception as e:
        print("Ошибка при отправке сообщения:", e)

# Обработка таблицы
def process_spreadsheet_data(chat_id):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&range=C4:G22"
        response = requests.get(url)

        if response.status_code != 200:
            send_message(chat_id, "Ошибка загрузки таблицы.")
            return

        df = pd.read_csv(io.StringIO(response.content.decode("utf-8-sig"))).dropna(how="all")
        today = pd.Timestamp.now()
        messages = []

        for _, row in df.iterrows():
            deadline_str = row.get("Дедлайн", "")
            if pd.notnull(deadline_str):
                deadline = pd.to_datetime(f"{deadline_str}.{today.year}", format="%d.%m.%Y", errors="coerce")
                if (deadline - today).days <= 3:
                    message = (
                        f"> 🎓 *Предмет*: {escape_markdown_v2(row.get('Предмет', 'Не указано'))}\n"
                        f"> 📖 *Тип*: {escape_markdown_v2(row.get('Тип пары', 'Не указано'))}\n"
                        f"> 📌 *Долг*: {escape_markdown_v2(row.get('Долги', 'Нет'))}\n\n"
                        f"> 🕒 Дедлайн: {escape_markdown_v2(deadline.strftime('%d.%m.%Y'))}\n"
                    )
                    messages.append(message)

        if messages:
            send_message(chat_id, "\n\n".join(messages))
        else:
            send_message(chat_id, "Нет данных для отправки.")
    except Exception as e:
        print("Ошибка при обработке данных:", e)
        send_message(chat_id, "Ошибка при обработке данных.")

# Основной цикл бота
def main():
    last_update_id = None
    while True:
        response = requests.get(f"{TELEGRAM_URL}/getUpdates", params={"offset": last_update_id, "timeout": 10}).json()
        for update in response.get("result", []):
            chat_id = update["message"]["chat"]["id"]
            command = update["message"]["text"].lower()
            if command == "/start":
                process_spreadsheet_data(chat_id)
            last_update_id = update["update_id"] + 1

if __name__ == "__main__":
    main()
