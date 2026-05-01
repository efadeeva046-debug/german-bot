import telebot
import requests
import json
import schedule
import time
import threading
from datetime import datetime, timedelta
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = "8664007998:AAGHIiHvIqNpJ4pCh6y4vrkzv3CsBTZqqYY"
ROUTER_KEY = "sk_7157b9a008702929fd9469d2fb9820d2be639e23a12dfcf1ea8903883947648e"
YOUR_TELEGRAM_ID = 1135980604
# ===============================

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Хранилище
user_data = {}
user_dialog = {}
spring_exercise = {}

# === ФРАЗЫ ПОХВАЛЫ ===
PRAISE_PHRASES = [
    "✅ Sehr gut!", "✅ Wunderbar!", "✅ Exzellent!",
    "✅ Prima gemacht!", "✅ Toll!", "✅ Fantastisch!",
    "✅ Du lernst schnell!", "✅ Gute Arbeit!",
    "✅ Perfekt!", "✅ Weiter so!", "✅ Spitze!",
    "✅ Klasse!", "✅ Großartig!"
]

def random_praise():
    return random.choice(PRAISE_PHRASES)

# === КНОПКИ ГЛАВНОГО МЕНЮ ===
def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📖 Темы", callback_data="show_themes"),
        InlineKeyboardButton("🏥 Диалог с врачом", callback_data="dialog_health"),
        InlineKeyboardButton("🌸 Весна", callback_data="spring"),
        InlineKeyboardButton("📝 Задать домашку", callback_data="set_hw"),
        InlineKeyboardButton("📚 Моя домашка", callback_data="show_hw"),
        InlineKeyboardButton("❓ Помощь", callback_data="help")
    )
    return keyboard

# === КНОПКИ ТЕМ ===
def topics_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📖 Lektion 1: Знакомство", callback_data="topic_Lektion1"),
        InlineKeyboardButton("🏥 Lektion 22: Gesundheit", callback_data="topic_Lektion22"),
        InlineKeyboardButton("💬 Lektion 22: Диалог", callback_data="topic_Dialog"),
        InlineKeyboardButton("🌸 Весна: 5 предложений", callback_data="topic_Spring")
    )
    return keyboard

# === ОБРАБОТКА КНОПОК ===
@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    if call.data == "show_themes":
        bot.edit_message_text("📚 Выбери тему:", call.message.chat.id, call.message.message_id, reply_markup=topics_keyboard())
    
    elif call.data == "dialog_health":
        bot.answer_callback_query(call.id)
        start_dialog_health(call.message)
    
    elif call.data == "spring":
        bot.answer_callback_query(call.id)
        start_spring(call.message)
    
    elif call.data == "set_hw":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📝 Формат: /hw вторник 5 предложений о погоде Выучи фразы")
    
    elif call.data == "show_hw":
        bot.answer_callback_query(call.id)
        show_homework(call.message)
    
    elif call.data == "help":
        bot.answer_callback_query(call.id)
        help_cmd(call.message)
    
    elif call.data == "menu":
        bot.edit_message_text("🇩🇪 *Главное меню*\n\nВыбери действие:", call.message.chat.id, call.message.message_id, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    
    elif call.data.startswith("topic_"):
        topic = call.data.replace("topic_", "")
        if topic == "Lektion1":
            user_data[call.message.chat.id] = {"topic": "Lektion 1: Vorstellung", "topic_rules": "Приветствия: Guten Tag, Hallo, Tschüs\n\nГлаголы: ich mache, du machst\n\nSein: ich bin, du bist\n\nЧисла: eins, zwei, drei\n\nФразы: Ich heiße... Ich komme aus..."}
        elif topic == "Lektion22":
            user_data[call.message.chat.id] = {"topic": "Lektion 22: Gesundheit", "topic_rules": "dürfen (разрешение): ich darf, du darfst\nsollen (совет): ich soll, du sollst\n\nСлова: der Schmerz, der Husten, die Grippe, das Fieber\n\nФразы: Was fehlt Ihnen? Mein Rücken tut weh."}
        elif topic == "Dialog":
            user_data[call.message.chat.id] = {"topic": "Диалог у врача", "topic_rules": "Реплики врача и пациента. Спрашивай и отвечай по-немецки."}
        elif topic == "Spring":
            user_data[call.message.chat.id] = {"topic": "Весна", "topic_rules": "5 предложений о погоде"}
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"✅ Тема установлена: {user_data[call.message.chat.id]['topic']}\n\nТеперь пиши предложения — я проверю!")

# === ДИАЛОГ С ПРОПУСКАМИ ===
DIALOG_HEALTH = [
    {"speaker": "Arzt", "text": "Guten Tag, Frau Rathke!", "gap": None, "expected": None},
    {"speaker": "Patientin", "text": "Guten Tag, Herr ___!", "gap": "Doktor", "expected": "Doktor"},
    {"speaker": "Arzt", "text": "Was fehlt Ihnen denn?", "gap": None, "expected": None},
    {"speaker": "Patientin", "text": "Mein ___ tut so weh.", "gap": "Rücken", "expected": "Rücken"},
    {"speaker": "Arzt", "text": "Seit wann haben Sie die Schmerzen?", "gap": None, "expected": None},
    {"speaker": "Patientin", "text": "Seit zwei, drei ___", "gap": "Wochen", "expected": "Wochen"},
    {"speaker": "Arzt", "text": "Haben Sie etwas Schweres gehoben?", "gap": None, "expected": None},
    {"speaker": "Patientin", "text": "Nein. Ich weiß nicht, warum ich ___ habe.", "gap": "Rückenschmerzen", "expected": "Rückenschmerzen"},
    {"speaker": "Arzt", "text": "Was sind Sie von Beruf?", "gap": None, "expected": None},
    {"speaker": "Patientin", "text": "___", "gap": "Sekretärin", "expected": "Sekretärin"},
    {"speaker": "Arzt", "text": "Und da sitzen Sie wahrscheinlich viel. Treiben Sie Sport?", "gap": None, "expected": None},
    {"speaker": "Patientin", "text": "Ich möchte schon mehr Sport machen, aber viel ___ bleibt nicht.", "gap": "Zeit", "expected": "Zeit"},
    {"speaker": "Arzt", "text": "Dann sollten Sie viel schwimmen und spazieren gehen.", "gap": None, "expected": None},
    {"speaker": "Patientin", "text": "Ja, ich werde es ___", "gap": "versuchen", "expected": "versuchen"},
    {"speaker": "Arzt", "text": "Kommen Sie in zwei Wochen wieder. Gute Besserung!", "gap": None, "expected": None},
    {"speaker": "Patientin", "text": "___", "gap": "Danke", "expected": "Danke"}
]

def start_dialog_health(message):
    user_dialog[message.chat.id] = {"step": 0, "mode": "health"}
    send_next_dialog_line(message.chat.id)

def send_next_dialog_line(chat_id):
    step = user_dialog[chat_id]["step"]
    if step >= len(DIALOG_HEALTH):
        bot.send_message(chat_id, "🎉 Поздравляю! Ты прошла весь диалог!\n\n/menu - главное меню")
        user_dialog.pop(chat_id, None)
        return
    line = DIALOG_HEALTH[step]
    speaker = "👨‍⚕️ Врач" if line["speaker"] == "Arzt" else "👩‍🦰 Пациентка"
    if line["gap"]:
        text = line["text"].replace("___", f"_____")
        bot.send_message(chat_id, f"{speaker}: {text}\n\n✏️ Напиши пропущенное слово:")
    else:
        bot.send_message(chat_id, f"{speaker}: {line['text']}")
        user_dialog[chat_id]["step"] += 1
        send_next_dialog_line(chat_id)

# === ВЕСНА ===
SPRING_SENTENCES = [
    {"ru": "Солнце светит", "de": "Die Sonne scheint."},
    {"ru": "Тепло", "de": "Es ist warm."},
    {"ru": "Цветы цветут", "de": "Die Blumen blühen."},
    {"ru": "Небо голубое", "de": "Der Himmel ist blau."},
    {"ru": "Птицы поют", "de": "Die Vögel singen."}
]

def start_spring(message):
    current = random.choice(SPRING_SENTENCES)
    spring_exercise[message.chat.id] = current
    bot.send_message(message.chat.id, f"🌸 Переведи на немецкий:\n\n\"{current['ru']}\"\n\n(Для нового нажми /spring)")

# === КОМАНДЫ ===
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(message.chat.id,
        "🇩🇪 *Hallo! Я твой репетитор немецкого!*\n\n"
        "Нажми на кнопку 👇",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown")

@bot.message_handler(commands=['menu'])
def menu_cmd(message):
    bot.send_message(message.chat.id,
        "🇩🇪 *Главное меню*",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown")

@bot.message_handler(commands=['themes'])
def themes_cmd(message):
    bot.send_message(message.chat.id, "📚 *Выбери тему:*", reply_markup=topics_keyboard(), parse_mode="Markdown")

@bot.message_handler(commands=['spring'])
def spring_cmd(message):
    start_spring(message)

@bot.message_handler(commands=['dialog_health'])
def dialog_cmd(message):
    start_dialog_health(message)

@bot.message_handler(commands=['hw'])
def set_hw(message):
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        bot.send_message(message.chat.id, "📝 /hw [день] [что учить] [подсказка]\nПример: /hw вторник 5 предложений о погоде Выучи фразы")
        return
    user_data[message.chat.id] = user_data.get(message.chat.id, {})
    user_data[message.chat.id]["homework"] = {"what": parts[2], "deadline": parts[1], "hint": parts[3]}
    bot.send_message(message.chat.id, f"✅ Домашка задана до {parts[1]}: {parts[2]}")

def show_homework(message):
    if message.chat.id in user_data and "homework" in user_data[message.chat.id]:
        hw = user_data[message.chat.id]["homework"]
        bot.send_message(message.chat.id, f"📚 Домашка: {hw['what']}\nДо: {hw['deadline']}\nПодсказка: {hw['hint']}")
    else:
        bot.send_message(message.chat.id, "Нет активной домашки. /hw чтобы задать")

@bot.message_handler(commands=['homework'])
def homework_cmd(message):
    show_homework(message)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(message.chat.id,
        "📖 *Команды:*\n"
        "/menu - главное меню\n"
        "/themes - выбрать тему\n"
        "/dialog_health - диалог с врачом\n"
        "/spring - весенние предложения\n"
        "/hw - задать домашку\n"
        "/homework - показать домашку\n"
        "/enddialog - выйти из диалога",
        parse_mode="Markdown")

@bot.message_handler(commands=['enddialog'])
def end_dialog(message):
    if message.chat.id in user_dialog:
        user_dialog.pop(message.chat.id)
    bot.send_message(message.chat.id, "🎭 Режим диалога завершён.")

# === ДЛЯ ТЕМ ===
@bot.message_handler(commands=['theme'])
def theme_cmd(message):
    themes_cmd(message)

@bot.message_handler(commands=['topic'])
def topic_cmd(message):
    if message.chat.id in user_data and "topic" in user_data[message.chat.id]:
        bot.send_message(message.chat.id, f"📖 Твоя тема: {user_data[message.chat.id]['topic']}")
    else:
        bot.send_message(message.chat.id, "Тема не выбрана. Нажми /themes")

# === РАССЫЛКА ДОМАШКИ (Только для админа) ===
ADMIN_ID = YOUR_TELEGRAM_ID  # Твой ID (кто может делать рассылку)

# Храним всех, кто писал боту
known_users = set()

@bot.message_handler(func=lambda message: True)
def track_users(message):
    """Запоминаем всех, кто написал боту"""
    known_users.add(message.chat.id)

@bot.message_handler(commands=['announce'])
def announce_homework(message):
    """Отправляет домашку всем пользователям (только админу)"""
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Только администратор может делать рассылку.")
        return
    
    # Берём текст после команды /announce
    text = message.text.replace("/announce", "").strip()
    if not text:
        bot.send_message(message.chat.id, "📝 Напиши домашку после /announce\nПример: /announce Учить диалог на стр.45 до вторника")
        return
    
    # Отправляем всем
    success = 0
    fail = 0
    for user_id in known_users:
        try:
            bot.send_message(user_id, 
                f"📚 *НОВОЕ ДОМАШНЕЕ ЗАДАНИЕ!* 📚\n\n{text}\n\n🇩🇪 Viel Erfolg!",
                parse_mode="Markdown")
            success += 1
        except:
            fail += 1
    
    bot.send_message(message.chat.id, f"✅ Домашка отправлена {success} пользователям.\n❌ Не доставлено: {fail}")

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    """Показывает количество пользователей (только админу)"""
    if message.chat.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, f"📊 Всего пользователей: {len(known_users)}")

# === ПРОВЕРКА ЗАДАНИЙ ===
@bot.message_handler(func=lambda message: True)
def check_homework(message):
    chat_id = message.chat.id
    
    if chat_id in user_dialog:
        step = user_dialog[chat_id]["step"]
        line = DIALOG_HEALTH[step]
        if line["gap"]:
            expected = line["expected"]
            if message.text.strip().lower() == expected.lower():
                bot.send_message(chat_id, f"✅ {expected}! Правильно!")
                user_dialog[chat_id]["step"] += 1
                send_next_dialog_line(chat_id)
            else:
                bot.send_message(chat_id, f"❌ Неверно. Правильно: {expected}. Попробуй ещё раз.")
        return
    
    if chat_id in spring_exercise:
        expected = spring_exercise[chat_id]["de"]
        if message.text.strip().lower() == expected.lower():
            bot.send_message(chat_id, f"✅ {random_praise()}\n\nНовое предложение: /spring")
            spring_exercise.pop(chat_id)
        else:
            bot.send_message(chat_id, f"❌ Неверно. Правильно: {expected}\nПопробуй ещё раз.")
        return
    
    bot.send_message(chat_id, "Выбери действие в меню: /menu")

# === ПОСТОЯННОЕ МЕНЮ ВНИЗУ ===
def set_main_menu():
    commands = [
        telebot.types.BotCommand("menu", "🏠 Главное меню"),
        telebot.types.BotCommand("themes", "📖 Темы"),
        telebot.types.BotCommand("dialog_health", "🏥 Диалог с врачом"),
        telebot.types.BotCommand("spring", "🌸 Весна"),
        telebot.types.BotCommand("hw", "📝 Задать домашку"),
        telebot.types.BotCommand("homework", "📚 Моя домашка"),
        telebot.types.BotCommand("help", "❓ Помощь"),
        telebot.types.BotCommand("enddialog", "🎭 Выйти из диалога")
    ]
    bot.set_my_commands(commands)

# === ЗАПУСК ===
if __name__ == "__main__":
    set_main_menu()
    print("✅ Бот запущен! Нажми /menu в Telegram")
    bot.infinity_polling()
