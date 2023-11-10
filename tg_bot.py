import telebot
from telebot import types
import modules.localization as localization
import os
import requests
import sqlite3
from datetime import datetime


# Отримання та створення об'єкту бота
token = os.environ.get('BOT_TOKEN')
if token is None:
    print("Bot Token:")
    token = input()

# API MyAnimeList
an_token = os.environ.get('YOUR_TOKEN')
if an_token is None:
    print("MyAnimeList Token:")
    an_token = input()
    
bot = telebot.TeleBot(token)

conn = sqlite3.connect('my_database.db')

# Шлях до локальних файлів
LOCALES_PATH = '/SearchAnime_TelegramBot/locales/'

# Збереження мов користувача та локалізацій
user_languages = {}
loaded_localizations = localization.load_localization()

# Змінна станів для кожного користувача
user_in_language_change_mode = {}

user_in_search_anime_mode = {}

user_in_choice_anime_mode = {}

# Функція отримання привітання
def get_greeting(first_name='', last_name='', language=''):
    greeting_text = language['phrases']["greeting"]
    full_name = (first_name + ' ' + last_name).strip()
    return greeting_text % full_name if full_name else language['phrases']['welcomes']

# Головна функція
@bot.message_handler(commands=['start'])
def main(message):
    lang = message.from_user.language_code

    date_registration = datetime.now() # визначення часу реєстрації користувача
    
    user = message.from_user
    
    with sqlite3.connect('my_database.db') as conn:
        cursor = conn.cursor()
    
        # Інформація про користувача
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        date_registration TEXT
                    )
                ''')
        conn.commit()
    
        # Вставка інформації про користувача
        cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, date_registration)
                VALUES (?, ?)
            ''', (user.id, date_registration.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()

        # Інформація про аніме
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS anime (
                        anime_id INTEGER PRIMARY KEY,
                        user_id INTEGER,
                        id INTEGER,
                        title TEXT,
                        num_episodes TEXT,
                        status TEXT,
                        source TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                ''')
        conn.commit()
    
    
    # Визначення обраної мови користувача
    user_choose_lang = next((v for k, v in loaded_localizations.items(
    ) if v['localization_short_code'] == lang), loaded_localizations['en_EN'])

    user_id = message.from_user.id
    user_name = message.from_user.first_name if message.from_user.first_name is not None else ""
    user_last_name = message.from_user.last_name if message.from_user.last_name is not None else ""

    user_languages[user_id] = user_choose_lang  # Збереження мови користувача

    greeting = get_greeting(user_name, user_last_name, user_choose_lang)

    buttons = [
        types.KeyboardButton(user_choose_lang["phrases"]["search_new_anime"]),
        types.KeyboardButton(user_choose_lang["phrases"]["search_history"]),
        types.KeyboardButton(user_choose_lang["phrases"]["change_language"])
    ]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(*buttons)

    # Відправлення привітання разом з клавіатурою
    bot.send_message(message.chat.id, greeting, reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == user_languages.get(message.from_user.id, {}).get("phrases", {}).get("change_language", ""))
def change_language(message):
    user_id = message.from_user.id
    user_in_change_mode = user_in_language_change_mode.get(user_id, False)

    if not user_in_change_mode:
        # Користувач не в режимі зміни мови
        user_in_language_change_mode[user_id] = True
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        keys_buttons = []

        # Використовуємо короткі коди локалізацій для тексту кнопок
        for key in loaded_localizations:
            keys = types.KeyboardButton(loaded_localizations.get(
                key).get("localization_name"))
            keys_buttons.append(keys)

        markup.row(*keys_buttons)

        markup.row(types.KeyboardButton(
            user_languages[user_id]["phrases"]["come_back"]))

        bot.send_message(message.chat.id, user_languages[user_id]["phrases"]["select_language"],
                         reply_markup=markup)
    else:
        # Користувач вже в режимі зміни мови
        bot.send_message(
            message.chat.id, user_languages[user_id]["phrases"]["already_change_lang"])


@bot.message_handler(func=lambda message: message.text in [loc['localization_name'] for loc in loaded_localizations.values()])
def set_language(message):
   
    user_id = message.from_user.id
    selected_language = message.text
    user_in_language_change_mode[user_id] = False

    current_language = user_languages.get(
        user_id, {}).get("localization_name", "")

    # Перевіряємо, чи введена мова відповідає короткому коду
    if selected_language in [loc["localization_name"] for loc in loaded_localizations.values()]:
        if current_language != selected_language:
            new_language = next(
                (loc for loc in loaded_localizations.values() if loc["localization_name"] == selected_language), None)
            
            user_languages[user_id] = new_language

            # Оновлення кнопок без повідомлення про це
            pharses1 = user_languages[user_id].get("phrases", {})
            buttons = [
                types.KeyboardButton(pharses1.get("search_new_anime", "")),
                types.KeyboardButton(pharses1.get("search_history", "")),
                types.KeyboardButton(pharses1.get("change_language", ""))
            ]

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row(*buttons)

            bot.send_message(
                message.chat.id, f"{new_language['phrases']['choose_language']} {new_language['localization_name']}", reply_markup=markup, disable_notification=True)
        else:
            bot.send_message(
                message.chat.id, user_languages[user_id]['phrases']['lang_used'])
    else:
        bot.send_message(
            message.chat.id, f"{user_languages[user_id]['phrases']['none_lang'].replace('%s', message.text)}")

    # Повернення до основної клавіатури
    pharses2 = user_languages[user_id].get("phrases", {})
    buttons = [
        types.KeyboardButton(pharses2.get("search_new_anime", "")),
        types.KeyboardButton(pharses2.get("search_history", "")),
        types.KeyboardButton(pharses2.get("change_language", ""))
    ]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(*buttons)

# Кнопка "Назад"
@bot.message_handler(func=lambda message: message.text == user_languages.get(message.from_user.id, {}).get("phrases", {}).get("come_back", ""))
def back_to_main_keyboard(message):
    user_id = message.from_user.id
    user_in_language_change_mode[user_id] = False

    # Повернення до основної клавіатури
    phrases3 = user_languages[user_id].get("phrases", {})
    buttons = [
        types.KeyboardButton(phrases3.get("search_new_anime", "")),
        types.KeyboardButton(phrases3.get("search_history", "")),
        types.KeyboardButton(phrases3.get("change_language", ""))
    ]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(*buttons)

    # Відправлення повідомлення разом з оновленою клавіатурою
    bot.send_message(
        message.chat.id, user_languages[user_id]["phrases"]["return_main_keyboard"], reply_markup=markup, disable_notification=True)

# Кнопка "Пошук аніме"
@bot.message_handler(func=lambda message: message.text == user_languages.get(message.from_user.id, {}).get("phrases", {}).get("search_new_anime", ""))
def search_anime(message):
    user_id = message.from_user.id
    # Встановлення режиму пошуку аніме для користувача
    user_in_search_anime_mode[user_id] = True

# Додавання кнопки "Назад"
    back_button = types.KeyboardButton(
        user_languages[user_id]["phrases"]["come_back"])
    kboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kboard.row(back_button)
    
    bot.send_message(
        message.chat.id, user_languages[user_id]["phrases"]["search_offer"], reply_markup=kboard)
    
user_data_anime = {}  # Інформація про аніме користувача

@bot.message_handler(func=lambda message: user_in_search_anime_mode.get(message.from_user.id, False))
def handle_anime_search(message):
    user_id = message.from_user.id
    # Завершення режиму пошуку аніме для користувача
    user_in_search_anime_mode[user_id] = False
    
    # Додаємо кнопку "Назад" для повернення на головне меню
    back_button = types.KeyboardButton(
        user_languages[user_id]["phrases"]["come_back"])
    
    anime_name = message.text  # Отримання назви аніме від користувача
    
    api_url = f"https://api.myanimelist.net/v2/anime?q={anime_name}&limit=4"
    headers = {
        "Authorization": f"Bearer {an_token}"
    }
    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 200:
        search_results = response.json()
    
        if 'data' in search_results and search_results['data']:
            kboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            
            anime_data = {}  # Збереження назв аніме та їх ідентифікаторів
            for result in search_results['data']:
                title = result.get('node', {}).get('title', 'Невідомо')
                anime_id = result.get('node', {}).get('id', 'Невідомо')
                anime_data[title] = anime_id
                kboard.add(types.KeyboardButton(title))
            
            kboard.row(back_button)
            
            bot.send_message(
                message.chat.id, user_languages[user_id]["phrases"]["choose_anime"], reply_markup=kboard)
            user_data_anime[user_id] = anime_data
            user_in_choice_anime_mode[user_id] = True
        else:
            bot.send_message(
                message.chat.id, user_languages[user_id]["phrases"]["error"])
    else:
        bot.send_message(
            message.chat.id, user_languages[user_id]["phrases"]["error_search"])


# Обробник повідомлень для вибору аніме
@bot.message_handler(func=lambda message: user_in_choice_anime_mode.get(message.from_user.id, False))
def handle_anime_choice(message):
    user_id = message.from_user.id
    user_in_choice_anime_mode[user_id] = False
    anime_data = user_data_anime.get(user_id, {})

    with sqlite3.connect('my_database.db') as conn:
        cursor = conn.cursor()

        if message.text in anime_data:
            anime_id = anime_data[message.text]

            api_url = f"https://api.myanimelist.net/v2/anime/{anime_id}?fields=alternative_titles,synopsis,num_episodes,status,source"
            headers = {
                "Authorization": f"Bearer {an_token}"
            }
            responses = requests.get(api_url, headers=headers)

            if responses.status_code == 200:
                anime_info = responses.json()

                # Перевірка, чи існує вже запис з таким user_id
                cursor.execute(
                    'SELECT * FROM anime WHERE user_id = ? AND id = ?', (user_id, anime_id))
                existing_record = cursor.fetchall()

                if existing_record:
                    # Оновлення існуючого запису замість вставки нового
                    cursor.execute('''
                        UPDATE anime
                        SET title=?, num_episodes=?, status=?, source=?
                        WHERE user_id=? AND id=?
                    ''', (anime_info['alternative_titles']['en'], anime_info['num_episodes'], anime_info['status'], anime_info['source'], user_id, anime_id))
                    conn.commit()
                else:
                    # Вставка нового запису, якщо існуючий не знайдено
                    cursor.execute('''
                                   INSERT OR REPLACE INTO anime (user_id, id, title, num_episodes, status, source)
                                   VALUES (?, ?, ?, ?, ?, ?)
                                   ''', (user_id, anime_id, anime_info['alternative_titles']['en'], anime_info['num_episodes'], anime_info['status'], anime_info['source']))
                    conn.commit()

                bot.send_message(
                    message.chat.id, user_languages[user_id]["phrases"]["res_search"])

                info_message = f"Synopsis: {anime_info['synopsis']}\nEpisodes: {anime_info['num_episodes']}\nStatus: {anime_info['status']}\nSource: {anime_info['source']}"
                
                # Оновлення значень кнопок
                phrases3 = user_languages[user_id].get("phrases", {})
                buttons = [
                    types.KeyboardButton(phrases3.get("search_new_anime", "")),
                    types.KeyboardButton(phrases3.get("search_history", "")),
                    types.KeyboardButton(phrases3.get("change_language", ""))
                ]

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.row(*buttons)
                
                bot.send_message(message.chat.id, info_message, reply_markup=markup)
                
            else:
                bot.send_message(
                    message.chat.id, user_languages[user_id]["phrases"]["error"])
        else:
            bot.send_message(
                message.chat.id, user_languages[user_id]["phrases"]["error_search"])


@bot.message_handler(func=lambda message: message.text == user_languages.get(message.from_user.id, {}).get("phrases", {}).get("come_back", ""))
def back_to_main_menu(message):
    user_id = message.from_user.id
    user_in_choice_anime_mode[user_id] = False

    # Оновлення значень кнопок
    phrases4 = user_languages[user_id].get("phrases", {})
    buttons = [
        types.KeyboardButton(phrases4.get("search_new_anime", "")),
        types.KeyboardButton(phrases4.get("search_history", "")),
        types.KeyboardButton(phrases4.get("change_language", ""))
    ]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(*buttons)

    # Відправлення повідомлення разом з оновленою клавіатурою
    bot.send_message(
        message.chat.id, user_languages[user_id]["phrases"]["return_main_keyboard"], reply_markup=markup, disable_notification=True)


@bot.message_handler(func=lambda message: message.text == user_languages.get(message.from_user.id, {}).get("phrases", {}).get("search_history", ""))
def search_history(message):
    user_id = message.from_user.id
    
    # Створення нового підключення та курсора для кожного виклику
    with sqlite3.connect('my_database.db') as conn:
        cursor = conn.cursor()

        # Вибірка інформації з бази даних за user_id в таблиці anime
        cursor.execute('SELECT * FROM anime WHERE user_id = ?', (user_id,))
        anime_info_list = cursor.fetchall()

    if anime_info_list:
        user_name = message.from_user.first_name

        # Збереження фраз в змінній
        phrases = user_languages[user_id]['phrases']
        
        history_message = f"{phrases['a_srch']} {user_name}:\n\n"

        for anime_info in anime_info_list:
            history_message += f"{phrases['a_name']} {anime_info[3]}\n"
            history_message += f"{phrases['a_num']} {anime_info[4]}\n"
            history_message += f"{phrases['a_st']}{anime_info[5]}\n"
            history_message += f"{phrases['a_sour']}{anime_info[6]}\n\n"
            
        # Додавання кнопок "Очистити історію" і "Назад"
        clear_button = types.KeyboardButton(phrases['clear_hist'])
        back_button = types.KeyboardButton(phrases['come_back'])
        kboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kboard.row(clear_button, back_button)
        
        bot.send_message(message.chat.id, history_message, reply_markup=kboard)
    else:
        bot.send_message(
            message.chat.id, {user_languages[user_id]['phrases']['a_inf']})

@bot.message_handler(func=lambda message: message.text == user_languages.get(message.from_user.id, {}).get("phrases", {}).get("clear_hist", ""))
def clear_history(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Видалення історії з бази даних
    with sqlite3.connect('my_database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM anime WHERE user_id = ?', (user_id,))
        conn.commit()

    phrases5 = user_languages[user_id].get("phrases", {})
    buttons = [
        types.KeyboardButton(phrases5.get("search_new_anime", "")),
        types.KeyboardButton(phrases5.get("search_history", "")),
        types.KeyboardButton(phrases5.get("change_language", ""))
    ]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(*buttons)

    phrasess = user_languages[user_id]['phrases']
    user_message = f"{phrasess['a_srch']} {user_name}:\n\n"
    user_message += f"{phrasess['hist_cleared']}"

    
    # Відправлення повідомлення про те, що історію очищено
    bot.send_message(message.chat.id, user_message, reply_markup=markup)

if __name__ == "__main__":
    try:
        # Постійний запуск бота + оновлення серверу бота та перевірка помилок
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Помилка: {e}")
    finally:
        conn.close()
